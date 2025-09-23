# app/routes.py
import os
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import and_, func, or_
from werkzeug import exceptions

from app import db
from app.investigations.models import Investigation
from app.models import Case, ChangeLog, UploadedFile, User
from app.paths import file_safe_case_number
from app.utils.case_helpers import build_case_context, ensure_unlocked_or_redirect
from app.utils.case_status import is_final_status
from app.utils.dates import attach_case_dates, safe_fmt
from app.utils.idempotency import claim_idempotency, make_default_key
from app.utils.rbac import require_roles as roles_required
from app.utils.roles import canonical_role
from app.utils.time_utils import fmt_budapest, fmt_date, now_utc
from app.utils.uploads import is_valid_category, resolve_safe, save_upload

main_bp = Blueprint("main", __name__)


def append_note(case, note_text, author=None):
    """Appends a note to the case.notes field with timestamp and author."""
    ts = fmt_budapest(now_utc())
    if author is None:
        author = current_user.screen_name or current_user.username
    entry = f"[{ts} – {author}] {note_text}"
    case.notes = (case.notes + "\n" if case.notes else "") + entry
    return entry


def handle_file_upload(case, file, category="egyéb"):
    """Handles file upload and database record creation. Returns filename if uploaded, None otherwise."""
    if not file or not file.filename:
        return None
    root = Path(current_app.config["UPLOAD_CASES_ROOT"])
    subdir = file_safe_case_number(case.case_number)
    try:
        dest = save_upload(file, root, "cases", subdir)
    except exceptions.BadRequest:
        raise
    except Exception as e:  # noqa: BLE001
        current_app.logger.error(f"File save failed: {e}")
        flash("A fájl mentése nem sikerült.", "danger")
        return None
    rec = UploadedFile(
        case_id=case.id,
        filename=dest.name,
        uploader=current_user.screen_name or current_user.username,
        upload_time=now_utc(),
        category=category,
    )
    db.session.add(rec)
    return dest.name


def is_expert_for_case(user, case):
    ident = user.screen_name or user.username
    return ident in (case.expert_1, case.expert_2)


def is_describer_for_case(user, case):
    ident = user.screen_name or user.username
    return ident == case.describer


@main_bp.app_errorhandler(413)
def _too_large(e):  # noqa: ARG001
    # Tests only check the status code; keep it minimal.
    return "", 413


def _max_upload_bytes():
    """Return max upload size in bytes, defaulting to 16MB if not configured or set to a non-number/None."""
    val = current_app.config.get("MAX_CONTENT_LENGTH", None)
    try:
        if val is None:
            return 16 * 1024 * 1024
        return int(val)
    except Exception:  # noqa: BLE001
        return 16 * 1024 * 1024


def enforce_upload_size_limit():
    """Abort with 413 if request exceeds configured/upload size limit."""
    cl = request.content_length
    if cl is not None and cl > _max_upload_bytes():
        abort(413)


@main_bp.route("/ugyeim")
@login_required
@roles_required("szakértő")
def ugyeim():
    ident = current_user.screen_name or current_user.username
    cases = (
        Case.query.filter(or_(Case.expert_1 == ident, Case.expert_2 == ident))
        .filter(Case.status != "boncolva-leírónál")
        .order_by(Case.id.desc())
        .all()
    )
    for case in cases:
        attach_case_dates(case)

    investigations = (
        Investigation.query.filter(
            or_(
                Investigation.expert1_id == current_user.id,
                Investigation.expert2_id == current_user.id,
            )
        )
        .order_by(Investigation.id.desc())
        .all()
    )
    for inv in investigations:
        inv.deadline_str = fmt_date(getattr(inv, "deadline", None))

    return render_template(
        "ugyeim.html",
        cases=cases,
        investigations=investigations,
        page_title="Elvégzendő",
    )


