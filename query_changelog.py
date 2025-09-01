from sqlalchemy import text

from app import create_app, db

app = create_app()

with app.app_context():
    query = text(
        """
    SELECT id, case_id, field_name, new_value, edited_by, timestamp
    FROM change_log
    WHERE new_value LIKE '%[____-__-__ __:__ – %'
    ORDER BY timestamp DESC;
    """
    )
    results = db.session.execute(query).fetchall()

    for row in results:
        print(row)
