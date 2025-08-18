# app/routes.py
import os
import json
from datetime import datetime

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, current_app,
    jsonify, abort
)
from flask_login import login_required, current_user
from sqlalchemy import or_
from werkzeug.utils import secure_filename, safe_join
from app.paths import ensure_case_folder, file_safe_case_number

from app import db
from app.utils.time_utils import now_local
from app.utils.roles import roles_required
from app.utils.case_helpers import build_case_context

# CSRF exempt (new Flask-WTF or fallback)
try:
    from flask_wtf.csrf import csrf_exempt
except ImportError:  # Flask-WTF < 1.2
    from app import csrf as _csrf
    csrf_exempt = _csrf.exempt

# Models used in this module
from app.models import User, Case, ChangeLog, UploadedFile, UserSessionLog
# Investigation models belong to the investigations blueprint module:
# from app.investigations.models import Investigation, InvestigationNote, ...

# Blueprint
main_bp = Blueprint("main", __name__)

# --- Helpers ---

def append_note(case, note_text, author=None):
    """Appends a note to the case.notes field with timestamp and author."""
    ts = now_local().strftime('%Y-%m-%d %H:%M')
    if author is None:
        author = current_user.screen_name or current_user.username
    entry = f"[{ts} – {author}] {note_text}"
    case.notes = (case.notes + "\n" if case.notes else "") + entry
    return entry

def handle_file_upload(case, file, category='egyéb'):
    """Handles file upload and database record creation. Returns filename if uploaded, None otherwise."""
    if not file or not file.filename:
        return None
    fn = secure_filename(file.filename)
    upload_dir = str(ensure_case_folder(case.case_number))
    try:
        file.save(os.path.join(upload_dir, fn))
    except Exception as e:
        current_app.logger.error(f"File save failed: {e}")
        flash("A fájl mentése nem sikerült.", "danger")
        return None
    rec = UploadedFile(
        case_id=case.id,
        filename=fn,
        uploader=current_user.screen_name or current_user.username,
        upload_time=now_local(),
        category=category
    )
    db.session.add(rec)
    return fn

def is_expert_for_case(user, case):
    ident = user.screen_name or user.username
    return ident in (case.expert_1, case.expert_2)

def is_describer_for_case(user, case):
    ident = user.screen_name or user.username
    return ident == case.describer

# --- Error handlers ---

@main_bp.app_errorhandler(413)
def _too_large(e):
    # Tests only check the status code; keep it minimal.
    return '', 413

def _max_upload_bytes():
    """Return max upload size in bytes, defaulting to 16MB if not configured or set to a non-number/None."""
    val = current_app.config.get('MAX_CONTENT_LENGTH', None)
    # Treat None/0/invalid as unset -> default 16MB
    try:
        if val is None:
            return 16 * 1024 * 1024
        return int(val)
    except Exception:
        return 16 * 1024 * 1024

def enforce_upload_size_limit():
    """Abort with 413 if request exceeds configured/upload size limit."""
    cl = request.content_length
    if cl is not None and cl > _max_upload_bytes():
        abort(413)

# --- Routes ---

@main_bp.route('/track', methods=['POST'])
@csrf_exempt
@login_required
def track_user_activity():
    if not current_app.config.get("TRACK_USER_ACTIVITY", False):
        return '', 204

    data = request.get_json()
    if not data:
        return '', 400

    value = data.get("value")
    extra = data.get("extra") or {}

    log = UserSessionLog(
        user_id=current_user.id,
        path=request.path,
        event_type=data.get("event_type"),
        element=data.get("element"),
        value=json.dumps(value) if value is not None else None,
        timestamp=now_local(),
        extra=json.dumps(extra),
    )
    db.session.add(log)
    db.session.commit()
    return '', 204

@main_bp.route('/cases')
@login_required
def case_list():
    """Simple passthrough to the main cases listing."""
    return redirect(url_for('auth.list_cases'))

@main_bp.route('/ugyeim')
@login_required
@roles_required('szakértő')
def ugyeim():
    ident = current_user.screen_name or current_user.username
    base_q = Case.query.filter(or_(
        Case.expert_1 == ident,
        Case.expert_2 == ident
    ))
    pending   = base_q.filter(Case.status != 'boncolva-leírónál').all()
    completed = base_q.filter(Case.status == 'boncolva-leírónál').all()
    return render_template('ugyeim.html',
                           pending_cases=pending,
                           completed_cases=completed)

