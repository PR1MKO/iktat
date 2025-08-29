import re
from pathlib import Path
from types import SimpleNamespace
from datetime import timedelta

from app.utils.dates import compute_deadline_flags
from app.utils.time_utils import now_local


# --- helpers -----------------------------------------------------------------

_JINJA_BLOCK_RE = re.compile(r"(\{\{.*?\}\}|\{%-?.*?-?%\})", re.DOTALL)

def _iter_jinja_blocks(text: str):
    """Yield (start, end, block_text) for each Jinja expression/statement block."""
    for m in _JINJA_BLOCK_RE.finditer(text):
        yield m.start(), m.end(), m.group(0)

def _line_of_pos(text: str, pos: int) -> int:
    """1-based line number for byte offset pos."""
    return text.count("\n", 0, pos) + 1

def _snippet_around(text: str, line_no: int, context: int = 2) -> str:
    """Return up to ~5 lines of context around the given 1-based line_no."""
    lines = text.splitlines()
    lo = max(0, line_no - 1 - context)
    hi = min(len(lines), line_no - 1 + context + 1)
    return "\n".join(lines[lo:hi])


# --- tests -------------------------------------------------------------------

def test_no_datetime_in_templates():
    # Only Jinja blocks are scanned; JS/CSS/HTML outside Jinja is ignored.
    banned_raw = [
        r"\.\s*date\(",
        r"\.strftime\(",
        r"\.isoformat\(",
        r"\|\s*localtime\b",
        r"\|\s*local_dt\b",
        r"\|\s*datetimeformat\b",
    ]
    banned = [re.compile(p) for p in banned_raw]

    for tpl in Path("app/templates").rglob("*.html"):
        text = tpl.read_text(encoding="utf-8")
        for start, end, block in _iter_jinja_blocks(text):
            for rx in banned:
                for m in rx.finditer(block):
                    abs_pos = start + m.start()
                    line_no = _line_of_pos(text, abs_pos)
                    snippet = _snippet_around(text, line_no, context=2)
                    raise AssertionError(
                        f"{tpl}:{line_no} contains banned pattern {rx.pattern} in Jinja block:\n{snippet}"
                    )


def test_compute_deadline_flags_boundaries():
    now = now_local()
    past = compute_deadline_flags(now - timedelta(days=1))
    today = compute_deadline_flags(now)
    future = compute_deadline_flags(now + timedelta(days=3))
    assert past["is_expired"] and not past["is_today"]
    assert today["is_today"] and not today["is_expired"]
    assert future["is_warning"] and future["days_left"] == 3


def test_sample_templates_render(app):
    # Minimal globals used by some templates
    app.jinja_env.globals["csrf_token"] = lambda: ""
    app.jinja_env.globals["current_user"] = SimpleNamespace(is_authenticated=False, role="")

    with app.test_request_context():
        case = SimpleNamespace(
            id=1,
            case_number="C1",
            deceased_name="D",
            status="open",
            registration_time_str="2024.01.01 10:00",
            deadline_str="2024.01.10 10:00",
            updated_at_iso="2024-01-02T00:00:00",
            uploaded_file_records=[
                SimpleNamespace(
                    filename="f.txt",
                    category="cat",
                    upload_time_str="2024.01.02 11:00",
                    uploader="u",
                )
            ],
            notes="",
        )
        changelog_entries = [
            SimpleNamespace(timestamp_str="2024.01.03 12:00", edited_by="u", new_value="v")
        ]

        render = app.jinja_env.get_template("assign_pathologist.html").render(
            case=case,
            szakerto_users=[],
            szakerto_choices=[],
            szakerto_choices_2=[],
            changelog_entries=changelog_entries,
            uploads=case.uploaded_file_records,
            caps={},
        )
        assert 'form_version" value="2024-01-02T00:00:00"' in render

        users = [SimpleNamespace(id=1, username="u", screen_name="", full_name="", role="", last_login_str="")]
        render2 = app.jinja_env.get_template("admin_users.html").render(users=users)
        assert "u" in render2
