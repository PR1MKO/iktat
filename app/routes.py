import os
from datetime import datetime
import pytz
from app.utils.time_utils import now_local
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, current_app,
    jsonify, abort
)
from flask_login import login_required, current_user
from app.utils.roles import roles_required
from sqlalchemy import or_
from werkzeug.utils import secure_filename
from app.models import User, Case, ChangeLog, UploadedFile
from app import db
from app import csrf
from app.utils.case_helpers import build_case_context

main_bp = Blueprint('main', __name__)

# --- Helpers ---

def append_note(case, note_text, author=None):
    """Appends a note to the case.notes field with timestamp and author."""
    ts = now_local().strftime('%Y-%m-%d %H:%M')
    if author is None:
        author = current_user.screen_name or current_user.username
    entry = f"[{ts} – {author}] {note_text}"
    case.notes = (case.notes + "\n" if case.notes else "") + entry
    return entry

def handle_file_upload(case, file, folder_key='UPLOAD_FOLDER'):
    """Handles file upload and database record creation. Returns filename if uploaded, None otherwise."""
    if not file or not file.filename:
        return None
    fn = secure_filename(file.filename)
    upload_dir = os.path.join(current_app.config[folder_key], str(case.id))
    os.makedirs(upload_dir, exist_ok=True)
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
        upload_time=datetime.now(pytz.UTC)
    )
    db.session.add(rec)
    return fn

def is_expert_for_case(user, case):
    return user.username in (case.expert_1, case.expert_2)

def is_describer_for_case(user, case):
    return user.username == case.describer

# --- Routes ---

@main_bp.route('/ugyeim')
@login_required
@roles_required('szakértő')
def ugyeim():
    base_q = Case.query.filter(or_(
        Case.expert_1 == current_user.username,
        Case.expert_2 == current_user.username
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
        flash("Valami hiba történt. Próbáld újra.", "danger")
        return jsonify({'error': 'DB error'}), 500

    html = f'<div class="alert alert-secondary py-2">{entry}</div>'
    return jsonify({'html': html})

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

    if request.method == 'POST':
        # 1) Chat-style note
        new_note = request.form.get('new_note','').strip()
        note_added = False
        if new_note:
            append_note(case, new_note)
            note_added = True

        # 2) File upload
        f = request.files.get('result_file')
        file_uploaded = handle_file_upload(case, f) if f else None

        # 3) Status transition
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
@roles_required('szakértő')
def vizsgalat_elrendelese(case_id):
    case = db.session.get(Case, case_id) or abort(404)
    if not is_expert_for_case(current_user, case):
        flash('Nincs jogosultságod vizsgálatot elrendelni.', 'danger')
        return redirect(url_for('main.ugyeim'))

    if request.method == 'POST':
        now    = now_local().strftime('%Y-%m-%d %H:%M')
        author = current_user.screen_name or current_user.username
        entries = []

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
            val = request.form.get(field)
            checked = request.form.get(f"{field}_ordered") == "on"
            setattr(case, field, val if checked else None)
            setattr(case, f"{field}_ordered", checked)
            if checked and val:
                entries.append(f"{label}: {val.strip()}")

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
            setattr(case, f"{organ}_spec", spec)
            setattr(case, f"{organ}_immun", immun)
            if spec or immun:
                badge = []
                if spec: badge.append("Spec fest")
                if immun: badge.append("Immun")
                entries.append(f"{label} – {', '.join(badge)}")

        # Egyéb szerv
        egyeb_szerv = request.form.get('egyeb_szerv')
        markers = request.form.getlist('egyeb_szerv_marker')
        case.egyeb_szerv = egyeb_szerv or None
        case.egyeb_szerv_spec = 'spec' in markers
        case.egyeb_szerv_immun = 'immun' in markers
        if egyeb_szerv and (case.egyeb_szerv_spec or case.egyeb_szerv_immun):
            badge = []
            if case.egyeb_szerv_spec: badge.append("Spec fest")
            if case.egyeb_szerv_immun: badge.append("Immun")
            entries.append(f"Egyéb szerv ({egyeb_szerv}): {', '.join(badge)}")

        if entries:
            new_block = "\n".join(f"{e} rendelve: {now} – {author}" for e in entries)
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
                return redirect(url_for('main.elvegzem', case_id=case.id))
            flash('Vizsgálatok elrendelve.', 'success')
        else:
            flash('Nem választottál ki vizsgálatot.', 'warning')

        return redirect(url_for('main.elvegzem', case_id=case.id))

    return render_template('vizsgalat.html', case=case)

# Extra file‐upload for szakértő flow
@main_bp.route('/ugyeim/<int:case_id>/upload_elvegzes_files', methods=['POST'])
@login_required
@roles_required('szakértő')
def upload_elvegzes_files(case_id):
    case = db.session.get(Case, case_id) or abort(404)
    if not is_expert_for_case(current_user, case):
        flash('Nincs jogosultságod fájlokat feltölteni.', 'danger')
        return redirect(url_for('main.elvegzem', case_id=case.id))

    files = request.files.getlist('extra_files')
    if not files:
        flash('Nincs kiválasztott fájl.', 'warning')
        return redirect(url_for('main.elvegzem', case_id=case.id))

    saved = []
    for f in files:
        fn = handle_file_upload(case, f)
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
    base_q = Case.query.filter_by(describer=current_user.username)
    pending   = base_q.filter(Case.status=='boncolva-leírónál').all()
    completed = base_q.filter(Case.status=='leiktatva').all()
    return render_template('leiro_ugyeim.html',
                           pending_cases=pending,
                           completed_cases=completed)

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
        file = request.files.get('result_file')
        file_uploaded = handle_file_upload(case, file)

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
        flash("Valami hiba történt. Próbáld újra.", "danger")
        return jsonify({'error': 'DB error'}), 500
    flash('Leíró sikeresen hozzárendelve.', 'success')
    return ('', 204)

@main_bp.route('/leiro/ugyeim/<int:case_id>/upload_file', methods=['POST'])
@login_required
@roles_required('leíró')
def leiro_upload_file(case_id):
    case = db.session.get(Case, case_id) or abort(404)
    if not is_describer_for_case(current_user, case):
        flash('Nincs jogosultságod!', 'danger')
        return redirect(url_for('main.leiro_elvegzem', case_id=case.id))

    file = request.files.get('result_file')
    file_uploaded = handle_file_upload(case, file)
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
    
