
# Developer Guide

This project is a Flask application with automated tests. Follow the instructions below when working in this repository.

## Environment setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Export the required environment variables before running the app or tests:
   - `MAIL_USERNAME` – email account used for outgoing mail
   - `MAIL_PASSWORD` – password or app token for the above account
   - `SECRET_KEY` – Flask secret key
   These can be placed in a `.env` file or exported in your shell.

## Running tests

Execute the automated tests with:
```bash
pytest
```

## Scheduled tasks

The application provides two scripts for periodic jobs. Run either of the following in an activated environment:
```bash
python run_scheduler.py  # simple scheduler
python run_tasks.py      # alternative scheduler
```

## Coding conventions and pre‑commit steps

- Ensure all tests pass before pushing changes:
  ```bash
  pytest
  ```
  
