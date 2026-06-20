"""
Script pour créer les tables du panier directement dans PostgreSQL
Exécuter avec: python setup_panier_db.py
"""

import psycopg2
import os

# URL de la base de données (depuis app.py)
DATABASE_URL = "postgresql://neondb_owner:npg_YaC69HIAGyZn@ep-muddy-darkness-ai9gl7w1-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require"

def create_panier_tables():
    """Crée les tables paniers et articles_panier"""
    try:
        # Se connecter à la base de données
        print("🔗 Connexion à la base de données...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # SQL pour créer la table paniers
        create_paniers_sql = """
        CREATE TABLE IF NOT EXISTS paniers (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            session_id VARCHAR(100),
            date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # SQL pour créer la table articles_panier
        create_articles_sql = """
        CREATE TABLE IF NOT EXISTS articles_panier (
            id SERIAL PRIMARY KEY,
            panier_id INTEGER NOT NULL REFERENCES paniers(id) ON DELETE CASCADE,
            produit_id INTEGER NOT NULL REFERENCES produits(id),
            quantite INTEGER NOT NULL DEFAULT 1,
            date_ajout TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # SQL pour créer les index
        create_indexes_sql = """
        CREATE INDEX IF NOT EXISTS idx_paniers_user_id ON paniers(user_id);
        CREATE INDEX IF NOT EXISTS idx_paniers_session_id ON paniers(session_id);
        CREATE INDEX IF NOT EXISTS idx_articles_panier_panier_id ON articles_panier(panier_id);
        CREATE INDEX IF NOT EXISTS idx_articles_panier_produit_id ON articles_panier(produit_id);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_panier_produit ON articles_panier(panier_id, produit_id);
        """
        
        # Exécuter les requêtes
        print("📦 Création de la table paniers...")
        cursor.execute(create_paniers_sql)
        
        print("📦 Création de la table articles_panier...")
        cursor.execute(create_articles_sql)
        
        print("📊 Création des index...")
        cursor.execute(create_indexes_sql)
        
        # Valider les changements
        conn.commit()
        
        print("✅ Tables créées avec succès !")
        print("   - Table 'paniers' créée")
        print("   - Table 'articles_panier' créée")
        print("   - Index créés")
        
        # Vérifier que les tables existent
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name IN ('paniers', 'articles_panier');
        """)
        tables = cursor.fetchall()
        print(f"\n📋 Tables existantes: {[t[0] for t in tables]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Erreur : {e}")
        raise

if __name__ == "__main__":
    create_panier_tables()