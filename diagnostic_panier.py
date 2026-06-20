"""
Script de diagnostic et réparation du système de panier
Exécuter avec: python diagnostic_panier.py
"""

import psycopg2
from psycopg2 import sql
import os

# URL de la base de données
DATABASE_URL = "postgresql://neondb_owner:npg_YaC69HIAGyZn@ep-muddy-darkness-ai9gl7w1-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require"

def diagnostic():
    """Diagnostic complet du système de panier"""
    print("=" * 60)
    print("🔍 DIAGNOSTIC DU SYSTÈME DE PANIER")
    print("=" * 60)
    
    try:
        # Connexion à la base de données
        print("\n🔗 Connexion à la base de données...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        print("✅ Connecté avec succès")
        
        # 1. Vérifier les tables existantes
        print("\n📋 TABLES EXISTANTES:")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            print(f"   - {table}")
        
        # 2. Vérifier si les tables du panier existent
        print("\n🛒 TABLES DU PANIER:")
        panier_exists = 'paniers' in tables
        articles_exists = 'articles_panier' in tables
        
        print(f"   paniers: {'✅ EXISTE' if panier_exists else '❌ MANQUANTE'}")
        print(f"   articles_panier: {'✅ EXISTE' if articles_exists else '❌ MANQUANTE'}")
        
        if panier_exists:
            # Vérifier la structure de la table paniers
            print("\n📊 STRUCTURE DE LA TABLE 'paniers':")
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'paniers'
                ORDER BY ordinal_position;
            """)
            for col in cursor.fetchall():
                nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col[3]}" if col[3] else ""
                print(f"   {col[0]}: {col[1]} {nullable}{default}")
        
        if articles_exists:
            # Vérifier la structure de la table articles_panier
            print("\n📊 STRUCTURE DE LA TABLE 'articles_panier':")
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'articles_panier'
                ORDER BY ordinal_position;
            """)
            for col in cursor.fetchall():
                nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col[3]}" if col[3] else ""
                print(f"   {col[0]}: {col[1]} {nullable}{default}")
        
        # 3. Vérifier la table produits (nécessaire pour la clé étrangère)
        print("\n📦 TABLE PRODUITS:")
        produits_exists = 'produits' in tables
        print(f"   produits: {'✅ EXISTE' if produits_exists else '❌ MANQUANTE'}")
        
        # 4. Vérifier la table users (nécessaire pour la clé étrangère)
        print("\n👤 TABLE USERS:")
        users_exists = 'user' in tables
        print(f"   user: {'✅ EXISTE' if users_exists else '❌ MANQUANTE'}")
        
        # 5. Si les tables manquent, proposer de les créer
        if not panier_exists or not articles_exists:
            print("\n" + "=" * 60)
            print("⚠️  TABLES MANQUANTES DÉTECTÉES")
            print("=" * 60)
            
            reponse = input("\nVoulez-vous créer les tables manquantes ? (o/n): ")
            if reponse.lower() in ['o', 'oui']:
                create_tables(cursor, conn, panier_exists, articles_exists)
            else:
                print("\n❌ Aucune action effectuée.")
        else:
            print("\n✅ TOUTES LES TABLES SONT PRÉSENTES")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        raise


def create_tables(cursor, conn, panier_exists, articles_exists):
    """Crée les tables manquantes"""
    
    if not panier_exists:
        print("\n📦 Création de la table 'paniers'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS paniers (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                session_id VARCHAR(100),
                date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("   ✅ Table 'paniers' créée")
    
    if not articles_exists:
        print("\n📦 Création de la table 'articles_panier'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles_panier (
                id SERIAL PRIMARY KEY,
                panier_id INTEGER NOT NULL REFERENCES paniers(id) ON DELETE CASCADE,
                produit_id INTEGER NOT NULL REFERENCES produits(id),
                quantite INTEGER NOT NULL DEFAULT 1,
                date_ajout TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(panier_id, produit_id)
            );
        """)
        print("   ✅ Table 'articles_panier' créée")
    
    # Créer les index
    print("\n📊 Création des index...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_paniers_user_id ON paniers(user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_paniers_session_id ON paniers(session_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_panier_panier_id ON articles_panier(panier_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_panier_produit_id ON articles_panier(produit_id);")
    print("   ✅ Index créés")
    
    # Valider les changements
    conn.commit()
    print("\n✅ TABLES CRÉÉES AVEC SUCCÈS")


if __name__ == "__main__":
    diagnostic()