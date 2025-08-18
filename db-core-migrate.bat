@echo off
set FLASK_APP=app:create_app
flask db migrate -d migrations -m "%*"