"""
==========================================
🧪 CRÉATION DES 5 000 UTILISATEURS DE TEST
==========================================

Usage :
    python create_test_users.py

Ce script génère :
    1. test_users.csv : Fichier CSV pour k6 (username,password,phone)
    2. test_users.sql  : Script SQL pour insérer dans la DB
    3. Insère directement dans la DB (optionnel)

⚠️  NE PAS exécuter sur la base de production !
⚠️  Utiliser une base de test séparée.
"""

import csv
import os
import hashlib
import argparse
from datetime import datetime

# Configuration
TEST_USER_COUNT = 5000
OUTPUT_CSV = "test_users.csv"
OUTPUT_SQL = "test_users.sql"
BATCH_SIZE = 1000  # Insérer par lots de 1000

# ==========================================
# Génération des utilisateurs
# ==========================================

def generate_test_users(count=TEST_USER_COUNT):
    """Génère les utilisateurs de test avec données réalistes."""
    users = []
    
    countries = ["Benin", "Togo", "Cote d'Ivoire", "Senegal", "Burkina Faso", "Mali", "Niger"]
    operators = ["Moov Money", "MTN Money", "Orange Money", "Wave"]
    
    for i in range(1, count + 1):
        username = f"testuser{i}"
        phone = f"+22901{str(i).zfill(6)}"
        email = f"testuser{i}@nectarpro-test.com"
        password = f"TestPass{i}!"
        
        # Hash du mot de passe (même méthode que Flask/werkzeug)
        from werkzeug.security import generate_password_hash
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        
        # Répartition réaliste
        country = countries[i % len(countries)]
        operator = operators[i % len(operators)]
        
        # Certains utilisateurs ont des parrains (niveau 1-3)
        parrain = None
        if i > 500 and i % 10 == 0:
            parrain_username = f"testuser{i - 500}"
            if parrain_username.startswith("testuser"):
                parrain = parrain_username
        
        # Soldes aléatoires réalistes
        import random
        has_deposit = random.random() < 0.6  # 60% ont déjà déposé
        solde_depot = random.uniform(5000, 100000) if has_deposit else 0
        solde_parrainage = random.uniform(0, 50000) if has_deposit else 0
        solde_revenu = random.uniform(0, 30000) if has_deposit else 0
        solde_total = solde_depot + solde_parrainage + solde_revenu
        
        users.append({
            "username": username,
            "phone": phone,
            "email": email,
            "password": password,
            "password_hash": password_hash,
            "country": country,
            "wallet_country": country,
            "wallet_operator": operator,
            "wallet_number": phone,
            "parrain": parrain,
            "solde_total": solde_total,
            "solde_depot": solde_depot,
            "solde_parrainage": solde_parrainage,
            "solde_revenu": solde_revenu,
            "is_verified": has_deposit,
            "premier_depot": has_deposit,
            "is_admin": (i == 1),  # testuser1 est admin
            "date_creation": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        })
    
    return users


# ==========================================
# Génération du CSV (pour k6)
# ==========================================

def generate_csv(users):
    """Génère un fichier CSV avec username,password,phone pour k6."""
    print(f"📝 Génération de {OUTPUT_CSV}...")
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["username", "password", "phone"])
        for user in users:
            writer.writerow([user["username"], user["password"], user["phone"]])
    print(f"✅ {OUTPUT_CSV} créé ({len(users)} utilisateurs)")


# ==========================================
# Génération du SQL (pour insertion DB)
# ==========================================

