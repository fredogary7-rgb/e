"""
Script de migration pour ajouter les tables du panier (Panier et ArticlePanier)
Exécuter avec: python migrate_panier.py
"""

import os
from app import app, db

def migrate():
    """Crée les tables Panier et ArticlePanier"""
    with app.app_context():
        try:
            # Créer toutes les tables (y compris les nouvelles)
            db.create_all()
            print("✅ Migration réussie !")
            print("   - Table 'paniers' créée")
            print("   - Table 'articles_panier' créée")
        except Exception as e:
            print(f"❌ Erreur lors de la migration : {e}")

if __name__ == "__main__":
    migrate()