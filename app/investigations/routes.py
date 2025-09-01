# app/investigations/routes.py

from datetime import timedelta
from pathlib import Path

from flask import (
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
from sqlalchemy import func, or_, text
from werkzeug import exceptions

from app import db
from app.paths import ensure_investigation_folder, investigation_subdir_from_case_number
from app.services.core_user_read import get_user_safe
from app.utils.dates import safe_fmt
from app.utils.permissions import capabilities_for
from app.utils.rbac import require_roles as roles_required
from app.utils.time_utils import fmt_date, now_local
from app.utils.uploads import save_upload, send_safe

from . import investigations_bp
from .forms import FileUploadForm, InvestigationForm, InvestigationNoteForm
from .models import (
    Investigation,
    InvestigationAttachment,
    InvestigationChangeLog,
    InvestigationNote,
)
from .utils import (
    generate_case_number,
    init_investigation_upload_dirs,
    user_display_name,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _can_modify(inv, user) -> bool:
    return user.role in {"admin", "iroda"}


def _can_note_or_upload(inv, user) -> bool:
    if user.role in {"admin", "iroda"}:
        return True
    return user.id in {inv.expert1_id, inv.expert2_id, inv.describer_id}


def _log_changes(inv: Investigation, form: InvestigationForm):
    fields = [
        "subject_name",
        "maiden_name",
        "mother_name",
        "birth_place",
        "birth_date",
        "taj_number",
        "residence",
        "citizenship",
        "institution_name",
        "investigation_type",
        "external_case_number",
        "other_identifier",
    ]
    logs = []
    for field in fields:
        new_val = getattr(form, field).data
        old_val = getattr(inv, field)
        if old_val != new_val:
            setattr(inv, field, new_val)
            logs.append(
                InvestigationChangeLog(
                    investigation_id=inv.id,
                    field_name=field,
                    old_value=str(old_val) if old_val is not None else None,
                    new_value=str(new_val) if new_val is not None else None,
                    edited_by=current_user.id,
                    timestamp=now_local(),
                )
            )
    return logs


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@investigations_bp.route("/")
@login_required
@roles_required("admin", "iroda", "szakértő", "pénzügy")
def list_investigations():
    search = (request.args.get("search") or request.args.get("q") or "").strip()
    case_type = request.args.get("case_type", "").strip()
    sort_by = request.args.get("sort_by", "case_number")
    sort_order = request.args.get("sort_order", "asc")
    page = request.args.get("page", 1, type=int)
    per_page = 25

    query = Investigation.query

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Investigation.case_number.ilike(like),
                Investigation.external_case_number.ilike(like),
                Investigation.other_identifier.ilike(like),
                Investigation.taj_number.ilike(like),
                Investigation.subject_name.ilike(like),
                Investigation.maiden_name.ilike(like),
                Investigation.mother_name.ilike(like),
                Investigation.birth_place.ilike(like),
                Investigation.residence.ilike(like),
                Investigation.citizenship.ilike(like),
                Investigation.investigation_type.ilike(like),
                Investigation.institution_name.ilike(like),
                func.strftime("%Y-%m-%d", Investigation.birth_date).like(like),
                func.strftime("%Y", Investigation.birth_date).like(like),
            )
        )

    if case_type:
        query = query.filter(Investigation.investigation_type == case_type)

    order_col = {
        "case_number": Investigation.case_number,
        "deadline": Investigation.deadline,
    }.get(sort_by, Investigation.id)

    query = query.order_by(
        order_col.desc() if sort_order == "desc" else order_col.asc()
    )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    investigations = pagination.items

    for inv in investigations:
        inv.registration_time_str = fmt_date(inv.registration_time)
        inv.deadline_str = fmt_date(inv.deadline)
        inv.expert1_name = user_display_name(get_user_safe(inv.expert1_id))
        inv.expert2_name = user_display_name(get_user_safe(inv.expert2_id))
        inv.describer_name = user_display_name(get_user_safe(inv.describer_id))

    has_edit_investigation = (
        "investigations.edit_investigation" in current_app.view_functions
    )

    return render_template(
        "investigations/list.html",
        investigations=investigations,
        pagination=pagination,
        sort_by=sort_by,
        sort_order=sort_order,
        case_type_filter=case_type,
        search_query=search,
        query_params=request.args.to_dict(),
        has_edit_investigation=has_edit_investigation,
        caps=capabilities_for(current_user),
    )


