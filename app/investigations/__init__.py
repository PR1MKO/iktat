from flask import Blueprint

investigations_bp = Blueprint(
    "investigations", __name__, template_folder="../templates/investigations"
)

# Keep imports after blueprint to avoid circular import issues.
from . import models, routes  # noqa: F401, E402
