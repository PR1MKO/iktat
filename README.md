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
4. Create a `.env` file or export these environment variables:
   - `MAIL_USERNAME` – your email account for outgoing mail
   - `MAIL_PASSWORD` – the password or app token
   - `MAIL_DEFAULT_SENDER` – default sender address
   - `SECRET_KEY` – Flask secret key
5. Run the development server:
   - `flask run`

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