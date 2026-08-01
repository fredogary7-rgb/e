# 🚀 RAPPORT COMPLET D'OPTIMISATION – Nectar Pro

**Date :** 01/08/2026  
**Cible :** 5 000 utilisateurs simultanés  
**Stack :** Flask 3.1.2 + SQLAlchemy 2.0 + PostgreSQL (Neon) + Gunicorn + Gevent  

---

## 📊 1. DIAGNOSTIC DE L'ÉTAT ACTUEL

### 1.1 Configuration Base de Données

| Paramètre | Valeur actuelle | Problème |
|-----------|----------------|----------|
| `pool_size` | 10 | Trop bas pour 5000 utilisateurs |
| `max_overflow` | 20 | OK temporairement |
| `pool_recycle` | 280s (via engine_options) + 1800s (via create_engine) | **CONFLIT** : deux valeurs différentes → 1800s prévaut, trop long pour Neon |
| `pool_timeout` | 20s (engine_options) + 30s (create_engine) | **CONFLIT** |
| `pool_pre_ping` | True | ✅ Bon |
| `channel_binding` | require | Peut causer des échecs de connexion |

**🔴 CRITIQUE :** Double configuration `create_engine` + `SQLALCHEMY_ENGINE_OPTIONS` conflit.  
**🔴 CRITIQUE :** `pool_recycle` à 1800s → connexions périmées après 5 min chez Neon (timeout idle 300s).

### 1.2 Modèle User – Analyse des Index

| Colonne | Indexée | Utilisation |
|---------|---------|-------------|
| `username` | ✅ | Connexion, parrainage, recherches |
| `email` | ✅ | Connexion, réinitialisation |
| `phone` | ✅ | Connexion, dépôts, retraits |
| `solde_revenu` | ✅ | Classement |
| `parrain` | ❌ | **Très utilisé** pour les filleuls, commissions |
| `is_admin` | ❌ | Filtrages admin |
| `is_banned` | ❌ | Filtrages |
| `country` | ❌ | Filtrages |
| `date_creation` | ❌ | Tris, classements |
| `last_login` | ❌ | Statistiques |
| `wallet_country` | ❌ | Filtres pays |
| `wallet_operator` | ❌ | Filtres opérateurs |

### 1.3 Modèle Depot – Analyse des Index

