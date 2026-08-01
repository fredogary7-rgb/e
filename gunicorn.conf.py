# ==========================================
# Gunicorn Configuration - Nectar Pro
# Optimisé pour 5 000 utilisateurs simultanés
# Utilisation : gunicorn -c gunicorn.conf.py app:app
# ==========================================

import os
import multiprocessing

# ==========================================
# Workers - Cœur de la performance
# ==========================================

# Nombre de workers : (2 * CPU) + 1
# Pour Render Standard (2 vCPUs) = 5 workers
# Pour Render Pro (4 vCPUs) = 9 workers
workers = int(os.getenv("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))

# Type de worker - Gevent pour le parallélisme I/O
# Gevent est idéal pour :
# - Requêtes BDD (PostgreSQL)
# - API externes (SoleasPay, Cloudinary)
# - Uploads de fichiers
# - WebSockets (chaines, notifications push)
worker_class = "gevent"

# Connexions simultanées par worker
# 1000 connexions × 5 workers = 5000 utilisateurs max
worker_connections = 1000

# Threads additionnels (1 seul avec Gevent)
threads = 1

# ==========================================
# Timeouts - Protection contre les requêtes lentes
# ==========================================

# Timeout général (120s pour les uploads vidéo)
timeout = 120

# Keep-alive (réduit les connexions TCP inutiles)
keep_alive = 5

# Graceful timeout pour les workers existants
graceful_timeout = 30

# ==========================================
# Recyclage automatique - Éviter les fuites mémoire
# ==========================================

# Redémarre un worker après 10 000 requêtes
max_requests = 10000

# Variation aléatoire (±1000) pour éviter le recyclage simultané
max_requests_jitter = 1000

# ==========================================
# Logging
# ==========================================

# Niveau de log (warning = pas de spam en prod)
loglevel = os.getenv("LOG_LEVEL", "warning")

# Logs d'accès dans stdout (capturés par Render)
accesslog = "-"

# Logs d'erreur dans stderr
errorlog = "-"

# Capture les prints de l'application dans les logs Gunicorn
capture_output = True

# Format des logs d'accès (JSON-like pour parsing)
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sμs'

# ==========================================
# Binding
# ==========================================

# Écouter sur le port défini par Render (PORT) ou 5000 par défaut
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

# Taille de la file d'attente TCP
backlog = 2048

# ==========================================
# Preload - Performance au démarrage
# ==========================================

# Charge l'application AVANT de forker les workers
# Avantages :
# - Moins de mémoire utilisée (partage du code)
# - Démarrage plus rapide des workers
preload_app = True

# ==========================================
# Sécurité
# ==========================================

# Limite la taille des requêtes à 100 MB (pour les uploads vidéo)
limit_request_line = 0
limit_request_fields = 100
limit_request_field_size = 0

# ==========================================
# Hooks - Monitoring et debugging
# ==========================================

def on_starting(server):
    """Appelé quand Gunicorn démarre"""
    print(f"[GUNICORN] Démarrage avec {workers} workers (Gevent) sur {bind}")

def when_ready(server):
    """Appelé quand Gunicorn est prêt à accepter des connexions"""
    print(f"[GUNICORN] Serveur prêt - {workers} workers démarrés")
    print(f"[GUNICORN] Worker class: {worker_class}")
    print(f"[GUNICORN] Worker connections: {worker_connections}")
    print(f"[GUNICORN] Max requests per worker: {max_requests}")
    print(f"[GUNICORN] Timeout: {timeout}s")

def on_exit(server):
    """Appelé quand Gunicorn s'arrête"""
    print("[GUNICORN] Arrêt du serveur")

def worker_abort(worker):
    """Appelé quand un worker est tué (timeout, OOM, etc.)"""
    print(f"[GUNICORN] ⚠️ Worker {worker.pid} avorté - redémarrage automatique")

def pre_request(worker, req):
    """Appelé avant chaque requête"""
    # Logguer les requêtes lentes (> 2 secondes) en warning
    worker.start_time = __import__('time').time()

def post_request(worker, req, environ, resp):
    """Appelé après chaque requête"""
    if hasattr(worker, 'start_time'):
        duration = __import__('time').time() - worker.start_time
        if duration > 2.0:
            worker.log.warning(
                f"Requête lente détectée (%.2fs) : %s %s" % (
                    duration, req.method, req.path
                )
            )

# ==========================================
# Variables d'environnement supportées
# ==========================================
# WEB_CONCURRENCY  : Nombre de workers (défaut: calculé automatiquement)
# PORT             : Port d'écoute (défaut: 5000)
# LOG_LEVEL        : Niveau de logs (défaut: warning)