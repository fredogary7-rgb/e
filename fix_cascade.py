#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script pour ajouter la contrainte CASCADE sur la table likes_publicites.
Cela permet de supprimer automatiquement les likes lorsqu'une publicité est supprimée.

Utilisation:
    cd e
    python fix_cascade.py
"""

from app import app, db
from sqlalchemy import text

def fix_cascade():
    """Ajoute la contrainte CASCADE sur la table likes_publicites"""
    with app.app_context():
        try:
            # Supprimer l'ancienne contrainte
            print("🔄 Suppression de l'ancienne contrainte...")
            db.session.execute(text("""
                ALTER TABLE likes_publicites 
                DROP CONSTRAINT IF EXISTS likes_publicites_publicite_id_fkey;
            """))
            db.session.commit()
            print("✅ Ancienne contrainte supprimée.")
            
            # Ajouter la nouvelle contrainte avec CASCADE
            print("🔄 Ajout de la nouvelle contrainte CASCADE...")
            db.session.execute(text("""
                ALTER TABLE likes_publicites 
                ADD CONSTRAINT likes_publicites_publicite_id_fkey 
                FOREIGN KEY (publicite_id) REFERENCES publicites(id) ON DELETE CASCADE;
            """))
            db.session.commit()
            print("✅ Nouvelle contrainte CASCADE ajoutée avec succès !")
            
            print("\n" + "=" * 50)
            print("🎉 OPÉRATION TERMINÉE AVEC SUCCÈS !")
            print("=" * 50)
            print("\nMaintenant, lorsque vous supprimez une publicité :")
            print("  ✅ Les likes associés sont automatiquement supprimés")
            print("  ✅ Les commentaires associés sont automatiquement supprimés")
            print("  ✅ La publicité est supprimée sans erreur")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ ERREUR : {e}")
            print("\nVeuillez vérifier que la base de données est accessible.")
            return False
    
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("🔧 FIX CASCADE - likes_publicites")
    print("=" * 50)
    print()
    
    success = fix_cascade()
    
    if success:
        print("\n✅ Tout s'est bien passé !")
        exit(0)
    else:
        print("\n❌ Une erreur s'est produite.")
        exit(1)