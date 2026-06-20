# 🛒 Configuration du Système de Panier

## ⚠️ ÉTAPE OBLIGATOIRE : Créer les tables dans la base de données

Les erreurs `relation "paniers" does not exist` indiquent que les tables n'ont pas été créées.

### Option 1 : Utiliser le script Python (Recommandé)

```bash
# 1. Ouvrir un terminal
cd e

# 2. Activer l'environnement virtuel (si nécessaire)
# Sur Windows :
.venv\Scripts\activate
# Sur Mac/Linux :
source .venv/bin/activate

# 3. Installer psycopg2 si ce n'est pas déjà fait
pip install psycopg2-binary

# 4. Exécuter le script de création des tables
python setup_panier_db.py
```

### Option 2 : Utiliser le script SQL manuellement

1. Se connecter à votre base de données PostgreSQL via un outil comme :
   - pgAdmin
   - DBeaver
   - psql en ligne de commande
   - L'interface Neon (si vous utilisez Neon)

2. Exécuter le fichier `create_panier_tables.sql`

### Option 3 : Via psql en ligne de commande

```bash
# Se connecter à la base de données
psql "postgresql://neondb_owner:npg_YaC69HIAGyZn@ep-muddy-darkness-ai9gl7w1-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require" -f create_panier_tables.sql
```

## ✅ Vérification

Après avoir exécuté l'une des options ci-dessus, vérifiez que les tables existent :

```bash
python -c "from app import app, db; app.app_context().push(); print('Tables créées:', db.engine.table_names())"
```

Vous devriez voir `paniers` et `articles_panier` dans la liste.

## 🚀 Redémarrer l'application

Après avoir créé les tables, redémarrez votre application Flask :

```bash
python app.py
```

## 📋 Résumé des fichiers créés

| Fichier | Description |
|---------|-------------|
| `setup_panier_db.py` | Script Python pour créer les tables (à exécuter) |
| `create_panier_tables.sql` | Script SQL équivalent |
| `migrate_panier.py` | Script de migration Flask (alternative) |
| `PANIER_SYSTEME_RAPPORT.md` | Documentation complète du système |

## 🆘 En cas de problème

Si vous rencontrez toujours des erreurs, vérifiez :
1. Que vous avez exécuté le script de création des tables
2. Que la connexion à la base de données fonctionne
3. Que les tables `paniers` et `articles_panier` existent bien