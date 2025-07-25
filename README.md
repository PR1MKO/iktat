# Forensic Case Tracker

A Flask-based web application for tracking forensic/autopsy cases with role-based access, document upload, and audit logging.
This project is a modern replacement for legacy Excel workflows, with future AI-ready features.

## Quick Start

1. Clone the repo (or copy the project folder).
2. Create and activate a virtualenv:
   - `python -m venv venv`
   - `venv\Scripts\activate`
3. Install requirements:
   - `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and update the values or export these variables:
   - `MAIL_USERNAME` – your email account for outgoing mail
   - `MAIL_PASSWORD` – the password or app token
   - `MAIL_DEFAULT_SENDER` – default sender address (falls back to `MAIL_USERNAME` if omitted)
   - `SECRET_KEY` – Flask secret key
   - `SMTP_USER` – account for `test_smtp.py`
   - `SMTP_PASSWORD` – password or token for `test_smtp.py`
5. Run the development server:
   - **Set the module for `flask run`:** `export FLASK_APP=run.py`  \
     Windows: `set FLASK_APP=run.py`
   - `flask run`
   - or simply `python run.py` (no `FLASK_APP` needed)
   
### Testing SMTP settings

Run `test_smtp.py` to verify your mail credentials. Set the following
environment variables before executing the script:

```bash
export SMTP_USER=your@gmail.com
export SMTP_PASSWORD=your-app-password
python test_smtp.py
```

## Development Setup

To run the unit tests, first ensure all required packages are installed in your
activated virtual environment. Install dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
```

Once the packages are installed you can execute the test suite with:

```bash
pytest
```

## Folder Structure

- `app/` - main application package (code, logic)
- `app/templates/` - HTML templates
- `app/static/` - CSS, JS, images
- `requirements.txt` - dependencies
- `run.py` - run the app
- `.gitignore` - files excluded from version control

## Features

- Secure login system with roles (admin, iroda, szig, szak)
- Case creation, assignment, and status tracking
- Change/audit log for all edits
- Automatic email notifications on milestones
- Document upload per case (planned)
- Ready for future AI modules (OCR, summarization, auto-assignment)
- Detailed permissions by role

---

*More documentation to be added as the project develops.*