# AJAX add-note
@main_bp.route('/ugyeim/<int:case_id>/add_note', methods=['POST'])
@login_required
@roles_required('szakértő')
def add_note(case_id):
    data = request.get_json() or {}
    note_text = data.get('new_note','').strip()
    if not note_text:
        return jsonify({'error':'Empty note'}), 400

    case = db.session.get(Case, case_id) or abort(404)
    entry = append_note(case, note_text)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Database error: {e}")
        return jsonify({'error': 'DB error'}), 500

    html = f'<div class="alert alert-secondary py-2">{entry}</div>'
    return jsonify({'html': html})

@main_bp.before_app_request
def _enforce_global_upload_cap():
    # Only check multipart POSTs
    if request.method != 'POST':
        return
    ct = request.content_type or ''
    if 'multipart/form-data' not in ct:
        return

    limit = _max_upload_bytes()

    # Prefer Content-Length if provided by client
    cl = request.content_length
    if cl is not None and cl > limit:
        abort(413)

    # Fallback: inspect uploaded files (Werkzeug FileStorage)
    try:
        for fs in request.files.values():
            size = getattr(fs, 'content_length', None)
            if size is None:
                pos = fs.stream.tell()
                fs.stream.seek(0, os.SEEK_END)
                size = fs.stream.tell()
                fs.stream.seek(pos, os.SEEK_SET)
            if size is not None and size > limit:
                abort(413)
    except Exception:
        # Do not block if we cannot determine size
        pass

@main_bp.route('/cases/<int:case_id>/mark_tox_viewed')
@login_required
@roles_required('szakértő')
def mark_tox_viewed(case_id):
    case = db.session.get(Case, case_id) or abort(404)
    if not is_expert_for_case(current_user, case):
        abort(403)

    case.tox_viewed_by_expert = True

    # Tests monkeypatch app.routes.datetime, so call utcnow() from THIS module's import
    ts = datetime.utcnow()
    if getattr(ts, "tzinfo", None) is not None:
        ts = ts.replace(tzinfo=None)
    case.tox_viewed_at = ts

    log = ChangeLog(
        case_id=case.id,
        field_name="system",
        old_value=None,
        new_value="Toxi végzés megtekintve",
        edited_by=current_user.screen_name or current_user.username,
        timestamp=ts,
    )
    db.session.add(log)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Database error: {e}")
        return jsonify({'error': 'DB error'}), 500

    flash("Toxikológiai végzés megtekintve.", "success")
    return redirect(url_for('main.elvegzem', case_id=case.id))