@main_bp.before_app_request
def _enforce_global_upload_cap():
    # Only check multipart POSTs
    if request.method != "POST":
        return
    ct = request.content_type or ""
    if "multipart/form-data" not in ct:
        return

    limit = _max_upload_bytes()

    # Prefer Content-Length if provided by client
    cl = request.content_length
    if cl is not None and cl > limit:
        abort(413)

    # Fallback: inspect uploaded files (Werkzeug FileStorage)
    try:
        for fs in request.files.values():
            size = getattr(fs, "content_length", None)
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


@main_bp.route("/cases/<int:case_id>/mark_tox_viewed")
@login_required
@roles_required("szakértő")
def mark_tox_viewed(case_id):
    case = db.session.get(Case, case_id) or abort(404)
    if (
        resp := ensure_unlocked_or_redirect(case, "auth.case_detail", case_id=case.id)
    ) is not None:
        return resp
    if not is_expert_for_case(current_user, case):
        abort(403)
    if not case.tox_ordered:
        flash("Nincs toxikológiai vizsgálat elrendelve.", "warning")
        return redirect(url_for("auth.case_detail", case_id=case.id))

    case.tox_viewed_by_expert = True
    ts = now_utc()
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
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        current_app.logger.error(f"Database error: {e}")
        return jsonify({"error": "DB error"}), 500

    flash("Toxikológiai végzés megtekintve.", "success")
    return redirect(url_for("main.elvegzem", case_id=case.id))


