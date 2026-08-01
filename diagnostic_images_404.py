#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de diagnostic : Erreurs 404 sur les images produits

Ce script :
1. Extrait toutes les images référencées dans la table `produits`
2. Vérifie quels fichiers existent réellement dans static/uploads/products/
3. Identifie les correspondances et les fichiers manquants
4. Diagnostique la cause probable des erreurs 404
"""

import os
import sys
import json
from datetime import datetime
from collections import defaultdict

# Forcer le bon répertoire de travail
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Produit, UPLOAD_FOLDER

TARGET_DIR = UPLOAD_FOLDER  # static/uploads/products/

def banner(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def main():
    with app.app_context():
        banner("🔍 DIAGNOSTIC IMAGES PRODUITS — ERREURS 404")

        # ─── 1. CONFIGURATION ───────────────────────────────
        banner("📁 1. CONFIGURATION UPLOAD")
        print(f"   UPLOAD_FOLDER       : {UPLOAD_FOLDER}")
        print(f"   Chemin absolu       : {os.path.abspath(UPLOAD_FOLDER)}")
        print(f"   Dossier existe      : {'✅ OUI' if os.path.exists(UPLOAD_FOLDER) else '❌ NON'}")
        print(f"   app.root_path       : {app.root_path}")
        print(f"   app.static_folder   : {app.static_folder}")
        print(f"   static_url_path     : {app.static_url_path}")

        # ─── 2. FICHIERS SUR DISQUE ─────────────────────────
        banner("📂 2. FICHIERS PRÉSENTS DANS static/uploads/products/")
        existing_files = set()
        if os.path.exists(TARGET_DIR):
            existing_files = set(os.listdir(TARGET_DIR))
            print(f"   Nombre de fichiers  : {len(existing_files)}")
            for f in sorted(existing_files):
                fpath = os.path.join(TARGET_DIR, f)
                size_kb = os.path.getsize(fpath) / 1024
                print(f"     ✅ {f} ({size_kb:.1f} KB)")
        else:
            print(f"   ❌ LE DOSSIER N'EXISTE PAS : {TARGET_DIR}")

        # ─── 3. IMAGES EN BASE DE DONNÉES ──────────────────
        banner("🗄️  3. IMAGES RÉFÉRENCÉES DANS LA BASE DE DONNÉES")
        produits = Produit.query.filter(Produit.images.isnot(None)).filter(Produit.images != '').all()
        print(f"   Produits avec images : {len(produits)}")

        all_db_images = []
        for p in produits:
            images = p.liste_images
            for img in images:
                all_db_images.append({
                    'produit_id': p.id,
                    'produit_nom': p.nom,
                    'boutique_id': p.boutique_id,
                    'valeur_brute': img,
                    'image_principale': p.image_principale,
                })

        print(f"   Total images en base : {len(all_db_images)}")
        for item in all_db_images:
            img = item['valeur_brute']
            expected = item['image_principale']
            print(f"\n   Produit #{item['produit_id']} : {item['produit_nom'][:50]}")
            print(f"     Valeur brute en DB   : {img}")
            print(f"     image_principale()   : {expected}")

        # ─── 4. EXTRACTION DES NOMS DE FICHIERS ─────────────
        banner("🔬 4. ANALYSE DE CORRESPONDANCE")
        
        # Extraire les noms de fichiers depuis les chemins en base
        db_filenames = set()
        db_filename_to_info = {}
        for item in all_db_images:
            img = item['valeur_brute']
            # Extraire le nom de fichier (dernière partie après /)
            # Ex: uploads/products/xxx.jpeg → xxx.jpeg
            filename = img.replace('\\', '/').split('/')[-1]
            db_filenames.add(filename)
            if filename not in db_filename_to_info:
                db_filename_to_info[filename] = []
            db_filename_to_info[filename].append(item)

        print(f"   Noms de fichiers uniques en base : {len(db_filenames)}")
        
        # Comparaison
        matching = db_filenames & existing_files
        missing_in_disk = db_filenames - existing_files
        orphan_on_disk = existing_files - db_filenames

        print(f"\n   ✅ Correspondances (DB + disque) : {len(matching)}")
        for f in sorted(matching):
            print(f"     ✅ {f}")
            for info in db_filename_to_info[f]:
                print(f"        → Produit #{info['produit_id']} : {info['produit_nom'][:50]}")

        print(f"\n   ❌ En base MAIS absent du disque : {len(missing_in_disk)}")
        for f in sorted(missing_in_disk):
            print(f"     ❌ {f}")
            for info in db_filename_to_info[f]:
                print(f"        → Produit #{info['produit_id']} : {info['produit_nom'][:50]}")
                print(f"          URL servie : {info['image_principale']}")

        print(f"\n   👻 Sur le disque MAIS absent de la base : {len(orphan_on_disk)}")
        for f in sorted(orphan_on_disk):
            print(f"     👻 {f}")

        # ─── 5. VÉRIFICATION STATIC FLASK ───────────────────
        banner("🌐 5. VÉRIFICATION DU ROUTAGE STATIC FLASK")
        from flask import url_for
        try:
            static_url = url_for('static', filename='uploads/products/test.txt')
            print(f"   url_for('static', filename='uploads/products/test.txt') = {static_url}")
        except Exception as e:
            print(f"   ❌ Erreur url_for: {e}")

        # Vérifier si un fichier existant est bien servi
        if existing_files:
            test_file = sorted(existing_files)[0]
            test_path = os.path.join('uploads', 'products', test_file)
            try:
                test_url = url_for('static', filename=test_path)
                print(f"   Test fichier existant '{test_file}' → URL: {test_url}")
            except Exception as e:
                print(f"   ❌ Erreur: {e}")

        # Vérifier si un fichier manquant renvoie bien 404
        if missing_in_disk:
            test_missing = sorted(missing_in_disk)[0]
            test_path_missing = os.path.join('uploads', 'products', test_missing)
            try:
                test_url_missing = url_for('static', filename=test_path_missing)
                print(f"   Test fichier MANQUANT '{test_missing}' → URL générée: {test_url_missing}")
                print(f"   ⚠️  Flask génère l'URL mais le fichier n'existe pas → 404 au chargement")
            except Exception as e:
                print(f"   ❌ Erreur: {e}")

        # ─── 6. DIAGNOSTIC GIT ──────────────────────────────
        banner("📦 6. STATUT GIT DE static/uploads/products/")
        import subprocess
        try:
            result = subprocess.run(
                ['git', 'ls-files', '--others', '--ignored', '--exclude-standard', 'static/uploads/products/'],
                capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__))
            )
            ignored = result.stdout.strip().split('\n') if result.stdout.strip() else []
            print(f"   Fichiers ignorés par git : {len(ignored)}")
            if ignored:
                for f in ignored[:10]:
                    print(f"     🚫 {f}")
            else:
                print("     Aucun — les fichiers sont peut-être trackés ?")
            
            result2 = subprocess.run(
                ['git', 'ls-files', 'static/uploads/products/'],
                capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__))
            )
            tracked = result2.stdout.strip().split('\n') if result2.stdout.strip() else []
            print(f"   Fichiers trackés par git  : {len(tracked)}")
            if tracked:
                for f in tracked[:10]:
                    print(f"     ✅ {f}")
            else:
                print("     ❌ AUCUN — les fichiers d'upload ne sont PAS dans git !")
        except Exception as e:
            print(f"   ⚠️  Impossible d'exécuter git : {e}")

        # ─── 7. DIAGNOSTIC FINAL ────────────────────────────
        banner("📋 7. DIAGNOSTIC FINAL — CAUSE DES ERREURS 404")
        
        causes = []
        
        if missing_in_disk:
            causes.append(
                f"🔴 {len(missing_in_disk)} fichier(s) référencé(s) en base "
                f"MAIS absent(s) du disque → ERREUR 404 garantie."
            )
        
        if not os.path.exists(TARGET_DIR):
            causes.append("🔴 Le dossier static/uploads/products/ n'existe pas du tout.")
        
        # Vérifier si le dossier est dans .gitignore
        gitignore_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.gitignore')
        uploads_ignored = False
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as f:
                for line in f:
                    if 'uploads' in line or 'static/uploads' in line:
                        uploads_ignored = True
                        causes.append(f"🔴 .gitignore contient '{line.strip()}' → les images ne sont jamais déployées.")
                        break
        
        if not uploads_ignored and not os.path.exists(gitignore_path):
            causes.append("🟡 Aucun .gitignore trouvé — mais vérifiez si static/uploads/ est ignoré par git.")
        
        causes.append(
            "\n🟡 EXPLICATION LA PLUS PROBABLE :\n"
            "   Railway (et la plupart des PaaS) utilise un SYSTÈME DE FICHIERS ÉPHÉMÈRE.\n"
            "   → Les fichiers écrits pendant l'exécution (uploads) sont PERDUS à chaque redéploiement.\n"
            "   → Seuls les fichiers versionnés dans Git survivent au déploiement.\n"
            "   → Comme les images uploadées ne sont PAS dans Git, elles disparaissent.\n"
            "\n"
            "   SOLUTION : Utiliser un stockage persistant externe :\n"
            "   - Cloudinary (déjà dans requirements.txt !)\n"
            "   - AWS S3\n"
            "   - Railway Volumes (stockage persistant payant)\n"
            "   - Uploadcare, etc."
        )
        
        # Vérifier si Cloudinary est configuré
        cloudinary_configured = all([
            os.environ.get('CLOUDINARY_CLOUD_NAME'),
            os.environ.get('CLOUDINARY_API_KEY'),
            os.environ.get('CLOUDINARY_API_SECRET'),
        ])
        if cloudinary_configured:
            causes.append("\n✅ Cloudinary est configuré dans .env — les NOUVEAUX uploads devraient être OK.")
            causes.append("   Mais les anciens produits pointent encore vers des fichiers locaux (uploads/products/...).")
        else:
            causes.append("\n🟡 Cloudinary n'est PAS configuré — tous les uploads vont dans le stockage local éphémère.")
        
        for c in causes:
            print(f"\n{c}")

        # ─── 8. RÉSUMÉ STATISTIQUE ──────────────────────────
        banner("📊 8. RÉSUMÉ")
        print(f"   Total images en base    : {len(db_filenames)}")
        print(f"   Présentes sur le disque : {len(matching)}  ({len(matching)/max(len(db_filenames),1)*100:.0f}%)")
        print(f"   MANQUANTES (→ 404)      : {len(missing_in_disk)}  ({len(missing_in_disk)/max(len(db_filenames),1)*100:.0f}%)")
        print(f"   Orphelines sur disque   : {len(orphan_on_disk)}")
        print(f"   Total produits          : {Produit.query.count()}")
        print(f"   Produits avec images    : {len(produits)}")
        print()

if __name__ == '__main__':
    main()