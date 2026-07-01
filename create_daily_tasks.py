from app import app, db
from sqlalchemy import text

with app.app_context():

    commands = [

        text("""
        CREATE TABLE IF NOT EXISTS daily_tasks (
            id SERIAL PRIMARY KEY,
            produit_id INTEGER NOT NULL,
            date DATE NOT NULL,
            ordre INTEGER DEFAULT 0,
            actif BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (produit_id) REFERENCES produits(id) ON DELETE CASCADE,
            UNIQUE (produit_id, date)
        );
        """),

        text("""
        CREATE TABLE IF NOT EXISTS user_tasks (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            task_id INTEGER NOT NULL,
            shared BOOLEAN DEFAULT FALSE,
            shared_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE,
            FOREIGN KEY (task_id) REFERENCES daily_tasks(id) ON DELETE CASCADE,
            UNIQUE (user_id, task_id)
        );
        """),

        text("""
        CREATE TABLE IF NOT EXISTS task_rewards (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            date DATE NOT NULL,
            montant DOUBLE PRECISION NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE,
            UNIQUE (user_id, date)
        );
        """),

        text("CREATE INDEX IF NOT EXISTS idx_daily_tasks_date ON daily_tasks(date);"),
        text("CREATE INDEX IF NOT EXISTS idx_user_tasks_user ON user_tasks(user_id);"),
        text("CREATE INDEX IF NOT EXISTS idx_task_rewards_user ON task_rewards(user_id);"),
        text("CREATE INDEX IF NOT EXISTS idx_task_rewards_date ON task_rewards(date);"),
    ]

    with db.engine.begin() as conn:
        for cmd in commands:
            conn.execute(cmd)

    print("✅ Tables créées avec succès.")
