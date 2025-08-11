from flask import Blueprint

investigations_bp = Blueprint(
    'investigations', __name__, template_folder='../templates/investigations'
)

from . import routes, models  # noqa: F401