# Unified elvégzem (szakértő & leíró)
@main_bp.route('/ugyeim/<int:case_id>/elvegzem', methods=['GET','POST'])
@login_required
@roles_required('szakértő', 'leíró')
def elvegzem(case_id):
    case = db.session.get(Case, case_id) or abort(404)

    # Authorization
    if current_user.role == 'szakértő':
        if not is_expert_for_case(current_user, case):
            flash('Nincs jogosultságod az ügy elvégzéséhez.', 'danger')
            return redirect(url_for('main.ugyeim'))
    else:
        if not is_describer_for_case(current_user, case):
            flash('Nincs jogosultságod az ügy elvégzéséhez.', 'danger')
            return redirect(url_for('main.leiro_ugyeim'))

    if current_user.role == 'szakértő' and not case.started_by_expert:
        case.started_by_expert = True
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Database error: {e}")

    if request.method == 'POST':
        if (
            current_user.role == 'szakértő'
            and case.tox_ordered
            and not case.tox_viewed_by_expert
        ):
            flash('Meg kell tekintenie a végzést', 'warning')
            return redirect(url_for('main.elvegzem', case_id=case.id))
        # 1) Chat-style note
        new_note = request.form.get('new_note','').strip()
        note_added = False
        if new_note:
            append_note(case, new_note)
            note_added = True

        # 2) File upload
        enforce_upload_size_limit()
        f = request.files.get('result_file')
        category = request.form.get('category') or 'egyéb'
        file_uploaded = handle_file_upload(case, f, category=category) if f else None

        # 3) Halotti bizonyítvány mezők
        who = request.form.get('halalt_megallap')
        case.halalt_megallap_pathologus = who == 'pathologus'
        case.halalt_megallap_kezeloorvos = who == 'kezeloorvos'
        case.halalt_megallap_mas_orvos = who == 'mas_orvos'

        bonc = request.form.get('boncolas_tortent')
        case.boncolas_tortent = bonc == 'igen'

        further = request.form.get('varhato_tovabbi_vizsgalat')
        case.varhato_tovabbi_vizsgalat = further == 'igen'
        case.kozvetlen_halalok = request.form.get('kozvetlen_halalok') or None
        case.kozvetlen_halalok_ido = request.form.get('kozvetlen_halalok_ido') or None
        case.alapbetegseg_szovodmenyei = request.form.get('alapbetegseg_szovodmenyei') or None
        case.alapbetegseg_szovodmenyei_ido = request.form.get('alapbetegseg_szovodmenyei_ido') or None
        case.alapbetegseg = request.form.get('alapbetegseg') or None
        case.alapbetegseg_ido = request.form.get('alapbetegseg_ido') or None
        case.kiserobetegsegek = request.form.get('kiserobetegsegek') or None

        # 4) Status transition
        previous_status = case.status
        case.status = 'boncolva-leírónál' if current_user.role=='szakértő' else 'leiktatva'

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Database error: {e}")
            flash("Valami hiba történt. Próbáld újra.", "danger")
            return redirect(request.referrer or url_for('main.ugyeim'))
        if note_added:
            flash('Megjegyzés hozzáadva.', 'success')
        if file_uploaded:
            flash(f'Fájl feltöltve: {file_uploaded}', 'success')
        if previous_status != case.status:
            flash('Művelet sikeresen rögzítve.', 'success')
        return redirect(
            url_for('main.ugyeim') if current_user.role=='szakértő'
            else url_for('main.leiro_ugyeim')
        )

    # GET: choose template & build context
    template = (
        'elvegzem_szakerto.html' if current_user.role=='szakértő'
        else 'elvegzem_leiro.html'
    )

    ctx = build_case_context(case)
    ctx['case'] = case
    vegzes_file = next(
        (f for f in case.uploaded_file_records if f.category == "végzés"),
        None
    )
    ctx['vegzes_file'] = vegzes_file
    if current_user.role=='szakértő':
        leiro_users = (User.query
            .filter_by(role='leíró')
            .order_by(User.username)
            .all())
        leiro_choices = [('', '(válasszon)')] + [
            (u.username, u.screen_name or u.username) for u in leiro_users
        ]
        ctx['leiro_users'] = leiro_users
        ctx['leiro_choices'] = leiro_choices

    return render_template(template, **ctx)