@main_bp.route("/ugyeim/<int:case_id>/elvegzem", methods=["GET", "POST"])
@login_required
@roles_required("szakértő", "leíró")
def elvegzem(case_id):
    entity = request.args.get("type")
    if entity == "investigation":
        inv = db.session.get(Investigation, case_id) or abort(404)

        if canonical_role(getattr(current_user, "role", None)) != "szakértő":
            abort(403)

        assigned_ids = {inv.expert1_id, inv.expert2_id}
        if current_user.id not in assigned_ids:
            flash("Nincs jogosultságod az ügy elvégzéséhez.", "danger")
            return redirect(url_for("main.ugyeim"))

        return redirect(url_for("investigations.detail_investigation", id=inv.id))

    case = db.session.get(Case, case_id)
    if case is None:
        inv = db.session.get(Investigation, case_id)
        if inv is None:
            abort(404)

        if canonical_role(getattr(current_user, "role", None)) != "szakértő":
            abort(403)

        assigned_ids = {inv.expert1_id, inv.expert2_id}
        if current_user.id not in assigned_ids:
            flash("Nincs jogosultságod az ügy elvégzéséhez.", "danger")
            return redirect(url_for("main.ugyeim"))

        return redirect(url_for("investigations.detail_investigation", id=inv.id))

    attach_case_dates(case)

    # Authorization
    if current_user.role == "szakértő":
        if not is_expert_for_case(current_user, case):
            flash("Nincs jogosultságod az ügy elvégzéséhez.", "danger")
            return redirect(url_for("main.ugyeim"))
    else:
        if not is_describer_for_case(current_user, case):
            flash("Nincs jogosultságod az ügy elvégzéséhez.", "danger")
            return redirect(url_for("main.leiro_ugyeim"))

    if current_user.role == "szakértő" and not case.started_by_expert:
        case.started_by_expert = True
        try:
            db.session.commit()
        except Exception as e:  # noqa: BLE001
            db.session.rollback()
            current_app.logger.error(f"Database error: {e}")

    if request.method == "POST":
        if (
            current_user.role == "szakértő"
            and case.tox_ordered
            and not case.tox_viewed_by_expert
        ):
            flash("Meg kell tekintenie a végzést", "warning")
            return redirect(url_for("main.elvegzem", case_id=case.id))
        # 1) Chat-style note
        new_note = request.form.get("new_note", "").strip()
        note_added = False
        if new_note:
            append_note(case, new_note)
            note_added = True

        # 2) File upload
        enforce_upload_size_limit()
        f = request.files.get("result_file")
        category = (request.form.get("category") or "").strip()
        if f and (not category or not is_valid_category(category)):
            flash("Kategória megadása kötelező.", "danger")
            return redirect(url_for("main.elvegzem", case_id=case.id))
        file_uploaded = handle_file_upload(case, f, category=category) if f else None

        # 3) Halotti bizonyítvány mezők
        who = request.form.get("halalt_megallap")
        case.halalt_megallap_pathologus = who == "pathologus"
        case.halalt_megallap_kezeloorvos = who == "kezeloorvos"
        case.halalt_megallap_mas_orvos = who == "mas_orvos"

        bonc = request.form.get("boncolas_tortent")
        case.boncolas_tortent = bonc == "igen"

        further = request.form.get("varhato_tovabbi_vizsgalat")
        case.varhato_tovabbi_vizsgalat = further == "igen"
        case.kozvetlen_halalok = request.form.get("kozvetlen_halalok") or None
        case.kozvetlen_halalok_ido = request.form.get("kozvetlen_halalok_ido") or None
        case.alapbetegseg_szovodmenyei = (
            request.form.get("alapbetegseg_szovodmenyei") or None
        )
        case.alapbetegseg_szovodmenyei_ido = (
            request.form.get("alapbetegseg_szovodmenyei_ido") or None
        )
        case.alapbetegseg = request.form.get("alapbetegseg") or None
        case.alapbetegseg_ido = request.form.get("alapbetegseg_ido") or None
        case.kiserobetegsegek = request.form.get("kiserobetegsegek") or None

        # 4) Status transition
        previous_status = case.status
        case.status = (
            "boncolva-leírónál" if current_user.role == "szakértő" else "leiktatva"
        )

        try:
            db.session.commit()
        except Exception as e:  # noqa: BLE001
            db.session.rollback()
            current_app.logger.error(f"Database error: {e}")
            flash("Valami hiba történt. Próbáld újra.", "danger")
            return redirect(request.referrer or url_for("main.ugyeim"))
        if note_added:
            flash("Megjegyzés hozzáadva.", "success")
        if file_uploaded:
            flash(f"Fájl feltöltve: {file_uploaded}", "success")
        if previous_status != case.status:
            flash("Művelet sikeresen rögzítve.", "success")
        return redirect(
            url_for("main.ugyeim")
            if current_user.role == "szakértő"
            else url_for("main.leiro_ugyeim")
        )

    # GET: choose template & build context
    template = (
        "elvegzem_szakerto.html"
        if current_user.role == "szakértő"
        else "elvegzem_leiro.html"
    )

    ctx = build_case_context(case)
    ctx["case"] = case
    for entry in ctx.get("changelog_entries", []):
        entry.timestamp_str = safe_fmt(entry.timestamp)
    vegzes_file = next(
        (f for f in case.uploaded_file_records if f.category == "végzés"), None
    )
    ctx["vegzes_file"] = vegzes_file
    if current_user.role == "szakértő":
        leiro_users = User.query.filter_by(role="leíró").order_by(User.username).all()
        leiro_choices = [("", "(válasszon)")] + [
            (u.username, u.screen_name or u.username) for u in leiro_users
        ]
        ctx["leiro_users"] = leiro_users
        ctx["leiro_choices"] = leiro_choices

    return render_template(template, **ctx)


