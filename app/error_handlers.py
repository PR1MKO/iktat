# app/error_handlers.py
from flask import render_template
from jinja2 import TemplateNotFound

from app import db


def register_error_handlers(app):
    @app.errorhandler(403)
    def forbidden(e):
        try:
            return render_template("403.html"), 403
        except Exception:
            return "403 Forbidden", 403

    @app.errorhandler(404)
    def not_found_error(e):
        try:
            return render_template("404.html"), 404
        except TemplateNotFound:
            return "404 Not Found", 404

    @app.errorhandler(413)  # RequestEntityTooLarge
    def too_large_error(e):
        try:
            return render_template("413.html"), 413
        except TemplateNotFound:
            return "413 Request Entity Too Large", 413

    @app.errorhandler(500)
    def internal_error(e):
        # Make sure failed transactions don't poison the next request
        try:
            db.session.rollback()
        except Exception:
            pass
        try:
            return render_template("500.html"), 500
        except TemplateNotFound:
            return "500 Internal Server Error", 500
