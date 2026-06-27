from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://neondb_owner:npg_YaC69HIAGyZn@ep-muddy-darkness-ai9gl7w1-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS webauthn_credentials (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            credential_id VARCHAR(500) UNIQUE NOT NULL,
            credential_public_key BYTEA NOT NULL,
            sign_count INTEGER DEFAULT 0,
            device_type VARCHAR(50),
            aaguid VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP,
            name VARCHAR(100),
            is_active BOOLEAN DEFAULT TRUE
        );
    """))

    conn.commit()

print("Table webauthn_credentials créée avec succès")
