from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://neondb_owner:npg_YaC69HIAGyZn@ep-muddy-darkness-ai9gl7w1-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    conn.execute(text("""
        ALTER TABLE retrait
        ADD COLUMN IF NOT EXISTS reference_soleaspay VARCHAR(100);
    """))

    conn.execute(text("""
        ALTER TABLE retrait
        ADD COLUMN IF NOT EXISTS transaction_reference VARCHAR(100);
    """))

    conn.execute(text("""
        ALTER TABLE retrait
        ADD COLUMN IF NOT EXISTS external_reference VARCHAR(100);
    """))

    conn.execute(text("""
        ALTER TABLE retrait
        ADD COLUMN IF NOT EXISTS soleaspay_status VARCHAR(50);
    """))

    conn.execute(text("""
        ALTER TABLE retrait
        ADD COLUMN IF NOT EXISTS soleaspay_created_at TIMESTAMP;
    """))

    conn.execute(text("""
        ALTER TABLE retrait
        ADD COLUMN IF NOT EXISTS last_sync TIMESTAMP;
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_retrait_external_reference
        ON retrait(external_reference);
    """))

    conn.commit()

print("✅ Migration Soleaspay terminée avec succès !")