@investigations_bp.route("/new", methods=["GET", "POST"])
@login_required
@roles_required("admin", "iroda")
def new_investigation():
    form = InvestigationForm()

    experts = db.session.execute(
        text(
            "SELECT id, screen_name, username FROM user "
            "WHERE role IN ('szakértő', 'szak') ORDER BY screen_name, username"
        )
    ).all()
    form.assigned_expert_id.choices = [(0, "— Válasszon —")] + [
        (row.id, row.screen_name or row.username) for row in experts
    ]

    if form.validate_on_submit():
        assignment_type = form.assignment_type.data
        assigned_expert_id = (
            form.assigned_expert_id.data if assignment_type == "SZAKÉRTŐI" else None
        )
        inv = Investigation(
            subject_name=form.subject_name.data,
            maiden_name=(
                getattr(form, "maiden_name", None).data
                if hasattr(form, "maiden_name")
                else None
            ),
            mother_name=form.mother_name.data,
            birth_place=form.birth_place.data,
            birth_date=form.birth_date.data,
            taj_number=form.taj_number.data,
            residence=form.residence.data,
            citizenship=form.citizenship.data,
            institution_name=form.institution_name.data,
            investigation_type=form.investigation_type.data,
            external_case_number=form.external_case_number.data,
            other_identifier=form.other_identifier.data,
            assignment_type=assignment_type,
            assigned_expert_id=assigned_expert_id,
        )
        inv.case_number = generate_case_number(db.session)  # V-####-YYYY
        inv.registration_time = now_local()
        inv.deadline = inv.registration_time + timedelta(days=30)

        db.session.add(inv)
        db.session.commit()

        # Create per-investigation folder (separate from Cases)
        ensure_investigation_folder(inv.case_number)
        init_investigation_upload_dirs(inv.case_number)

        flash("Vizsgálat létrehozva.", "success")
        # Go straight to the Investigations Documents page
        return redirect(url_for("investigations.documents", id=inv.id))
    elif request.method == "POST":
        for errs in form.errors.values():
            for err in errs:
                flash(err)
        if current_app.config.get("STRICT_PRG_ENABLED", True):
            return redirect(url_for("investigations.new_investigation"))

    return render_template("investigations/new.html", form=form)


@investigations_bp.route("/<int:id>/documents", methods=["GET"])
@login_required
@roles_required("admin", "iroda", "szakértő")
def documents(id):
    inv = db.session.get(Investigation, id)
    if inv is None:
        abort(404)

    attachments = (
        InvestigationAttachment.query.filter_by(investigation_id=id)
        .order_by(InvestigationAttachment.uploaded_at.desc())
        .all()
    )
    for att in attachments:
        att.uploaded_at_str = safe_fmt(att.uploaded_at)
    for att in attachments:
        att.uploaded_at_str = att.uploaded_at.strftime("%Y.%m.%d %H:%M")

    upload_form = FileUploadForm()
    return render_template(
        "investigations/documents.html",
        investigation=inv,
        attachments=attachments,
        upload_form=upload_form,
        upload_url=url_for("investigations.upload_investigation_file", id=inv.id),
    )


@investigations_bp.route("/<int:id>/view")
@login_required
@roles_required("admin", "iroda", "szakértő", "pénzügy")
def view_investigation(id):
    inv = db.session.get(Investigation, id)
    if inv is None:
        abort(404)

    attachments = (
        InvestigationAttachment.query.filter_by(investigation_id=id)
        .order_by(InvestigationAttachment.uploaded_at.desc())
        .all()
    )

    notes = (
        InvestigationNote.query.filter_by(investigation_id=id)
        .order_by(InvestigationNote.timestamp.desc())
        .all()
    )
    for note in notes:
        note.author = get_user_safe(note.author_id)
        note.timestamp_str = safe_fmt(note.timestamp)

    changelog_entries = (
        InvestigationChangeLog.query.filter_by(investigation_id=id)
        .order_by(InvestigationChangeLog.timestamp.desc())
        .all()
    )
    for entry in changelog_entries:
        entry.edited_by = user_display_name(get_user_safe(entry.edited_by))
        entry.timestamp_str = safe_fmt(entry.timestamp)

    assigned_expert = get_user_safe(inv.assigned_expert_id)
    inv.registration_time_str = safe_fmt(inv.registration_time)
    inv.deadline_str = safe_fmt(inv.deadline)

    return render_template(
        "investigations/view.html",
        investigation=inv,
        attachments=attachments,
        notes=notes,
        assigned_expert=assigned_expert,
        changelog_entries=changelog_entries,
        user_display_name=user_display_name,
        caps=capabilities_for(current_user),
    )


@investigations_bp.route("/<int:id>")
@login_required
@roles_required("admin", "iroda", "szakértő", "pénzügy")
def detail_investigation(id):
    inv = db.session.get(Investigation, id)
    if inv is None:
        abort(404)
    form = InvestigationForm(obj=inv)
    note_form = InvestigationNoteForm()
    upload_form = FileUploadForm()
    inv.birth_date_str = fmt_date(inv.birth_date)
    inv.registration_time_str = fmt_date(inv.registration_time)
    inv.deadline_str = fmt_date(inv.deadline)
    notes = (
        InvestigationNote.query.filter_by(investigation_id=id)
        .order_by(InvestigationNote.timestamp.desc())
        .all()
    )
    attachments = (
        InvestigationAttachment.query.filter_by(investigation_id=id)
        .order_by(InvestigationAttachment.uploaded_at.desc())
        .all()
    )
    for note in notes:
        note.timestamp_str = note.timestamp.strftime("%Y.%m.%d %H:%M")
        note.author = get_user_safe(note.author_id)
    for att in attachments:
        att.uploaded_at_str = att.uploaded_at.strftime("%Y.%m.%d %H:%M")
    changelog = (
        InvestigationChangeLog.query.filter_by(investigation_id=id)
        .order_by(InvestigationChangeLog.timestamp.desc())
        .all()
    )
    for log in changelog:
        log.timestamp_str = log.timestamp.strftime("%Y.%m.%d %H:%M")
        log.editor = get_user_safe(log.edited_by)
    return render_template(
        "investigations/detail.html",
        investigation=inv,
        form=form,
        note_form=note_form,
        upload_form=upload_form,
        notes=notes,
        attachments=attachments,
        changelog=changelog,
        user_display_name=user_display_name,
        caps=capabilities_for(current_user),
    )


