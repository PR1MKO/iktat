from flask import Flask
from .models import db
from flask_migrate import Migrate

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///forensic_cases.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate = Migrate(app, db)  # <-- ADD THIS LINE

    @app.route("/")
    def hello():
        return "Hello, world! Forensic Case Tracker is running."

    return app