@main_bp.route("/ugyeim/<int:case_id>/vizsgalat_elrendelese", methods=["GET", "POST"])
@login_required
@roles_required("szakértő", "iroda")
def vizsgalat_elrendelese(case_id):
    case = db.session.get(Case, case_id) or abort(404)
    if current_user.role == "szakértő" and not is_expert_for_case(current_user, case):
        flash("Nincs jogosultságod vizsgálatot elrendelni.", "danger")
        return redirect(url_for("main.ugyeim"))

    if request.method == "POST":
        # Use local Budapest time and the username for logging toxicology orders
        now = fmt_budapest(now_utc())
        author = current_user.username
        redirect_target = (
            url_for("auth.edit_case", case_id=case.id)
            if current_user.role == "iroda"
            else url_for("main.elvegzem", case_id=case.id)
        )
        lines = []

        # Tox text fields with checkbox state
        for label, field in [
            ("Alkohol vér", "alkohol_ver"),
            ("Alkohol vizelet", "alkohol_vizelet"),
            ("Alkohol liquor", "alkohol_liquor"),
            ("Egyéb alkohol", "egyeb_alkohol"),
            ("Gyógyszer vér", "tox_gyogyszer_ver"),
            ("Gyógyszer vizelet", "tox_gyogyszer_vizelet"),
            ("Gyógyszer gyomortartalom", "tox_gyogyszer_gyomor"),
            ("Gyógyszer máj", "tox_gyogyszer_maj"),
            ("Kábítószer vér", "tox_kabitoszer_ver"),
            ("Kábítószer vizelet", "tox_kabitoszer_vizelet"),
            ("CPK", "tox_cpk"),
            ("Szárazanyagtartalom", "tox_szarazanyag"),
            ("Diatóma", "tox_diatoma"),
            ("CO", "tox_co"),
            ("Egyéb toxikológia", "egyeb_tox"),
        ]:
            val = (request.form.get(field) or "").strip()
            ordered = request.form.get(f"{field}_ordered") == "on"
            already = getattr(case, f"{field}_ordered")
            if already:
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
            ("sziv", "Szív"),
            ("tudo", "Tüdő"),
            ("maj", "Máj"),
            ("vese", "Vese"),
            ("agy", "Agy"),
            ("mellekvese", "Mellékvese"),
            ("pajzsmirigy", "Pajzsmirigy"),
            ("hasnyalmirigy", "Hasnyálmirigy"),
            ("lep", "Lép"),
        ]:
            markers = request.form.getlist(f"{organ}_marker")
            spec = "spec" in markers
            immun = "immun" in markers
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
                lines.append(f"{label} – {', '.join(badge)} rendelve: {now} – {author}")

        # Egyéb szerv
        egyeb_szerv = request.form.get("egyeb_szerv")
        markers = request.form.getlist("egyeb_szerv_marker")
        prev_spec = case.egyeb_szerv_spec
        prev_immun = case.egyeb_szerv_immun
        if not prev_spec and not prev_immun:
            case.egyeb_szerv = egyeb_szerv or None
            spec = "spec" in markers
            immun = "immun" in markers
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
            except Exception as e:  # noqa: BLE001
                db.session.rollback()
                current_app.logger.error(f"Database error: {e}")
                flash("Valami hiba történt. Próbáld újra.", "danger")
                return redirect(redirect_target)
            flash("Vizsgálatok elrendelve.", "success")
        else:
            flash("Nem választottál ki vizsgálatot.", "warning")

        return redirect(redirect_target)

    return render_template("vizsgalat.html", case=case)


@main_bp.route("/ugyeim/<int:case_id>/upload_elvegzes_files", methods=["POST"])
@login_required
@roles_required("szakértő")
def upload_elvegzes_files(case_id):
    enforce_upload_size_limit()
    case = db.session.get(Case, case_id) or abort(404)
    if not is_expert_for_case(current_user, case):
        flash("Nincs jogosultságod fájlokat feltölteni.", "danger")
        return redirect(url_for("main.elvegzem", case_id=case.id))

    files = request.files.getlist("extra_files")
    if not files:
        flash("Nincs kiválasztott fájl.", "warning")
        return redirect(url_for("main.elvegzem", case_id=case.id))

    saved = []
    category = (request.form.get("category") or "").strip()
    if not category or not is_valid_category(category):
        flash("Kategória megadása kötelező.", "danger")
        return redirect(url_for("main.elvegzem", case_id=case.id))
    for f in files:
        fn = handle_file_upload(case, f, category=category)
        if fn:
            saved.append(fn)

    if saved:
        try:
            db.session.commit()
        except Exception as e:  # noqa: BLE001
            db.session.rollback()
            current_app.logger.error(f"Database error: {e}")
            flash("Valami hiba történt. Próbáld újra.", "danger")
            return redirect(url_for("main.elvegzem", case_id=case.id))
        flash(f"Feltöltve: {', '.join(saved)}", "success")

    return redirect(url_for("main.elvegzem", case_id=case.id))


