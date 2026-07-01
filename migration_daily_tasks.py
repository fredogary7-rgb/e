from app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.begin() as conn:

        conn.execute(text("""
            ALTER TABLE daily_tasks
            ALTER COLUMN produit_id DROP NOT NULL;
        """))

        conn.execute(text("""
            ALTER TABLE daily_tasks
            ALTER COLUMN publicite_id DROP NOT NULL;
        """))

    print("OK")
