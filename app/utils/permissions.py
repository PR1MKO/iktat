from __future__ import annotations

from typing import Dict

# Define the set of capabilities used across the application.
_CAP_KEYS = [
    "can_view_cases",
    "can_view_investigations",
    "can_edit_case",
    "can_upload_case",
    "can_assign",
    "can_change_status",
    "can_post_notes",
    "can_download_files",
    "can_edit_investigation",
    "can_upload_investigation",
    "can_post_investigation_notes",
]

# Base capability matrix for existing roles. Values preserve the current
# behaviour seen in routes and templates (e.g. _can_modify/_can_note_or_upload).
_BASE_ROLE_CAPS: Dict[str, Dict[str, bool]] = {
    "admin": {key: True for key in _CAP_KEYS},
    "iroda": {
        "can_view_cases": True,
        "can_view_investigations": True,
        "can_edit_case": True,
        "can_upload_case": True,
        "can_assign": False,
        "can_change_status": True,
        "can_post_notes": True,
        "can_download_files": True,
        "can_edit_investigation": True,
        "can_upload_investigation": True,
        "can_post_investigation_notes": True,
    },
    "szignáló": {
        "can_view_cases": True,
        "can_view_investigations": True,
        "can_edit_case": True,
        "can_upload_case": True,
        "can_assign": True,
        "can_change_status": True,
        "can_post_notes": True,
        "can_download_files": True,
        "can_edit_investigation": False,
        "can_upload_investigation": False,
        "can_post_investigation_notes": False,
    },
    "szakértő": {
        "can_view_cases": True,
        "can_view_investigations": True,
        "can_edit_case": False,
        "can_upload_case": False,
        "can_assign": False,
        "can_change_status": False,
        "can_post_notes": True,
        "can_download_files": True,
        "can_edit_investigation": False,
        "can_upload_investigation": True,
        "can_post_investigation_notes": True,
    },
    "leíró": {
        "can_view_cases": True,
        "can_view_investigations": True,
        "can_edit_case": False,
        "can_upload_case": True,
        "can_assign": False,
        "can_change_status": False,
        "can_post_notes": True,
        "can_download_files": True,
        "can_edit_investigation": False,
        "can_upload_investigation": True,
        "can_post_investigation_notes": True,
    },
    "toxi": {
        "can_view_cases": True,
        "can_view_investigations": True,
        "can_edit_case": False,
        "can_upload_case": True,
        "can_assign": False,
        "can_change_status": False,
        "can_post_notes": True,
        "can_download_files": True,
        "can_edit_investigation": False,
        "can_upload_investigation": False,
        "can_post_investigation_notes": False,
    },
}


def _intersection_caps(matrix: Dict[str, Dict[str, bool]]) -> Dict[str, bool]:
    """Return the intersection (logical AND) of all role capabilities."""
    return {
        cap: all(caps.get(cap, False) for caps in matrix.values()) for cap in _CAP_KEYS
    }


_ROLE_CAPS = dict(_BASE_ROLE_CAPS)
_ROLE_CAPS["pénzügy"] = _intersection_caps(_BASE_ROLE_CAPS)


def capabilities_for(user) -> Dict[str, bool]:
    """Return capability flags for the given user."""
    role = getattr(user, "role", None)
    caps = _ROLE_CAPS.get(role) or _ROLE_CAPS["pénzügy"]
    return dict(caps)
