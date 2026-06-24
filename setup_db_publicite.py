#!/usr/bin/env python3
"""
Script Python pour créer les tables manquantes sauvegardes_publicites et signalements_publicites.
Exécution: python e/setup_db_publicite.py
"""

from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# URL de la base de données
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_YaC69HIAGyZn@ep-muddy-darkness-ai9gl7w1-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require")

def setup_tables():
    """Crée les tables manquantes pour les publicités"""
    
    engine = create_engine(DATABASE_URL)
    
    sql = """
    -- Table pour les sauvegardes de publicités
    CREATE TABLE IF NOT EXISTS sauvegardes_publicites (
        id SERIAL PRIMARY KEY,
        publicite_id INTEGER NOT NULL REFERENCES publicites(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
        date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(publicite_id, user_id)
    );

    -- Table pour les signalements de publicités
    CREATE TABLE IF NOT EXISTS signalements_publicites (
        id SERIAL PRIMARY KEY,
        publicite_id INTEGER NOT NULL REFERENCES publicites(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
        raison VARCHAR(50),
        description TEXT,
        date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(publicite_id, user_id)
    );

    -- Index pour améliorer les performances
    CREATE INDEX IF NOT EXISTS idx_sauvegardes_publicite ON sauvegardes_publicites(publicite_id);
    CREATE INDEX IF NOT EXISTS idx_sauvegardes_user ON sauvegardes_publicites(user_id);
    CREATE INDEX IF NOT EXISTS idx_signalements_publicite ON signalements_publicites(publicite_id);
    CREATE INDEX IF NOT EXISTS idx_signalements_user ON signalements_publicites(user_id);
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        print("✅ Tables créées avec succès !")
        print("   - sauvegardes_publicites")
        print("   - signalements_publicites")
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

if __name__ == "__main__":
    setup_tables()