def generate_sql(users):
    """Génère un script SQL pour insérer les utilisateurs dans la DB de test."""
    print(f"📝 Génération de {OUTPUT_SQL}...")
    
    with open(OUTPUT_SQL, "w", encoding="utf-8") as f:
        f.write("""-- ==========================================
-- 🧪 UTILISATEURS DE TEST - Nectar Pro
-- Généré le {date}
-- {count} utilisateurs
-- ==========================================
-- NE PAS exécuter sur la base de production !
-- ==========================================

BEGIN;

""".format(date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), count=len(users)))
        
        # Insérer par lots de BATCH_SIZE
        for batch_start in range(0, len(users), BATCH_SIZE):
            batch = users[batch_start:batch_start + BATCH_SIZE]
            
            f.write(f"-- Lot {batch_start // BATCH_SIZE + 1} ({batch_start+1}-{min(batch_start+BATCH_SIZE, len(users))})\n")
            f.write("INSERT INTO \"user\" (username, phone, email, password, country, wallet_country, wallet_operator, wallet_number, solde_total, solde_depot, solde_parrainage, solde_revenu, is_verified, premier_depot, is_admin, date_creation) VALUES\n")
            
            values = []
            for user in batch:
                vals = "('{username}', '{phone}', '{email}', '{password_hash}', '{country}', '{wallet_country}', '{wallet_operator}', '{wallet_number}', {solde_total}, {solde_depot}, {solde_parrainage}, {solde_revenu}, {is_verified}, {premier_depot}, {is_admin}, '{date_creation}')".format(
                    username=user["username"],
                    phone=user["phone"],
                    email=user["email"],
                    password_hash=user["password_hash"],
                    country=user["country"],
                    wallet_country=user["wallet_country"],
                    wallet_operator=user["wallet_operator"],
                    wallet_number=user["wallet_number"],
                    solde_total=user["solde_total"],
                    solde_depot=user["solde_depot"],
                    solde_parrainage=user["solde_parrainage"],
                    solde_revenu=user["solde_revenu"],
                    is_verified=str(user["is_verified"]).upper(),
                    premier_depot=str(user["premier_depot"]).upper(),
                    is_admin=str(user["is_admin"]).upper(),
                    date_creation=user["date_creation"],
                )
                values.append(vals)
            
            f.write(",\n".join(values))
            f.write("\nON CONFLICT (username) DO NOTHING;\n\n")
        
        # Mise à jour des parrains (après insertion pour éviter les dépendances)
        f.write("-- Mise à jour des parrains\n")
        for user in users:
            if user["parrain"]:
                f.write("UPDATE \"user\" SET parrain = '{parrain}' WHERE username = '{username}';\n".format(
                    parrain=user["parrain"],
                    username=user["username"],
                ))
        
        f.write("\nCOMMIT;\n")
        
        # Statistiques
        f.write("""
-- ==========================================
-- Vérification
-- ==========================================
SELECT 
    COUNT(*) as total_users,
    SUM(CASE WHEN is_verified = TRUE THEN 1 ELSE 0 END) as verified_users,
    SUM(CASE WHEN is_admin = TRUE THEN 1 ELSE 0 END) as admin_users,
    SUM(CASE WHEN parrain IS NOT NULL THEN 1 ELSE 0 END) as users_with_parrain,
    ROUND(AVG(solde_total)::numeric, 2) as avg_solde_total,
    ROUND(SUM(solde_total)::numeric, 2) as total_soldes
FROM "user";
""")
    
    print(f"✅ {OUTPUT_SQL} créé ({len(users)} utilisateurs, {len(users)//BATCH_SIZE + 1} lots)")


# ==========================================
# Insertion directe via SQLAlchemy (optionnel)
# ==========================================