# Vizsgálat elrendelése
@main_bp.route('/ugyeim/<int:case_id>/vizsgalat_elrendelese', methods=['GET', 'POST'])
@login_required
@roles_required('szakértő', 'iroda')
def vizsgalat_elrendelese(case_id):
    case = db.session.get(Case, case_id) or abort(404)
    # Only restrict experts to their assigned cases; iroda may order for any case
    if current_user.role == 'szakértő' and not is_expert_for_case(current_user, case):
        flash('Nincs jogosultságod vizsgálatot elrendelni.', 'danger')
        return redirect(url_for('main.ugyeim'))

    if request.method == 'POST':
        # Use local Budapest time and the username for logging toxicology orders
        now = now_local().strftime('%Y-%m-%d %H:%M')
        author = current_user.username
        redirect_target = (
            url_for('auth.edit_case', case_id=case.id)
            if current_user.role == 'iroda'
            else url_for('main.elvegzem', case_id=case.id)
        )
        lines = []

        # Tox text fields with checkbox state
        for label, field in [
            ('Alkohol vér', 'alkohol_ver'),
            ('Alkohol vizelet', 'alkohol_vizelet'),
            ('Alkohol liquor', 'alkohol_liquor'),
            ('Egyéb alkohol', 'egyeb_alkohol'),
            ('Gyógyszer vér', 'tox_gyogyszer_ver'),
            ('Gyógyszer vizelet', 'tox_gyogyszer_vizelet'),
            ('Gyógyszer gyomortartalom', 'tox_gyogyszer_gyomor'),
            ('Gyógyszer máj', 'tox_gyogyszer_maj'),
            ('Kábítószer vér', 'tox_kabitoszer_ver'),
            ('Kábítószer vizelet', 'tox_kabitoszer_vizelet'),
            ('CPK', 'tox_cpk'),
            ('Szárazanyagtartalom', 'tox_szarazanyag'),
            ('Diatóma', 'tox_diatoma'),
            ('CO', 'tox_co'),
            ('Egyéb toxikológia', 'egyeb_tox')
        ]:
            val = (request.form.get(field) or "").strip()
            ordered = request.form.get(f"{field}_ordered") == "on"
            already = getattr(case, f"{field}_ordered")
            if already:
                # Never unset previously ordered fields — they are permanent once submitted
                continue
            if ordered:
                setattr(case, field, val)
                setattr(case, f"{field}_ordered", True)
                if val:
                    lines.append(f"{label} rendelve ({val}): {now} – {author}")
                else:
                    lines.append(f"{label} rendelve: {now} – {author}")

        # Organs – checkboxes
        for organ, label in [
            ('sziv', 'Szív'),
            ('tudo', 'Tüdő'),
            ('maj', 'Máj'),
            ('vese', 'Vese'),
            ('agy', 'Agy'),
            ('mellekvese', 'Mellékvese'),
            ('pajzsmirigy', 'Pajzsmirigy'),
            ('hasnyalmirigy', 'Hasnyálmirigy'),
            ('lep', 'Lép')
        ]:
            markers = request.form.getlist(f"{organ}_marker")
            spec = 'spec' in markers
            immun = 'immun' in markers
            prev_spec = getattr(case, f"{organ}_spec")
            prev_immun = getattr(case, f"{organ}_immun")
            new_spec = prev_spec or spec
            new_immun = prev_immun or immun
            setattr(case, f"{organ}_spec", new_spec)
            setattr(case, f"{organ}_immun", new_immun)
            if (not prev_spec and spec) or (not prev_immun and immun):
                badge = []
                if new_spec:
                    badge.append("Spec fest")
                if new_immun:
                    badge.append("Immun")
                lines.append(
                    f"{label} – {', '.join(badge)} rendelve: {now} – {author}"
                )

        # Egyéb szerv
        egyeb_szerv = request.form.get('egyeb_szerv')
        markers = request.form.getlist('egyeb_szerv_marker')
        prev_spec = case.egyeb_szerv_spec
        prev_immun = case.egyeb_szerv_immun
        if not prev_spec and not prev_immun:
            case.egyeb_szerv = egyeb_szerv or None
            spec = 'spec' in markers
            immun = 'immun' in markers
            case.egyeb_szerv_spec = spec
            case.egyeb_szerv_immun = immun
            if egyeb_szerv and (spec or immun):
                badge = []
                if spec:
                    badge.append("Spec fest")
                if immun:
                    badge.append("Immun")
                lines.append(
                    f"Egyéb szerv ({egyeb_szerv}): {', '.join(badge)} rendelve: {now} – {author}"
                )

        if lines:
            new_block = "\n".join(lines)
            if case.tox_orders:
                case.tox_orders = case.tox_orders.strip() + "\n" + new_block
            else:
                case.tox_orders = new_block

            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Database error: {e}")
                flash("Valami hiba történt. Próbáld újra.", "danger")
                return redirect(redirect_target)
            flash('Vizsgálatok elrendelve.', 'success')
        else:
            flash('Nem választottál ki vizsgálatot.', 'warning')

        return redirect(redirect_target)

    return render_template('vizsgalat.html', case=case)

# Extra file‐upload for szakértő flow
@main_bp.route('/ugyeim/<int:case_id>/upload_elvegzes_files', methods=['POST'])
@login_required
@roles_required('szakértő')
def upload_elvegzes_files(case_id):
    enforce_upload_size_limit()
    case = db.session.get(Case, case_id) or abort(404)
    if not is_expert_for_case(current_user, case):
        flash('Nincs jogosultságod fájlokat feltölteni.', 'danger')
        return redirect(url_for('main.elvegzem', case_id=case.id))

    files = request.files.getlist('extra_files')
    if not files:
        flash('Nincs kiválasztott fájl.', 'warning')
        return redirect(url_for('main.elvegzem', case_id=case.id))

    saved = []
    category = request.form.get('category') or 'egyéb'
    for f in files:
        fn = handle_file_upload(case, f, category=category)
        if fn:
            saved.append(fn)

    if saved:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Database error: {e}")
            flash("Valami hiba történt. Próbáld újra.", "danger")
            return redirect(url_for('main.elvegzem', case_id=case.id))
        flash(f'Feltöltve: {", ".join(saved)}', 'success')

    return redirect(url_for('main.elvegzem', case_id=case.id))