@main_bp.route("/leiro/ugyeim")
@login_required
@roles_required("leíró")
def leiro_ugyeim():
    ident_screen = (current_user.screen_name or "").strip().lower()
    ident_username = (current_user.username or "").strip().lower()
    identifiers = tuple({ident for ident in (ident_screen, ident_username) if ident})

    normalized_describer = func.lower(func.trim(Case.describer))
    normalized_expert_1 = func.lower(func.trim(Case.expert_1))
    normalized_expert_2 = func.lower(func.trim(Case.expert_2))

    normalized_user_screen = func.lower(func.trim(User.screen_name))
    normalized_user_username = func.lower(func.trim(User.username))

    empty_describer = or_(Case.describer.is_(None), func.trim(Case.describer) == "")

    expert_links = or_(
        or_(
            normalized_user_screen == normalized_expert_1,
            normalized_user_username == normalized_expert_1,
        ),
        or_(
            normalized_user_screen == normalized_expert_2,
            normalized_user_username == normalized_expert_2,
        ),
    )

    default_leiro_exists = (
        db.session.query(User.id)
        .filter(User.default_leiro_id == current_user.id)
        .filter(expert_links)
        .exists()
    )

    filters = [and_(empty_describer, default_leiro_exists)]
    if identifiers:
        filters.append(normalized_describer.in_(identifiers))

    combined_filter = or_(*filters) if len(filters) > 1 else filters[0]
    base_q = Case.query.filter(combined_filter)
    pending_statuses = {"szignálva", "boncolva-leírónál"}
    pending = (
        base_q.filter(Case.status.in_(pending_statuses))
        .order_by(Case.case_number.desc())
        .all()
    )
    completed = (
        base_q.filter(Case.status == "leiktatva")
        .order_by(Case.case_number.desc())
        .all()
    )
    for case in pending + completed:
        attach_case_dates(case)
    return render_template(
        "leiro_ugyeim.html", pending_cases=pending, completed_cases=completed
    )


@main_bp.route("/ugyeim/toxi")
@login_required
@roles_required("toxi")
def toxi_ugyeim():
    """Dashboard for toxicology specialists."""
    vegzes_exists = (
        db.session.query(UploadedFile.id)
        .filter(UploadedFile.case_id == Case.id, UploadedFile.category == "végzés")
        .exists()
    )

    pending_filter = or_(Case.tox_completed.is_(False), Case.tox_completed.is_(None))

    assigned_cases = Case.query.filter(pending_filter, vegzes_exists).all()
    done_cases = Case.query.filter(Case.tox_completed.is_(True), vegzes_exists).all()
    for case in assigned_cases + done_cases:
        attach_case_dates(case)

    return render_template(
        "toxi_ugyeim.html",
        assigned_cases=assigned_cases,
        done_cases=done_cases,
    )


@main_bp.route("/elvegzem_toxi/<int:case_id>", methods=["GET", "POST"])
@login_required
@roles_required("toxi")
def elvegzem_toxi(case_id):
    case = db.session.get(Case, case_id) or abort(404)

    if case.tox_expert and case.tox_expert != current_user.screen_name:
        flash("Nincs jogosultságod az ügy elvégzéséhez.", "danger")
        return redirect(url_for("main.toxi_ugyeim"))

    if request.method == "POST":
        note = request.form.get("new_note", "").strip()
        if note:
            append_note(case, note)
        case.tox_expert = current_user.screen_name or current_user.username
        case.tox_completed = True
        try:
            db.session.commit()
        except Exception as e:  # noqa: BLE001
            db.session.rollback()
            current_app.logger.error(f"Database error: {e}")
            flash("Valami hiba történt. Próbáld újra.", "danger")
            return redirect(url_for("main.elvegzem_toxi", case_id=case.id))
        flash("✔️ Toxikológiai vizsgálat elvégezve.", "success")
        return redirect(url_for("main.toxi_ugyeim"))

    attach_case_dates(case)
    return render_template("elvegzem_toxi.html", case=case)


