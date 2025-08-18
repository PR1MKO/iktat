@echo off
set FLASK_APP=app:create_app
flask db upgrade -d migrations_examination