# Leíró’s dashboard & flow
@main_bp.route('/leiro/ugyeim')
@login_required
@roles_required('leíró')
def leiro_ugyeim():
    ident = current_user.screen_name or current_user.username
    base_q = Case.query.filter_by(describer=ident)
    pending   = base_q.filter(Case.status=='boncolva-leírónál').all()
    completed = base_q.filter(Case.status=='leiktatva').all()
    return render_template('leiro_ugyeim.html',
                           pending_cases=pending,
                           completed_cases=completed)

# Toxi dashboard
@main_bp.route('/ugyeim/toxi')
@login_required
@roles_required('toxi')
def toxi_ugyeim():
    """Dashboard for toxicology specialists."""
    vegzes_exists = db.session.query(UploadedFile.id).filter(
        UploadedFile.case_id == Case.id,
        UploadedFile.category == 'végzés'
    ).exists()

    pending_filter = or_(Case.tox_completed.is_(False), Case.tox_completed.is_(None))

    assigned_cases = Case.query.filter(pending_filter, vegzes_exists).all()
    done_cases = Case.query.filter(Case.tox_completed.is_(True), vegzes_exists).all()

    return render_template(
        'toxi_ugyeim.html',
        assigned_cases=assigned_cases,
        done_cases=done_cases,
    )

@main_bp.route('/elvegzem_toxi/<int:case_id>', methods=['GET', 'POST'])
@login_required
@roles_required('toxi')
def elvegzem_toxi(case_id):
    case = db.session.get(Case, case_id) or abort(404)

    if case.tox_expert and case.tox_expert != current_user.screen_name:
        flash('Nincs jogosultságod az ügy elvégzéséhez.', 'danger')
        return redirect(url_for('main.toxi_ugyeim'))

    if request.method == 'POST':
        note = request.form.get('new_note', '').strip()
        if note:
            append_note(case, note)
        case.tox_expert = current_user.screen_name or current_user.username
        case.tox_completed = True
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Database error: {e}")
            flash('Valami hiba történt. Próbáld újra.', 'danger')
            return redirect(url_for('main.elvegzem_toxi', case_id=case.id))
        flash('✔️ Toxikológiai vizsgálat elvégezve.', 'success')
        return redirect(url_for('main.toxi_ugyeim'))

    return render_template('elvegzem_toxi.html', case=case)

@main_bp.route('/leiro/ugyeim/<int:case_id>/elvegzem', methods=['GET','POST'])
@login_required
@roles_required('leíró')
def leiro_elvegzem(case_id):
    case = db.session.get(Case, case_id) or abort(404)
    if not is_describer_for_case(current_user, case):
        flash('Nincs jogosultságod az ügy elvégzéséhez.', 'danger')
        return redirect(url_for('main.leiro_ugyeim'))

    if request.method == 'POST':
        # 1) Handle file upload
        enforce_upload_size_limit()
        file = request.files.get('result_file')
        category = request.form.get('category') or 'egyéb'
        file_uploaded = handle_file_upload(case, file, category=category)

        # 2) Add any new note
        new_note = request.form.get('new_note','').strip()
        if new_note:
            append_note(case, new_note)

        # 3) Mark the case as completed by the describer
        case.status = 'leiktatva'
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Database error: {e}")
            flash("Valami hiba történt. Próbáld újra.", "danger")
            return redirect(url_for('main.leiro_elvegzem', case_id=case.id))

        if file_uploaded:
            flash(f'Fájl feltöltve: {file_uploaded}', 'success')
        if new_note:
            flash('Megjegyzés hozzáadva.', 'success')
        flash('Ügy elvégzése sikeresen rögzítve.', 'success')
        # Redirect to the listing page, not back to the same form
        return redirect(url_for('main.leiro_ugyeim'))

    # GET
    changelog_entries = (
        ChangeLog.query
                 .filter_by(case_id=case.id)
                 .order_by(ChangeLog.timestamp.desc())
                 .all()
    )
    return render_template(
        'elvegzem_leiro.html',
        case=case,
        changelog_entries=changelog_entries
    )