@main_bp.route("/leiro/ugyeim/<int:case_id>/elvegzem", methods=["GET", "POST"])
@login_required
@roles_required("leíró")
def leiro_elvegzem(case_id):
    case = db.session.get(Case, case_id) or abort(404)
    if (
        resp := ensure_unlocked_or_redirect(case, "auth.case_detail", case_id=case.id)
    ) is not None:
        return resp
    if not is_describer_for_case(current_user, case):
        flash("Nincs jogosultságod az ügy elvégzéséhez.", "danger")
        return redirect(url_for("main.leiro_ugyeim"))
    if case.status != "boncolva-leírónál":
        flash("Az ügy nincs a leírónál.", "warning")
        return redirect(url_for("auth.case_detail", case_id=case.id))

    if request.method == "POST":
        # 1) Handle file upload
        enforce_upload_size_limit()
        file = request.files.get("result_file")
        category = (request.form.get("category") or "").strip()
        if file and (not category or not is_valid_category(category)):
            flash("Kategória megadása kötelező.", "danger")
            return redirect(url_for("main.leiro_elvegzem", case_id=case.id))
        file_uploaded = handle_file_upload(case, file, category=category)

        # 2) Add any new note
        new_note = request.form.get("new_note", "").strip()
        if new_note:
            append_note(case, new_note)

        # 3) Mark the case as completed by the describer
        case.status = "leiktatva"
        try:
            db.session.commit()
        except Exception as e:  # noqa: BLE001
            db.session.rollback()
            current_app.logger.error(f"Database error: {e}")
            flash("Valami hiba történt. Próbáld újra.", "danger")
            return redirect(url_for("main.leiro_elvegzem", case_id=case.id))

        if file_uploaded:
            flash(f"Fájl feltöltve: {file_uploaded}", "success")
        if new_note:
            flash("Megjegyzés hozzáadva.", "success")
        flash("Ügy elvégzése sikeresen rögzítve.", "success")
        return redirect(url_for("main.leiro_ugyeim"))

    changelog_entries = (
        ChangeLog.query.filter_by(case_id=case.id)
        .order_by(ChangeLog.timestamp.desc())
        .all()
    )
    return render_template(
        "elvegzem_leiro.html", case=case, changelog_entries=changelog_entries
    )


@main_bp.route("/ugyeim/<int:case_id>/assign_describer", methods=["POST"])
@login_required
@roles_required("szakértő")
def assign_describer(case_id):
    data = request.get_json() or {}
    case = db.session.get(Case, case_id) or abort(404)
    if is_final_status(case.status):
        return jsonify({"error": "Az ügy lezárva"}), 409
    if not case.started_by_expert:
        return jsonify({"error": "Szakértői munka nem indult"}), 409
    describer = data.get("describer")
    key = make_default_key(request)
    if not claim_idempotency(
        key, route=request.endpoint, user_id=current_user.id, case_id=case.id
    ):
        return jsonify({"error": "Művelet már feldolgozva"}), 409
    if describer == case.describer:
        return jsonify({"message": "nincs változás"}), 200
    case.describer = describer
    try:
        db.session.commit()
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        current_app.logger.error(f"Database error: {e}")
        return jsonify({"error": "DB error"}), 500
    flash("Leíró sikeresen hozzárendelve.", "success")
    return ("", 204)


