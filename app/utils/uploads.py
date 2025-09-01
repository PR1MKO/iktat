from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Optional

from flask import abort, current_app, request, send_file
from werkzeug import exceptions
from werkzeug.utils import secure_filename

try:  # optional python-magic
    import magic  # type: ignore
except Exception:  # pragma: no cover - import failure
    magic = None  # type: ignore

ALLOWED_EXTENSIONS = {
    "cases": {"pdf", "jpg", "jpeg", "png", "doc", "docx", "xls", "xlsx"},
    "investigations": {"pdf", "jpg", "jpeg", "png"},
}


def allowed_file(filename: str, domain: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in ALLOWED_EXTENSIONS.get(domain, set())


def resolve_safe(root: Path, *parts: str) -> Path:
    root_resolved = root.resolve()
    p = (root / Path(*parts)).resolve()
    if root_resolved not in p.parents and p != root_resolved:
        raise exceptions.BadRequest("invalid path")
    return p


def guess_mimetype(path: Path) -> str:
    mime: Optional[str] = None
    if magic:  # pragma: no cover - optional
        try:
            mime = magic.from_file(str(path), mime=True)
        except Exception:
            mime = None
    if not mime:
        mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def save_upload(file_storage, root: Path, domain: str, *subdirs: str) -> Path:
    limit = current_app.config.get("MAX_CONTENT_LENGTH")
    if request.content_length and limit and request.content_length > int(limit):
        abort(413)
    filename = secure_filename(file_storage.filename or "")
    if not filename or not allowed_file(filename, domain):
        raise exceptions.BadRequest("forbidden file type")
    # basic MIME sanity
    expected, _ = mimetypes.guess_type(filename)
    if (
        expected
        and file_storage.mimetype
        and file_storage.mimetype not in (expected, "application/octet-stream")
    ):
        raise exceptions.BadRequest("forbidden file type")
    target_dir = resolve_safe(root, *subdirs)
    target_dir.mkdir(parents=True, exist_ok=True)
    dest = resolve_safe(target_dir, filename)
    file_storage.save(str(dest))
    return dest


def send_safe(root: Path, *parts: str, as_attachment: bool = True):
    path = resolve_safe(root, *parts)
    return send_file(path, as_attachment=as_attachment, mimetype=guess_mimetype(path))
