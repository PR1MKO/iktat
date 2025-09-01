from flask import render_template_string


def test_cases_macro_handles_missing_context(app):
    tmpl = (
        "{% import 'includes/case_macros.html' as cm %}{{ cm.cases_table([], None) }}"
    )
    with app.test_request_context("/"):
        html = render_template_string(tmpl)
        assert "Nincs megjeleníthető ügy." in html