@main_bp.route("/leiro/ugyeim/<int:case_id>/upload_file", methods=["POST"])
@login_required
@roles_required("leíró")
def leiro_upload_file(case_id):
    enforce_upload_size_limit()
    case = db.session.get(Case, case_id) or abort(404)
    if not is_describer_for_case(current_user, case):
        flash("Nincs jogosultságod!", "danger")
        return redirect(url_for("main.leiro_elvegzem", case_id=case.id))

    file = request.files.get("result_file")
    category = (request.form.get("category") or "").strip()
    if not category or not is_valid_category(category):
        flash("Kategória megadása kötelező.", "danger")
        return redirect(url_for("main.leiro_elvegzem", case_id=case.id))
    file_uploaded = handle_file_upload(case, file, category=category)
    if not file_uploaded:
        flash("Nincs kiválasztott fájl.", "warning")
        return redirect(url_for("main.leiro_elvegzem", case_id=case.id))

    try:
        db.session.commit()
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        current_app.logger.error(f"Database error: {e}")
        flash("Valami hiba történt. Próbáld újra.", "danger")
        return redirect(url_for("main.leiro_elvegzem", case_id=case.id))
    flash(f"Fájl feltöltve: {file_uploaded}", "success")
    return redirect(url_for("main.leiro_elvegzem", case_id=case.id))


@main_bp.route("/ugyeim/<int:case_id>/generate_certificate", methods=["POST"])
@login_required
@roles_required("szakértő")
def generate_certificate(case_id):
    """Generate death certificate text file in the exact format tests expect."""
    case = db.session.get(Case, case_id) or abort(404)
    if (
        resp := ensure_unlocked_or_redirect(case, "auth.case_detail", case_id=case.id)
    ) is not None:
        return resp

    if not is_expert_for_case(current_user, case):
        abort(403)

    key = make_default_key(request)
    if not claim_idempotency(
        key, route=request.endpoint, user_id=current_user.id, case_id=case.id
    ):
        flash("Művelet már feldolgozva.")
        return redirect(url_for("main.elvegzem", case_id=case.id))

    root = Path(current_app.config["UPLOAD_CASES_ROOT"])

    f = request.form

    def get_value(k: str) -> str:
        return (f.get(k) or "").strip()

    lines = [
        f"Ügy: {case.case_number}",
        "",
        f"A halál okát megállapította: {get_value('halalt_megallap')}",
        "",
        f"Történt-e boncolás: {get_value('boncolas_tortent')}",
        f"Ha igen, várhatók-e további vizsgálati eredmények: {get_value('varhato_tovabbi_vizsgalat')}",
        "",
        f"Közvetlen halálok: {get_value('kozvetlen_halalok')}",
        f"Esemény kezdete és halál között eltelt idő: {get_value('kozvetlen_halalok_ido')}",
        "",
        f"Alapbetegség szövődményei: {get_value('alapbetegseg_szovodmenyei')}",
        f"Esemény kezdete és halál között eltelt idő: {get_value('alapbetegseg_szovodmenyei_ido')}",
        "",
        f"Alapbetegség: {get_value('alapbetegseg')}",
        f"Esemény kezdete és halál között eltelt idő: {get_value('alapbetegseg_ido')}",
        "",
        f"Kísérő betegségek vagy állapotok: {get_value('kiserobetegsegek')}",
    ]

    dest = resolve_safe(
        root,
        file_safe_case_number(case.case_number),
        f"halottvizsgalati_bizonyitvany-{file_safe_case_number(case.case_number)}.txt",
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))

    case.certificate_generated = True
    case.certificate_generated_at = now_utc()
    db.session.commit()

    flash("Bizonyítvány generálva.", "success")
    return redirect(url_for("main.elvegzem", case_id=case.id))


@main_bp.route("/cases/<int:case_id>/complete_expert", methods=["POST"])
@login_required
@roles_required("szakértő", "admin")
def complete_expert(case_id):
    case = db.session.get(Case, case_id)
    if case is None:
        abort(404)

    case.status = "boncolva-leírónál"
    append_note(case, "Szakértő elvégezte a boncolást.")
    db.session.commit()

    flash("Szakértői vizsgálat elvégezve.")
    return redirect(url_for("main.ugyeim"))