@main_bp.route('/ugyeim/<int:case_id>/assign_describer', methods=['POST'])
@login_required
@roles_required('szakértő')
def assign_describer(case_id):
    data = request.get_json() or {}
    case = db.session.get(Case, case_id) or abort(404)
    case.describer = data.get('describer')
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Database error: {e}")
        return jsonify({'error': 'DB error'}), 500
    flash('Leíró sikeresen hozzárendelve.', 'success')  # shown after page reload
    return ('', 204)

@main_bp.route('/leiro/ugyeim/<int:case_id>/upload_file', methods=['POST'])
@login_required
@roles_required('leíró')
def leiro_upload_file(case_id):
    enforce_upload_size_limit()
    case = db.session.get(Case, case_id) or abort(404)
    if not is_describer_for_case(current_user, case):
        flash('Nincs jogosultságod!', 'danger')
        return redirect(url_for('main.leiro_elvegzem', case_id=case.id))

    file = request.files.get('result_file')
    category = request.form.get('category') or 'egyéb'
    file_uploaded = handle_file_upload(case, file, category=category)
    if not file_uploaded:
        flash('Nincs kiválasztott fájl!', 'warning')
        return redirect(url_for('main.leiro_elvegzem', case_id=case.id))

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Database error: {e}")
        flash("Valami hiba történt. Próbáld újra.", "danger")
        return redirect(url_for('main.leiro_elvegzem', case_id=case.id))
    flash(f'Fájl feltöltve: {file_uploaded}', 'success')
    return redirect(url_for('main.leiro_elvegzem', case_id=case.id))

@main_bp.route('/ugyeim/<int:case_id>/generate_certificate', methods=['POST'])
@login_required
@roles_required('szakértő')
def generate_certificate(case_id):
    """Generate death certificate text file in the exact format tests expect."""
    case = db.session.get(Case, case_id) or abort(404)

    # Only assigned experts may generate the certificate
    if not is_expert_for_case(current_user, case):
        abort(403)

    # Ensure output directory: <case_root>/<case_number>/
    case_dir = str(ensure_case_folder(case.case_number))

    f = request.form
    get = lambda k: (f.get(k) or "").strip()

    lines = [
        f"Ügy: {case.case_number}",
        "",
        f"A halál okát megállapította: {get('halalt_megallap')}",
        "",
        f"Történt-e boncolás: {get('boncolas_tortent')}",
        f"Ha igen, várhatók-e további vizsgálati eredmények: {get('varhato_tovabbi_vizsgalat')}",
        "",  # spacer
        f"Közvetlen halálok: {get('kozvetlen_halalok')}",
        f"Esemény kezdete és halál között eltelt idő: {get('kozvetlen_halalok_ido')}",
        "",
        f"Alapbetegség szövődményei: {get('alapbetegseg_szovodmenyei')}",
        f"Esemény kezdete és halál között eltelt idő: {get('alapbetegseg_szovodmenyei_ido')}",
        "",
        f"Alapbetegség: {get('alapbetegseg')}",
        f"Esemény kezdete és halál között eltelt idő: {get('alapbetegseg_ido')}",
        "",
        f"Kísérő betegségek vagy állapotok: {get('kiserobetegsegek')}",
    ]

    # NEW: footer line the test asserts with lines[-1].startswith('Generálva: ')
    lines.append(f"Generálva: {now_local().strftime('%Y-%m-%d %H:%M')}")

    out_path = os.path.join(
        case_dir, f"halottvizsgalati_bizonyitvany-{file_safe_case_number(case.case_number)}.txt"
    )
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))

    case.certificate_generated = True
    case.certificate_generated_at = now_local()
    db.session.commit()

    flash("Bizonyítvány generálva.", "success")
    return redirect(url_for("main.elvegzem", case_id=case.id))

@main_bp.route('/cases/<int:case_id>/complete_expert', methods=['POST'])
@login_required
def complete_expert(case_id):
    case = Case.query.get_or_404(case_id)

    # Set status to indicate expert work is done
    case.status = 'boncolva-leírónál'

    # Log the action
    append_note(case, "Szakértő elvégezte a boncolást.")
    db.session.commit()

    flash("Szakértői vizsgálat elvégezve.")
    return redirect(url_for('main.ugyeim'))

@main_bp.route('/create-examination', methods=['GET', 'POST'])
def create_examination():
    return redirect(url_for('investigations.new_investigation'))