@investigations_bp.route("/<int:id>/edit", methods=["POST"])
@login_required
@roles_required("admin", "iroda")
def edit_investigation(id):
    inv = db.session.get(Investigation, id)
    if inv is None:
        abort(404)
    caps = capabilities_for(current_user)
    if not caps.get("can_edit_investigation"):
        flash("Nincs jogosultság", "danger")
        return redirect(url_for("investigations.detail_investigation", id=id))
    form = InvestigationForm()
    if not form.validate_on_submit():
        flash("Hibás űrlap", "error")
        return redirect(url_for("investigations.detail_investigation", id=id))
    logs = _log_changes(inv, form)
    db.session.add_all(logs)
    db.session.commit()
    flash("Vizsgálat frissítve.", "success")
    return redirect(url_for("investigations.detail_investigation", id=id))


@investigations_bp.route("/<int:id>/notes", methods=["POST"])
@login_required
@roles_required("admin", "iroda", "szakértő")
def add_investigation_note(id):
    inv = db.session.get(Investigation, id)
    if inv is None:
        abort(404)
    caps = capabilities_for(current_user)
    if not caps.get("can_post_investigation_notes"):
        abort(403)
    if current_user.role not in {"admin", "iroda"} and current_user.id not in {
        inv.expert1_id,
        inv.expert2_id,
        inv.describer_id,
    }:
        abort(403)

    form = InvestigationNoteForm()
    text = None
    if form.validate_on_submit():
        text = form.text.data
    else:
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Empty note"}), 400

    note = InvestigationNote(
        investigation_id=inv.id, author_id=current_user.id, text=text
    )
    db.session.add(note)
    db.session.commit()

    # ensure author is available for the partial
    author = get_user_safe(note.author_id)
    note.timestamp_str = note.timestamp.strftime("%Y.%m.%d %H:%M")

    html = render_template(
        "investigations/_note.html",
        note=note,
        author=author,
        user_display_name=user_display_name,
    )
    return html


@investigations_bp.route("/<int:id>/upload", methods=["POST"])
@login_required
@roles_required("admin", "iroda", "szakértő")
def upload_investigation_file(id):
    inv = db.session.get(Investigation, id)
    if inv is None:
        abort(404)
    caps = capabilities_for(current_user)
    if not caps.get("can_upload_investigation"):
        abort(403)
    if current_user.role not in {"admin", "iroda"} and current_user.id not in {
        inv.expert1_id,
        inv.expert2_id,
        inv.describer_id,
    }:
        abort(403)

    form = FileUploadForm()
    if not form.validate_on_submit():
        return jsonify({"error": "invalid"}), 400

    upfile = form.file.data
    root = Path(current_app.config["UPLOAD_INVESTIGATIONS_ROOT"])
    subdir = investigation_subdir_from_case_number(inv.case_number)
    try:
        dest = save_upload(upfile, root, "investigations", subdir)
    except exceptions.BadRequest:
        return jsonify({"error": "forbidden"}), 400
    except Exception as e:
        current_app.logger.error(f"Investigation file save failed: {e}")
        return jsonify({"error": "save-failed"}), 500

    attachment = InvestigationAttachment(
        investigation_id=inv.id,
        filename=dest.name,
        category=form.category.data,
        uploaded_by=current_user.id,
        uploaded_at=now_local(),
    )
    db.session.add(attachment)
    db.session.commit()

    return jsonify(
        {
            "id": attachment.id,
            "filename": attachment.filename,
            "category": attachment.category,
            "uploaded_at": fmt_date(attachment.uploaded_at),
        }
    )


@investigations_bp.route("/<int:id>/files/<path:filename>")
@login_required
@roles_required("admin", "iroda", "szakértő")
def download_investigation_file(id, filename):
    inv = db.session.get(Investigation, id)
    if inv is None:
        abort(404)
    if not _can_note_or_upload(inv, current_user):
        abort(403)

    subdir = investigation_subdir_from_case_number(inv.case_number)
    root = Path(current_app.config["UPLOAD_INVESTIGATIONS_ROOT"]) / subdir
    try:
        return send_safe(root, filename, as_attachment=True)
    except (exceptions.BadRequest, FileNotFoundError):
        abort(404)
