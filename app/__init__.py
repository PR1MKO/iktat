from flask import Flask

def create_app():
    app = Flask(__name__)

    @app.route("/")
    def hello():
        return "Hello, world! Forensic Case Tracker is running."

    return app