| Colonne | Indexée | Utilisation |
|---------|---------|-------------|
| `user_id` | ❌ (FK mais pas d'index explicite) | **Très utilisé** – historique dépôts |
| `user_name` | ❌ | Ancien système |
| `statut` | ❌ | **Très utilisé** – filtres pending/valide/rejete |
| `date` | ❌ | Tris |
| `reference` | ❌ | Recherches |

### 1.4 Modèle Retrait – Analyse des Index

| Colonne | Indexée | Utilisation |
|---------|---------|-------------|
| `user_id` | ❌ | **Très utilisé** |
| `statut` | ❌ | Filtres |
| `date` | ❌ | Tris |
| `reference_soleaspay` | ❌ | Synchro |

### 1.5 Autres Tables Critiques

| Table | Colonnes non indexées | Impact |
|-------|----------------------|--------|
| `Commission` | `parrain_uid`, `date` | Élevé |
| `notification` | `user_id` déjà ✅, `lu`, `date_creation` | Moyen |
| `commandes` | `user_id`, `boutique_id`, `statut`, `date_creation` | Élevé |
| `publicites` | `user_id`, `est_actif`, `date_creation` | Élevé |
| `produits` | ✅ la plupart | OK |
| `user_tasks` | `user_id`, `task_id` | Moyen |
| `follows` | `follower_id`, `following_id` | Élevé |

### 1.6 Problèmes N+1 Détectés

| Route | Problème |
|-------|----------|
| `/dashboard` | Chargement séparé des tâches, notifications, parrainage → multiple queries |
| `/admin/classement-soldes` | ✅ déjà corrigé avec raw SQL |
| `/admin/users` | Pas de pagination efficace |
| `/publicite` | Chargement lazy des commentaires, likes, sauvegardes |
| `/boutique/*` | Relations imbriquées sans `joinedload` |

### 1.7 Absence Totale de Cache

- ❌ Aucun système de cache (ni Redis, ni Memcached, ni Flask-Caching)
- ❌ Les dashboards refont les mêmes requêtes à chaque chargement
- ❌ Pas de cache HTTP (Cache-Control: no-cache partout)
- ❌ Les templates Jinja2 sont recompilés à chaque requête

---

## 🔧 2. CORRECTIONS IMMÉDIATES

### 2.1 Pool PostgreSQL – Configuration Optimale

```python
# Remplace la config actuelle (lignes 134-150)
DATABASE_URL = "postgresql://neondb_owner:npg_YaC69HIAGyZn@ep-muddy-darkness-ai9gl7w1-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require"

engine = create_engine(
    DATABASE_URL,
    pool_size=20,          # 20 connexions par worker (au lieu de 10)
    max_overflow=40,       # 40 supplémentaires en pic
    pool_timeout=10,       # Timeout réduit à 10s
    pool_recycle=280,      # Recyclage avant timeout Neon (300s)
    pool_pre_ping=True,    # Vérifie la validité avant utilisation
    echo_pool=False,       # Pas de logs pool en production
)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 280,
    "pool_timeout": 10,
    "pool_size": 20,
    "max_overflow": 40,
}
```

### 2.2 Index Manquants – Script SQL

```sql
-- USER
CREATE INDEX IF NOT EXISTS idx_user_parrain ON "user" (parrain);
CREATE INDEX IF NOT EXISTS idx_user_is_admin ON "user" (is_admin);
CREATE INDEX IF NOT EXISTS idx_user_is_banned ON "user" (is_banned);
CREATE INDEX IF NOT EXISTS idx_user_country ON "user" (country);
CREATE INDEX IF NOT EXISTS idx_user_date_creation ON "user" (date_creation);
CREATE INDEX IF NOT EXISTS idx_user_last_login ON "user" (last_login);
CREATE INDEX IF NOT EXISTS idx_user_wallet_country ON "user" (wallet_country);
CREATE INDEX IF NOT EXISTS idx_user_wallet_operator ON "user" (wallet_operator);

-- DEPOT
CREATE INDEX IF NOT EXISTS idx_depot_user_id ON depot (user_id);
CREATE INDEX IF NOT EXISTS idx_depot_statut ON depot (statut);
CREATE INDEX IF NOT EXISTS idx_depot_date ON depot (date);

-- RETRAIT
CREATE INDEX IF NOT EXISTS idx_retrait_user_id ON retrait (user_id);
CREATE INDEX IF NOT EXISTS idx_retrait_statut ON retrait (statut);
CREATE INDEX IF NOT EXISTS idx_retrait_date ON retrait (date);
CREATE INDEX IF NOT EXISTS idx_retrait_reference_soleaspay ON retrait (reference_soleaspay);

-- COMMISSION
CREATE INDEX IF NOT EXISTS idx_commission_parrain_uid ON commission (parrain_uid);
CREATE INDEX IF NOT EXISTS idx_commission_date ON commission (date);

-- COMMANDES
CREATE INDEX IF NOT EXISTS idx_commandes_user_id ON commandes (user_id);
CREATE INDEX IF NOT EXISTS idx_commandes_boutique_id ON commandes (boutique_id);
CREATE INDEX IF NOT EXISTS idx_commandes_statut ON commandes (statut);
CREATE INDEX IF NOT EXISTS idx_commandes_date ON commandes (date_creation);

-- PUBLICITES
CREATE INDEX IF NOT EXISTS idx_publicites_user_id ON publicites (user_id);
CREATE INDEX IF NOT EXISTS idx_publicites_actif ON publicites (est_actif);
CREATE INDEX IF NOT EXISTS idx_publicites_date ON publicites (date_creation);

-- NOTIFICATIONS
CREATE INDEX IF NOT EXISTS idx_notifications_user_lu ON notifications (user_id, lu);
CREATE INDEX IF NOT EXISTS idx_notifications_date ON notifications (date_creation);

-- USER_TASKS
CREATE INDEX IF NOT EXISTS idx_user_tasks_user_id ON user_tasks (user_id);
CREATE INDEX IF NOT EXISTS idx_user_tasks_task_id ON user_tasks (task_id);

-- FOLLOWS
CREATE INDEX IF NOT EXISTS idx_follows_follower ON follows (follower_id);
CREATE INDEX IF NOT EXISTS idx_follows_following ON follows (following_id);

-- PANIER
CREATE INDEX IF NOT EXISTS idx_paniers_user_id ON paniers (user_id);
```

---

## 📦 3. SYSTÈME DE CACHE RECOMMANDÉ

### 3.1 Flask-Caching + Redis

```python
# Installation
# pip install flask-caching redis

from flask_caching import Cache

cache_config = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "nectarpro_",
}

cache = Cache(app, config=cache_config)

# Utilisation sur les routes lourdes :
@app.route("/dashboard")
@login_required
@cache.cached(timeout=60, key_prefix=lambda: f"dashboard_{session.get('user_id')}")
def dashboard_page():
    ...
```

### 3.2 Fallback SimpleCache (sans Redis)

Si Redis n'est pas disponible, utiliser `SimpleCache` en mémoire :

```python
cache_config = {
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 120,
    "CACHE_THRESHOLD": 500,  # Max 500 entrées en cache
}
```

### 3.3 Stratégie de Cache par Route

| Route | TTL | Stratégie |
|-------|-----|-----------|
| `/` (index) | 300s | Cache global |
| `/dashboard` | 30s | Cache par user_id |
| `/admin/classement-soldes` | 60s | Cache global |
| `/publicite` | 60s | Cache global avec invalidation |
| `/api/notifications` | 15s | Cache par user_id |
| `/market` | 120s | Cache global |
| `/produit/<slug>` | 300s | Cache par slug |

### 3.4 Invalidation du Cache

```python
# Quand un utilisateur fait un dépôt → invalider son dashboard
cache.delete(f"dashboard_{user.id}")

# Quand une pub est créée → invalider le feed
cache.delete("publicite_feed")

# Pattern d'invalidation globale
cache.delete_many("dashboard_*")  # Attention : pas supporté par tous les backends
```

---

## ⚡ 4. OPTIMISATIONS SQLALCHEMY

### 4.1 Remplacer les `.all()` massifs par de la pagination

```python
# AVANT (charge TOUS les utilisateurs en mémoire)
users = User.query.all()

# APRÈS (pagination)
page = request.args.get('page', 1, type=int)
users = User.query.paginate(page=page, per_page=50, error_out=False)
```

### 4.2 Utiliser `joinedload` / `selectinload` pour éviter N+1

```python
from sqlalchemy.orm import joinedload, selectinload

# AVANT : N+1 requêtes
publicites = Publicite.query.all()
for pub in publicites:
    print(pub.createur.username)  # 1 requête par publicité

# APRÈS : 1 seule requête
publicites = Publicite.query.options(
    joinedload(Publicite.createur),
    joinedload(Publicite.boutique)
).all()
```

### 4.3 Requêtes Agrégées avec `func`

```python
# AVANT : boucle Python
total = 0
for depot in user.depots:
    if depot.statut == 'valide':
        total += depot.montant

# APRÈS : agrégation SQL
from sqlalchemy import func
total = db.session.query(func.sum(Depot.montant)).filter(
    Depot.user_id == user.id,
    Depot.statut == 'valide'
).scalar() or 0
```

### 4.4 Utiliser `defer()` pour les colonnes lourdes

```python
# Ne charge pas les colonnes binaires/larges quand pas nécessaire
user = User.query.options(
    db.defer(User.password),
    db.defer(User.pin_code)
).filter_by(username=username).first()
```

---

## 🖥️ 5. CONFIGURATION GUNICORN OPTIMALE

### 5.1 Procfile actuel
```
web: gunicorn app:app
```

### 5.2 Procfile optimisé
```
web: gunicorn app:app --workers 4 --worker-class gevent --worker-connections 1000 --max-requests 10000 --max-requests-jitter 1000 --timeout 120 --keep-alive 5 --log-level warning --access-logfile - --error-logfile -
```

**Explication :**
| Paramètre | Valeur | Justification |
|-----------|--------|---------------|
| `--workers 4` | $(2*CPU)+1 | Pour Render (2 CPUs) |
| `--worker-class gevent` | Gevent | Meilleur pour I/O (DB, API externes) |
| `--worker-connections 1000` | 1000 | Supporte 1000 connexions simultanées par worker |
| `--max-requests 10000` | 10000 | Recyclage des workers pour éviter les fuites mémoire |
| `--max-requests-jitter 1000` | 1000 | Variation aléatoire pour éviter recyclage simultané |
| `--timeout 120` | 120s | Timeout augmenté pour les uploads |
| `--keep-alive 5` | 5s | Réduit le temps d'attente des connexions inactives |

---

## 📈 6. GUNICORN CONFIG FILE

Créer `gunicorn.conf.py` :

```python
import os
import multiprocessing

# Worker
workers = int(os.getenv("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
worker_class = "gevent"
worker_connections = 1000
threads = 1

# Timeouts
timeout = 120
keep_alive = 5
graceful_timeout = 30

# Restart
max_requests = 10000
max_requests_jitter = 1000

# Logging
loglevel = "warning"
accesslog = "-"
errorlog = "-"
capture_output = True

# Server
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
backlog = 2048
preload_app = True
```

---

## 📊 7. KPI DE PERFORMANCE CIBLES

| Métrique | Actuel (estimé) | Cible |
|----------|-----------------|-------|
| Temps réponse moyen | ~500-800ms | < 300ms |
| p95 latence | ~2s | < 800ms |
| Requêtes/seconde | ~50 | > 500 |
| Taux d'erreur | ~2% | < 0.1% |
| Connexions DB | 10-30 | Pool géré |
| Cache hit ratio | 0% | > 80% |

---

## 🧪 8. STRATÉGIE DE TEST DE CHARGE

### 8.1 Préparation

1. **Base de données de test** séparée (clone de la prod)
2. **5000 utilisateurs de test** avec différents rôles et soldes
3. **Données réalistes** : dépôts, retraits, commissions, notifications

### 8.2 Scénarios k6

| Scénario | Poids | Description |
|----------|-------|-------------|
| Connexion | 15% | POST /connexion |
| Dashboard | 25% | GET /dashboard |
| Notifications | 10% | GET /api/notifications |
| Recherche | 10% | GET /market?q=... |
| Portefeuille | 15% | GET /dashboard (section solde) |
| Transfert | 10% | POST /retrait |
| Navigation | 10% | GET /publicite, /boutique |
| Déconnexion | 5% | GET /logout |

### 8.3 Montée en charge progressive

| Étape | Utilisateurs | Durée | Objectif |
|-------|-------------|-------|----------|
| 1 | 50 | 2 min | Warmup |
| 2 | 100 | 3 min | Validation baseline |
| 3 | 250 | 3 min | Charge modérée |
| 4 | 500 | 3 min | Charge moyenne |
| 5 | 1 000 | 5 min | Charge élevée |
| 6 | 2 000 | 5 min | Stress test |
| 7 | 3 000 | 5 min | Stress test |
| 8 | 5 000 | 5 min | Pic maximum |

### 8.4 Surveillance en temps réel

- **CPU** : `htop` ou dashboard Render
- **RAM** : `free -m` ou dashboard Render
- **DB** : `SELECT * FROM pg_stat_activity;`
- **Logs** : `tail -f access.log | p50, p95, p99`
- **Erreurs** : `grep " 500 \| 502 \| 504 " access.log | wc -l`

---

## 🛡️ 9. RECOMMANDATIONS DE SÉCURITÉ

1. **Rate Limiting** : Ajouter Flask-Limiter
   ```python
   pip install Flask-Limiter
   from flask_limiter import Limiter
   limiter = Limiter(app, key_func=lambda: session.get('user_id'))
   
   @app.route("/connexion", methods=["POST"])
   @limiter.limit("10 per minute")  # Max 10 tentatives/min
   def connexion_page():
       ...
   ```

2. **Timeout des requêtes BDD** : Déjà configuré à 10s ✅

3. **Circuit Breaker** pour les API externes (SoleasPay) :
   ```python
   import time
   from functools import wraps
   
   def circuit_breaker(max_failures=3, reset_timeout=30):
       failures = 0
       last_failure_time = 0
       
       def decorator(func):
           @wraps(func)
           def wrapper(*args, **kwargs):
               nonlocal failures, last_failure_time
               if failures >= max_failures:
                   if time.time() - last_failure_time < reset_timeout:
                       raise Exception("Circuit breaker ouvert")
                   failures = 0
               try:
                   result = func(*args, **kwargs)
                   failures = 0
                   return result
               except:
                   failures += 1
                   last_failure_time = time.time()
                   raise
           return wrapper
       return decorator
   ```

---

## 📋 10. PLAN D'ACTION (Ordre de Priorité)

| Priorité | Action | Impact | Effort |
|----------|--------|--------|--------|
| 🔴 P0 | Corriger `pool_recycle` conflit | Critique | 5 min |
| 🔴 P0 | Configurer Gunicorn optimal | Critique | 10 min |
| 🔴 P0 | Ajouter les index SQL manquants | Élevé | 15 min |
| 🟡 P1 | Installer Flask-Caching | Élevé | 30 min |
| 🟡 P1 | Remplacer `.all()` par pagination | Élevé | 1h |
| 🟡 P1 | Ajouter `joinedload` sur routes lourdes | Élevé | 1h |
| 🟢 P2 | Ajouter Flask-Limiter | Moyen | 30 min |
| 🟢 P2 | Circuit breaker pour API externes | Moyen | 30 min |
| 🟢 P2 | Tests de charge k6 | Validation | 2h |
| 🔵 P3 | Redis pour le cache | Moyen | 1h |
| 🔵 P3 | CDN pour les statics | Faible | 30 min |

---

## 📝 11. FICHIERS GÉNÉRÉS

| Fichier | Description |
|---------|-------------|
| `optimize_db.sql` | Script d'ajout des index manquants |
| `optimize_app.py` | Patch des fonctions critiques (pool, cache, N+1) |
| `gunicorn.conf.py` | Configuration Gunicorn optimisée |
| `loadtest.js` | Script k6 pour tests de charge |
| `create_test_users.py` | Script de création des 5000 utilisateurs de test |
| `monitor.py` | Script de monitoring des performances |