"""
Script de migration pour ajouter le champ slug aux produits existants.
À exécuter une seule fois pour initialiser les slugs.
"""

import sys
import os

# Ajouter le répertoire courant au chemin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Produit
import unicodedata
import re
import uuid

def generate_slug(text):
    """Génère un slug URL-safe à partir d'un texte"""
    if not text:
        return str(uuid.uuid4())[:8]
    slug = unicodedata.normalize('NFKD', text.lower())
    slug = slug.encode('ascii', 'ignore').decode('ascii')
    slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
    slug = slug[:80]
    return slug or str(uuid.uuid4())[:8]

def migrate_slugs():
    """Ajoute un slug unique à chaque produit qui n'en a pas"""
    with app.app_context():
        produits = Produit.query.filter_by(slug=None).all()
        updated = 0
        
        for produit in produits:
            base_slug = generate_slug(produit.nom)
            slug = base_slug
            counter = 1
            
            # Vérifier l'unicité
            while Produit.query.filter_by(slug=slug).first() is not None:
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            produit.slug = slug
            updated += 1
            print(f"  {produit.nom} -> {slug}")
        
        if updated > 0:
            db.session.commit()
            print(f"\n✅ Migration terminée : {updated} produits mis à jour")
        else:
            print("\nℹ️ Aucun produit à migrer")

if __name__ == "__main__":
    print("🚀 Migration des slugs pour les produits...")
    migrate_slugs()