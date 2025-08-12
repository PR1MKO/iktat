from datetime import timedelta
import os

from flask import (
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for
    send_from_directory,
)
from flask_login import current_user, login_required
from sqlalchemy import or_, func
from werkzeug.utils import secure_filename, safe_join

from app import db
from app.models import User  # ← needed for resolving author
from app.utils.roles import roles_required
from app.utils.time_utils import fmt_date, now_local
from . import investigations_bp
from .forms import InvestigationForm, FileUploadForm, InvestigationNoteForm
from .models import (
    Investigation,
    InvestigationNote,
    InvestigationAttachment,
    InvestigationChangeLog,
)
from .utils import generate_case_number, ensure_investigation_folder


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
        "maiden_name",              # ← add this
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
def list_investigations():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 25
    query = Investigation.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Investigation.case_number.ilike(like),
                Investigation.external_case_number.ilike(like),
                Investigation.other_identifier.ilike(like),
                Investigation.subject_name.ilike(like),
                Investigation.maiden_name.ilike(like),
                Investigation.investigation_type.ilike(like),
                Investigation.mother_name.ilike(like),
                Investigation.birth_place.ilike(like),
                func.strftime("%Y-%m-%d", Investigation.birth_date).like(like),
                Investigation.taj_number.ilike(like),
                Investigation.residence.ilike(like),
                Investigation.citizenship.ilike(like),
                Investigation.institution_name.ilike(like),
            )
        )
    pagination = (
        query.order_by(Investigation.id.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    investigations = pagination.items
    for inv in investigations:
        inv.birth_date_str = fmt_date(inv.birth_date)
        inv.registration_time_str = fmt_date(inv.registration_time)
        inv.deadline_str = fmt_date(inv.deadline)
    return render_template(
        "investigations/list.html",
        investigations=investigations,
        q=q,
        pagination=pagination,
    )


@investigations_bp.route("/new", methods=["GET", "POST"])
@login_required
@roles_required("admin", "iroda")
def new_investigation():
    form = InvestigationForm()
    if form.validate_on_submit():
        inv = Investigation(
            subject_name=form.subject_name.data,
            maiden_name=getattr(form, "maiden_name", None).data if hasattr(form, "maiden_name") else None,
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
        )
        inv.case_number = generate_case_number(db.session)  # V-####-YYYY
        inv.registration_time = now_local()
        inv.deadline = inv.registration_time + timedelta(days=30
        
        db.session.add(inv)
        db.session.commit()

        # Create per-investigation folder (separate from Cases)
        ensure_investigation_folder(current_app, inv.case_number)
        
        flash("Vizsgálat létrehozva.", "success")
        # Go straight to the Investigations Documents page
        return redirect(url_for("investigations.documents", id=inv.id))
        
    return render_template("investigations/new.html", form=form)
    
@investigations_bp.route("/<int:id>/documents", methods=["GET"])
@login_required
def documents(id):
    inv = Investigation.query.get_or_404(id)
    folder = ensure_investigation_folder(current_app, inv.case_number)

    attachments = (
        InvestigationAttachment.query
        .filter_by(investigation_id=id)
        .order_by(InvestigationAttachment.uploaded_at.desc())
        .all()
    )
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

@investigations_bp.route("/<int:id>")
@login_required
def detail_investigation(id):
    inv = Investigation.query.get_or_404(id)
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
    for att in attachments:
        att.uploaded_at_str = att.uploaded_at.strftime("%Y.%m.%d %H:%M")
    changelog = (
        InvestigationChangeLog.query.filter_by(investigation_id=id)
        .order_by(InvestigationChangeLog.timestamp.desc())
        .all()
    )
    for log in changelog:
        log.timestamp_str = log.timestamp.strftime("%Y.%m.%d %H:%M")
    return render_template(
        "investigations/detail.html",
        investigation=inv,
        form=form,
        note_form=note_form,
        upload_form=upload_form,
        notes=notes,
        attachments=attachments,
        changelog=changelog,
    )


@investigations_bp.route("/<int:id>/edit", methods=["POST"])
@login_required
@roles_required("admin", "iroda")
def edit_investigation(id):
    inv = Investigation.query.get_or_404(id)
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
def add_investigation_note(id):
    inv = Investigation.query.get_or_404(id)
    if not _can_note_or_upload(inv, current_user):
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
    author = db.session.get(User, note.author_id)
    note.timestamp_str = note.timestamp.strftime("%Y.%m.%d %H:%M")

    html = render_template("investigations/_note.html", note=note, author=author)
    return html


@investigations_bp.route("/<int:id>/upload", methods=["POST"])
@login_required
def upload_investigation_file(id):
    inv = Investigation.query.get_or_404(id)
    if not _can_note_or_upload(inv, current_user):
        abort(403)

    form = FileUploadForm()
    if not form.validate_on_submit():
        return jsonify({"error": "invalid"}), 400

    file = form.file.data
    filename = secure_filename(file.filename)

    folder = ensure_investigation_folder(current_app, inv.case_number)
    file_path = os.path.join(folder, filename)
    file.save(file_path)

    attachment = InvestigationAttachment(
        investigation_id=inv.id,
        filename=filename,
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
def download_investigation_file(id, filename):
    inv = Investigation.query.get_or_404(id)
    if not _can_note_or_upload(inv, current_user):
        abort(403)

    folder = ensure_investigation_folder(current_app, inv.case_number)
    full_path = safe_join(folder, filename)
    if not full_path or not os.path.isfile(full_path):
        abort(404)

    return send_from_directory(folder, os.path.basename(full_path), as_attachment=True)
    