def insert_into_db(users, db_url=None):
    """Insère les utilisateurs directement dans la base via SQLAlchemy (mode batch)."""
    if not db_url:
        print("⚠️  URL de base de données non fournie. Utilisez generate_sql() à la place.")
        return False
    
    try:
        from sqlalchemy import create_engine, text
        from werkzeug.security import generate_password_hash
        
        engine = create_engine(db_url, echo=False)
        
        print(f"🔌 Connexion à la base de données...")
        
        with engine.begin() as conn:
            for i, user in enumerate(users, 1):
                conn.execute(
                    text("""
                        INSERT INTO "user" (username, phone, email, password, country, 
                                           wallet_country, wallet_operator, wallet_number,
                                           solde_total, solde_depot, solde_parrainage, solde_revenu,
                                           is_verified, premier_depot, is_admin, date_creation)
                        VALUES (:username, :phone, :email, :password, :country,
                                :wallet_country, :wallet_operator, :wallet_number,
                                :solde_total, :solde_depot, :solde_parrainage, :solde_revenu,
                                :is_verified, :premier_depot, :is_admin, :date_creation)
                        ON CONFLICT (username) DO NOTHING
                    """),
                    {
                        "username": user["username"],
                        "phone": user["phone"],
                        "email": user["email"],
                        "password": user["password_hash"],
                        "country": user["country"],
                        "wallet_country": user["wallet_country"],
                        "wallet_operator": user["wallet_operator"],
                        "wallet_number": user["wallet_number"],
                        "solde_total": user["solde_total"],
                        "solde_depot": user["solde_depot"],
                        "solde_parrainage": user["solde_parrainage"],
                        "solde_revenu": user["solde_revenu"],
                        "is_verified": user["is_verified"],
                        "premier_depot": user["premier_depot"],
                        "is_admin": user["is_admin"],
                        "date_creation": user["date_creation"],
                    }
                )
                
                if i % 1000 == 0:
                    print(f"   {i}/{len(users)} utilisateurs insérés...")
        
        # Mise à jour des parrains
        print("🔗 Mise à jour des parrains...")
        with engine.begin() as conn:
            for user in users:
                if user["parrain"]:
                    conn.execute(
                        text("UPDATE \"user\" SET parrain = :parrain WHERE username = :username"),
                        {"parrain": user["parrain"], "username": user["username"]}
                    )
        
        print(f"✅ {len(users)} utilisateurs insérés dans la base")
        return True
        
    except ImportError:
        print("⚠️  SQLAlchemy non installé. Installez-le avec : pip install sqlalchemy")
        return False
    except Exception as e:
        print(f"❌ Erreur lors de l'insertion : {e}")
        return False


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Générer des utilisateurs de test pour Nectar Pro")
    parser.add_argument("--count", type=int, default=TEST_USER_COUNT, help="Nombre d'utilisateurs à générer")
    parser.add_argument("--csv-only", action="store_true", help="Générer uniquement le CSV (pas de SQL)")
    parser.add_argument("--sql-only", action="store_true", help="Générer uniquement le SQL (pas de CSV)")
    parser.add_argument("--db-url", type=str, help="URL de base de données pour insertion directe (ex: postgresql://...)")
    
    args = parser.parse_args()
    
    print(f"""
╔══════════════════════════════════════════════╗
║     🧪 GÉNÉRATION UTILISATEURS DE TEST      ║
║     Nectar Pro - {args.count} utilisateurs              ║
╚══════════════════════════════════════════════╝
""")
    
    # ==========================================
    # ÉTAPE 1 : Génération des données
    # ==========================================
    print(f"👥 Génération de {args.count} utilisateurs de test...")
    users = generate_test_users(args.count)
    print(f"✅ {len(users)} utilisateurs générés")
    
    # ==========================================
    # ÉTAPE 2 : Génération CSV
    # ==========================================
    if not args.sql_only:
        generate_csv(users)
    
    # ==========================================
    # ÉTAPE 3 : Génération SQL
    # ==========================================
    if not args.csv_only:
        generate_sql(users)
    
    # ==========================================
    # ÉTAPE 4 : Insertion DB (optionnel)
    # ==========================================
    if args.db_url:
        print(f"🗄️  Insertion dans la base de données...")
        success = insert_into_db(users, args.db_url)
        if success:
            print("✅ Insertion DB terminée")
        else:
            print("⚠️  Utilisez le fichier SQL généré pour l'insertion manuelle")
    
    print(f"""
╔══════════════════════════════════════════════╗
║     ✅ GÉNÉRATION TERMINÉE                  ║
║                                              ║
║     📄 CSV : {OUTPUT_CSV}
║     🗄️  SQL : {OUTPUT_SQL}
║     👥 Utilisateurs : {args.count}
║                                              ║
║     Pour les tests de charge :               ║
║     k6 run loadtest.js                      ║
║                                              ║
║     Pour insérer dans la DB :                ║
║     psql \$DB_URL -f {OUTPUT_SQL}
╚══════════════════════════════════════════════╝
""")