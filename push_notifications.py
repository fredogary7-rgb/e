"""
============================================================
NectarPro – Logique de Notifications Web Push VAPID
============================================================
Helpers VAPID, file d'attente, triggers automatiques,
nettoyage et stats.
Tous les modèles (PushSubscription, Notification, NotificationQueue)
sont définis dans app.py pour éviter les imports circulaires.
============================================================
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from threading import Thread, Lock

from flask import current_app, url_for

# Logger dédié
logger = logging.getLogger("nectarpro.push")
logger.setLevel(logging.INFO)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
    logger.addHandler(h)

# ── Verrou pour éviter les doublons d'envoi concurrents ──
_send_lock = Lock()

# ────────────────────────────────────────────────
# 1. HELPERS VAPID (clés, vérification, pywebpush)
# ────────────────────────────────────────────────

def _get_db():
    """Retourne l'instance db depuis app (import tardif pour éviter circulaire)."""
    from app import db
    return db

def _get_models():
    """Retourne les 3 modèles push (import tardif)."""
    from app import PushSubscription, Notification, NotificationQueue
    return PushSubscription, Notification, NotificationQueue

# ── Cache global pour l'objet clé privée cryptography ──
_vapid_private_key_obj = None
_vapid_private_key_obj_valid = False

def _get_vapid_private_key():
    """
    Retourne l'OBJET clé privée VAPID (cryptography) depuis les variables d'environnement.
    
    Charge la clé PEM depuis VAPID_PRIVATE_KEY, la parse en objet cryptography
    EC private key, et retourne l'objet directement.
    
    L'objet est utilisable par pywebpush sans parsing interne (évite le bug
    'header too long' d'OpenSSL sur certaines versions de pywebpush/cryptography).
    
    L'objet est caché globalement pour éviter de re-parser la clé à chaque envoi.
    """
    global _vapid_private_key_obj, _vapid_private_key_obj_valid
    
    # Retourner l'objet caché s'il est déjà chargé
    if _vapid_private_key_obj_valid and _vapid_private_key_obj is not None:
        return _vapid_private_key_obj

    raw = os.environ.get("VAPID_PRIVATE_KEY", "")
    if not raw:
        logger.error("❌ VAPID_PRIVATE_KEY absente de l'environnement")
        logger.error("   ⚠️  VAPID_PUBLIC_KEY est configurée mais pas VAPID_PRIVATE_KEY.")
        logger.error("   ⚠️  Les notifications push NE FONCTIONNERONT PAS.")
        logger.error("   ➜ Solution: sur Render → Environment → ajouter VAPID_PRIVATE_KEY")
        logger.error("   ➜ La clé privée doit être au format PEM PKCS8 (240 caractères, 5 lignes)")
        logger.error("   ➜ Exemple: -----BEGIN PRIVATE KEY-----\\nMIGHAgE...\\n-----END PRIVATE KEY-----")
        logger.error("   ➜ Générer une paire: python -c \"from push_notifications import generate_vapid_keys; pub, priv = generate_vapid_keys(); print(f'PUBLIC: {pub}'); print(f'PRIVATE: {priv}')\"")
        return None

    # ── DIAGNOSTIC COMPLET ──
    logger.info("🔍 DIAGNOSTIC VAPID_PRIVATE_KEY:")
    logger.info("   Longueur brute: %d caractères", len(raw))
    logger.info("   20 premiers caractères (repr): %s", repr(raw[:20]))
    logger.info("   20 derniers caractères (repr): %s", repr(raw[-20:]))
    logger.info("   Contient '-----BEGIN': %s", "-----BEGIN" in raw)
    logger.info("   Contient '-----END': %s", "-----END" in raw)
    logger.info("   Contient guillemets doubles: %s", '"' in raw)
    logger.info("   Contient guillemets simples: %s", "'" in raw)
    logger.info("   Contient espaces en début: %s", raw.startswith(" ") or raw.startswith("\t"))
    logger.info("   Contient espaces en fin: %s", raw.endswith(" ") or raw.endswith("\t"))
    logger.info("   Contient \\\\n littéral: %s", "\\n" in raw)
    logger.info("   Contient vrai \\n (LF): %s", "\n" in raw)
    logger.info("   Contient \\r (CR): %s", "\r" in raw)
    logger.info("   Contient \\r\\n (CRLF): %s", "\r\n" in raw)
    # Compter les lignes
    lines = raw.split("\n")
    logger.info("   Nombre de lignes (split sur LF): %d", len(lines))
    if len(lines) >= 3:
        logger.info("   Ligne 0: %s", repr(lines[0]))
        logger.info("   Ligne 1: %s", repr(lines[1]))
        logger.info("   Dernière ligne: %s", repr(lines[-1]))

    # ── NETTOYAGE ──
    cleaned = raw.strip()

    # Supprimer les guillemets englobants si présents (copie mal formatée)
    if (cleaned.startswith('"') and cleaned.endswith('"')) or \
       (cleaned.startswith("'") and cleaned.endswith("'")):
        logger.warning("⚠️ La clé est entourée de guillemets, suppression...")
        cleaned = cleaned[1:-1]

    # Remplacer CRLF → LF
    if "\r\n" in cleaned:
        logger.info("🔧 Conversion CRLF → LF")
        cleaned = cleaned.replace("\r\n", "\n")
    # Remplacer CR seul → LF
    elif "\r" in cleaned and "\n" not in cleaned:
        logger.info("🔧 Conversion CR → LF")
        cleaned = cleaned.replace("\r", "\n")

    # Restaurer les vrais \n à partir des \\n littéraux
    if "\\n" in cleaned:
        logger.info("🔧 Conversion \\\\n littéraux → vrais \\n")
        cleaned = cleaned.replace("\\n", "\n")

    # ── VALIDATION ──
    if "-----BEGIN PRIVATE KEY-----" not in cleaned and "-----BEGIN EC PRIVATE KEY-----" not in cleaned:
        logger.error("❌ VAPID_PRIVATE_KEY ne contient pas d'en-tête PEM valide.")
        logger.error("   Début de la clé nettoyée: %s", repr(cleaned[:100]))
        return None

    # Vérifier que la clé se termine par un END valide
    if "-----END PRIVATE KEY-----" not in cleaned and "-----END EC PRIVATE KEY-----" not in cleaned:
        logger.error("❌ VAPID_PRIVATE_KEY ne contient pas de pied PEM valide.")
        logger.error("   Fin de la clé nettoyée: %s", repr(cleaned[-50:]))
        return None

    # Vérifier la structure : doit avoir au moins 3 lignes (BEGIN, corps base64, END)
    pem_lines = [l for l in cleaned.split("\n") if l.strip()]
    if len(pem_lines) < 3:
        logger.error("❌ Structure PEM invalide: seulement %d ligne(s) non vides", len(pem_lines))
        for i, line in enumerate(pem_lines):
            logger.error("   Ligne %d: %s", i, repr(line))
        return None

    logger.info("✅ VAPID_PRIVATE_KEY nettoyée et validée (%d caractères, %d lignes)", len(cleaned), len(pem_lines))

    # ── CHARGER EN OBJET CRYPTOGRAPHY ──
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        import base64

        # Charger la clé privée PEM en objet cryptography
        priv_key_obj = serialization.load_pem_private_key(
            cleaned.encode("utf-8"),
            password=None,
        )
        
        # Vérifier que c'est bien une clé EC (EllipticCurvePrivateKey)
        if not hasattr(priv_key_obj, "private_numbers"):
            logger.error("❌ La clé chargée n'est pas une clé privée EC valide")
            return None

        logger.info("✅ Clé privée VAPID chargée en objet cryptography (type: %s)", type(priv_key_obj).__name__)

        # ── VÉRIFICATION DE LA CORRESPONDANCE PUBLIQUE/PRIVÉE ──
        pub_from_priv = priv_key_obj.public_key()
        pub_raw = pub_from_priv.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )
        pub_b64_from_priv = base64.urlsafe_b64encode(pub_raw).rstrip(b"=").decode("ascii")

        # Comparer avec VAPID_PUBLIC_KEY
        vapid_pub = os.environ.get("VAPID_PUBLIC_KEY", "").strip()
        if vapid_pub:
            if vapid_pub == pub_b64_from_priv:
                logger.info("✅ La paire VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY correspond parfaitement")
            else:
                logger.critical("❌❌❌ INCOMPATIBILITÉ DES CLÉS VAPID ! ❌❌❌")
                logger.critical("   VAPID_PUBLIC_KEY (env): %s...", vapid_pub[:40])
                logger.critical("   Publique dérivée de la privée: %s...", pub_b64_from_priv[:40])
                logger.critical("   Ces deux clés ne forment PAS une paire valide !")
                logger.critical("   Solution: régénérer une nouvelle paire avec generate_vapid_keys()")
                logger.critical("   et mettre à jour les deux variables d'environnement sur Render.")
                _vapid_private_key_obj_valid = False
                return None
        else:
            logger.warning("⚠️ VAPID_PUBLIC_KEY absente, impossible de vérifier la correspondance")

        # Mettre en cache l'objet
        _vapid_private_key_obj = priv_key_obj
        _vapid_private_key_obj_valid = True
        
        return priv_key_obj

    except Exception as e:
        logger.critical("❌ Impossible de charger la clé privée avec cryptography: %s", e)
        logger.critical("   La clé est corrompue ou dans un format non supporté.")
        logger.critical("   Clé nettoyée (repr complet): %s", repr(cleaned))
        _vapid_private_key_obj_valid = False
        return None

def _get_vapid_private_key_pem():
    """
    Retourne la clé privée VAPID au format PEM (string).
    Utile uniquement pour le diagnostic/logging, pas pour pywebpush.
    Préférer _get_vapid_private_key() qui retourne l'objet cryptography.
    """
    raw = os.environ.get("VAPID_PRIVATE_KEY", "")
    if not raw:
        return None
    cleaned = raw.strip()
    if "\\n" in cleaned:
        cleaned = cleaned.replace("\\n", "\n")
    if "\r\n" in cleaned:
        cleaned = cleaned.replace("\r\n", "\n")
    return cleaned

def _get_vapid_claims():
    """Retourne les claims VAPID (sub, aud)."""
    domain = os.environ.get("VAPID_SUBJECT", "mailto:admin@nectarpro.cc")
    return {"sub": domain}

def generate_vapid_keys():
    """Génère une nouvelle paire de clés VAPID (à utiliser une seule fois en dev)."""
    try:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import serialization
    except ImportError:
        logger.error("❌ cryptography non installé – pip install cryptography")
        return None, None

    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    private_pem = (
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        .decode("utf-8")
        .strip()
    )

    public_raw = (
        public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )
    )
    import base64
    public_b64 = base64.urlsafe_b64encode(public_raw).rstrip(b"=").decode("ascii")
    logger.info("✅ Nouvelles clés VAPID générées")
    return public_b64, private_pem

def get_vapid_public_key():
    """
    Retourne la clé publique VAPID (depuis l'env ou générée).
    Valide que la clé est au format URL-safe base64 attendu par le navigateur.
    """
    from_env = os.environ.get("VAPID_PUBLIC_KEY")
    if from_env:
        pub = from_env.strip()
        # Validation basique : la clé publique VAPID est en base64 URL-safe (65 octets non compressés)
        import base64
        try:
            # Tenter de décoder pour valider
            padded = pub + "=" * (4 - len(pub) % 4) if len(pub) % 4 else pub
            decoded = base64.urlsafe_b64decode(padded)
            if len(decoded) != 65:
                logger.warning("⚠️ VAPID_PUBLIC_KEY longueur anormale: %d octets (attendu 65)", len(decoded))
            else:
                logger.info("✅ VAPID_PUBLIC_KEY chargée et validée depuis l'environnement")
        except Exception as e:
            logger.error("❌ VAPID_PUBLIC_KEY invalide (base64 corrompu): %s", e)
            return None
        return pub

    # Génération automatique (fallback dev)
    logger.warning("⚠️ VAPID_PUBLIC_KEY absente, génération automatique (dev uniquement)")
    pub, priv = generate_vapid_keys()
    if pub:
        os.environ["VAPID_PUBLIC_KEY"] = pub
        os.environ["VAPID_PRIVATE_KEY"] = priv
    return pub

def _send_webpush_single(subscription_data, payload_dict):
    """Envoi unitaire via pywebpush. Retourne True si succès, False sinon.
    Gère automatiquement la suppression des abonnements invalides
    (404, 410, 401, expired)."""
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.error("❌ pywebpush non installé – pip install pywebpush")
        return False

    priv_key = _get_vapid_private_key()
    if not priv_key:
        return False

    # ── DIAGNOSTIC PRÉ-WEBPUSH ──
    claims = _get_vapid_claims()
    logger.info("🔍 PRÉ-WEBPUSH:")
    logger.info("   vapid_claims: %s", claims)
    logger.info("   priv_key type: %s", type(priv_key).__name__)
    
    # Vérifier si c'est un objet cryptography (EllipticCurvePrivateKey)
    is_crypto_obj = hasattr(priv_key, "private_numbers") and not isinstance(priv_key, str)
    if is_crypto_obj:
        logger.info("   ✅ Clé privée est un objet cryptography (sera passé directement à pywebpush)")
        # Extraire la taille de la clé
        try:
            key_size = priv_key.key_size
            logger.info("   Taille de la clé: %d bits", key_size)
        except Exception:
            pass
    elif isinstance(priv_key, str):
        logger.info("   priv_key longueur: %d", len(priv_key))
        logger.info("   priv_key contient BEGIN: %s", "-----BEGIN" in priv_key)
        logger.info("   priv_key contient END: %s", "-----END" in priv_key)
        if "-----BEGIN" not in priv_key:
            logger.warning("⚠️ La clé privée n'est PAS au format PEM ! pywebpush attend du PEM PKCS8.")
    else:
        logger.warning("⚠️ Type de clé inattendu: %s", type(priv_key))

    endpoint = subscription_data.get("endpoint", "inconnu")
    try:
        webpush(
            subscription_info={
                "endpoint": endpoint,
                "keys": {
                    "p256dh": subscription_data["p256dh"],
                    "auth": subscription_data["auth"],
                },
            },
            data=json.dumps(payload_dict),
            vapid_private_key=priv_key,
            vapid_claims=claims,
            timeout=15,
        )
        logger.info("✅ Notification push envoyée → %s...", endpoint[:80])
        return True
    except WebPushException as e:
        logger.warning("⚠️ WebPushException: %s", e)
        if hasattr(e, "response") and e.response is not None:
            status = e.response.status_code
            logger.warning("   ↳ Statut HTTP: %s", status)
            if status in (404, 410, 401):
                logger.warning("   ↳ Suppression de l'abonnement invalide (%s)", status)
                _delete_subscription(endpoint)
            else:
                logger.warning("   ↳ Statut non géré: %s", status)
        else:
            err_msg = str(e).lower()
            if "expired" in err_msg or "unsubscribed" in err_msg or "no such subscription" in err_msg:
                logger.warning("   ↳ Abonnement expiré détecté dans le message d'erreur")
                _delete_subscription(endpoint)
        return False
    except Exception as e:
        logger.error("❌ Erreur push inconnue: %s", e)
        err_msg = str(e).lower()
        if "subscription" in err_msg and ("expired" in err_msg or "invalid" in err_msg or "not found" in err_msg):
            _delete_subscription(endpoint)
        return False

def _delete_subscription(endpoint):
    """Supprime définitivement un abonnement invalide de la base de données."""
    db = _get_db()
    PushSubscription, _, _ = _get_models()
    try:
        deleted = PushSubscription.query.filter_by(endpoint=endpoint).delete()
        db.session.commit()
        if deleted:
            logger.info("🗑️ Abonnement supprimé (endpoint invalide): %s...", endpoint[:80])
    except Exception as e:
        db.session.rollback()
        logger.error("❌ Erreur suppression abonnement: %s", e)

def _build_payload(notification):
    """Construit le payload JSON envoyé au Service Worker."""
    return {
        "title": notification.titre,
        "body": notification.message,
        "icon": notification.icon or "/static/images/pwa/icon-192.png",
        "badge": "/static/images/pwa/icon-96.png",
        "image": notification.image or "",
        "tag": f"nectarpro-{notification.type or 'general'}-{notification.id}",
        "data": {
            "url": notification.url or "/",
            "notification_id": notification.id,
        },
        "requireInteraction": False,
        "vibrate": [200, 100, 200],
    }

# ────────────────────────────────────────────────
# 2. ENVOI (batch, asynchrone, file d'attente)
# ────────────────────────────────────────────────

def send_notification_to_user(user_id, titre, message, **kwargs):
    """Crée une Notification + met en file d'attente pour envoi push."""
    db = _get_db()
    PushSubscription, Notification, NotificationQueue = _get_models()

    notification = Notification(
        user_id=user_id,
        titre=titre,
        message=message,
        icon=kwargs.get("icon"),
        image=kwargs.get("image"),
        url=kwargs.get("url"),
        type=kwargs.get("type"),
    )
    db.session.add(notification)
    db.session.flush()

    queue_entry = NotificationQueue(
        notification_id=notification.id,
        statut="en_attente",
    )
    db.session.add(queue_entry)
    db.session.commit()

    Thread(
        target=_process_single_notification,
        args=(notification.id,),
        daemon=True,
    ).start()

    return notification

def _process_single_notification(notification_id):
    """Traite une notification de la file d'attente (appelée par le thread)."""
    from app import app
    db = _get_db()
    PushSubscription, Notification, NotificationQueue = _get_models()

    with app.app_context():
        logger.info("📨 Traitement notification #%s...", notification_id)
        queue_entry = (
            NotificationQueue.query
            .filter_by(notification_id=notification_id, statut="en_attente")
            .order_by(NotificationQueue.id.asc())
            .first()
        )
        if not queue_entry:
            logger.info("   ↳ Aucune entrée en attente trouvée")
            return

        queue_entry.statut = "en_cours"
        db.session.commit()

        notification = Notification.query.get(notification_id)
        if not notification:
            queue_entry.statut = "echec"
            queue_entry.erreur = "Notification introuvable"
            db.session.commit()
            logger.warning("   ↳ Notification #%s introuvable", notification_id)
            return

        payload = _build_payload(notification)
        logger.info("   ↳ Titre: %s, Type: %s", notification.titre, notification.type)

        subs = (
            PushSubscription.query
            .filter_by(user_id=notification.user_id, actif=True)
            .all()
        )
        logger.info("   ↳ %d abonnement(s) actif(s) pour user_id=%s", len(subs), notification.user_id)

        success_count = 0
        for i, sub in enumerate(subs):
            sub_data = {
                "endpoint": sub.endpoint,
                "p256dh": sub.p256dh,
                "auth": sub.auth,
            }
            if _send_webpush_single(sub_data, payload):
                success_count += 1
                sub.derniere_utilisation = datetime.now(timezone.utc)
            else:
                logger.warning("   ↳ Échec envoi #%d/%d", i + 1, len(subs))

        if success_count > 0:
            queue_entry.statut = "envoye"
            notification.date_envoi = datetime.now(timezone.utc)
            logger.info("✅ Notification #%s envoyée (%d/%d succès)", notification_id, success_count, len(subs))
        else:
            queue_entry.statut = "echec"
            queue_entry.erreur = "Aucun envoi réussi"
            logger.warning("❌ Notification #%s: aucun envoi réussi sur %d abonnements", notification_id, len(subs))

        queue_entry.date_traitement = datetime.now(timezone.utc)
        db.session.commit()

def send_bulk_notification(user_ids, titre, message, **kwargs):
    """Envoi par lots à une liste d'utilisateurs."""
    db = _get_db()
    PushSubscription, Notification, NotificationQueue = _get_models()

    notifications = []
    for uid in user_ids:
        notif = Notification(
            user_id=uid,
            titre=titre,
            message=message,
            icon=kwargs.get("icon"),
            image=kwargs.get("image"),
            url=kwargs.get("url"),
            type=kwargs.get("type"),
        )
        db.session.add(notif)
        notifications.append(notif)

    db.session.flush()

    for notif in notifications:
        qe = NotificationQueue(notification_id=notif.id, statut="en_attente")
        db.session.add(qe)

    db.session.commit()

    Thread(
        target=_process_batch,
        args=([n.id for n in notifications],),
        daemon=True,
    ).start()

    return len(notifications)

def _process_batch(notification_ids):
    """Traite un lot de notifications (appelée dans un thread)."""
    from app import app
    with app.app_context():
        for nid in notification_ids:
            _process_single_notification(nid)
            time.sleep(0.05)

def notify_all_users(titre, message, **kwargs):
    """Envoie une notification à TOUS les utilisateurs ayant un abonnement actif."""
    db = _get_db()
    PushSubscription, _, _ = _get_models()

    subs = (
        db.session.query(PushSubscription.user_id)
        .filter_by(actif=True)
        .distinct()
        .all()
    )
    user_ids = [s[0] for s in subs if s[0] is not None]
    if user_ids:
        return send_bulk_notification(user_ids, titre, message, **kwargs)
    return 0

# ────────────────────────────────────────────────
# 3. NETTOYAGE AUTOMATIQUE
# ────────────────────────────────────────────────

def cleanup_expired_subscriptions():
    """Supprime les abonnements inactifs depuis plus de 90 jours."""
    db = _get_db()
    PushSubscription, _, NotificationQueue = _get_models()
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    deleted = (
        PushSubscription.query
        .filter(PushSubscription.actif == False, PushSubscription.date_creation < cutoff)
        .delete()
    )
    db.session.commit()
    logger.info("Nettoyage: %d abonnements supprimés", deleted)
    return deleted

def cleanup_old_queue_entries():
    """Supprime les entrées de file d'attente traitées depuis plus de 30 jours."""
    db = _get_db()
    _, _, NotificationQueue = _get_models()
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    deleted = (
        NotificationQueue.query
        .filter(
            NotificationQueue.date_traitement.isnot(None),
            NotificationQueue.date_traitement < cutoff,
        )
        .delete()
    )
    db.session.commit()
    logger.info("Nettoyage queue: %d entrées supprimées", deleted)
    return deleted

# ────────────────────────────────────────────────
# 4. TRIGGERS AUTOMATIQUES
# ────────────────────────────────────────────────

def notify_deposit_accepted(user_id, montant, reference):
    return send_notification_to_user(
        user_id,
        titre="✅ Dépôt validé !",
        message=f"Votre dépôt de {montant:,.0f} XOF (réf. {reference}) a été validé avec succès.",
        url="/dashboard",
        type="depot_valide",
    )

def notify_deposit_rejected(user_id, montant, reference, motif=""):
    msg = f"Votre dépôt de {montant:,.0f} XOF (réf. {reference}) a été refusé."
    if motif:
        msg += f" Motif : {motif}"
    return send_notification_to_user(
        user_id,
        titre="❌ Dépôt refusé",
        message=msg,
        url="/dashboard",
        type="depot_refuse",
    )

def notify_retrait_accepted(user_id, montant):
    return send_notification_to_user(
        user_id,
        titre="💰 Retrait validé !",
        message=f"Votre retrait de {montant:,.0f} XOF a été traité avec succès.",
        url="/mes-retraits",
        type="retrait_valide",
    )

def notify_retrait_rejected(user_id, montant, motif=""):
    msg = f"Votre retrait de {montant:,.0f} XOF a été refusé."
    if motif:
        msg += f" Motif : {motif}"
    return send_notification_to_user(
        user_id,
        titre="⚠️ Retrait refusé",
        message=msg,
        url="/mes-retraits",
        type="retrait_refuse",
    )

def notify_new_order(user_id, commande_id):
    return send_notification_to_user(
        user_id,
        titre="🛒 Nouvelle commande",
        message=f"Votre commande #{commande_id} a bien été enregistrée.",
        url=f"/boutique/commandes/{commande_id}",
        type="nouvelle_commande",
    )

def notify_order_shipped(user_id, commande_id):
    return send_notification_to_user(
        user_id,
        titre="📦 Commande livrée",
        message=f"Votre commande #{commande_id} a été livrée !",
        url=f"/boutique/commandes/{commande_id}",
        type="commande_livree",
    )

def notify_new_message(user_id, expediteur, message_preview):
    return send_notification_to_user(
        user_id,
        titre=f"💬 Message de {expediteur}",
        message=message_preview[:200],
        url="/dashboard",
        type="nouveau_message",
    )

def notify_new_follower(user_id, follower_name):
    return send_notification_to_user(
        user_id,
        titre="👤 Nouvel abonné",
        message=f"{follower_name} s'est abonné à votre profil.",
        url="/profile",
        type="nouveau_follower",
    )

def notify_new_comment(user_id, commenter_name, preview):
    return send_notification_to_user(
        user_id,
        titre="💬 Nouveau commentaire",
        message=f"{commenter_name}: {preview[:200]}",
        url="/dashboard",
        type="nouveau_commentaire",
    )

def notify_new_like(user_id, liker_name):
    return send_notification_to_user(
        user_id,
        titre="❤️ Nouveau like",
        message=f"{liker_name} a aimé votre contenu.",
        url="/dashboard",
        type="nouveau_like",
    )

def notify_new_publicite(user_id, pub_titre):
    return send_notification_to_user(
        user_id,
        titre="📢 Nouvelle publicité",
        message=f"La publicité \"{pub_titre}\" est maintenant en ligne.",
        url="/publicites",
        type="nouvelle_publicite",
    )

def notify_new_product(user_id, product_name):
    return send_notification_to_user(
        user_id,
        titre="🆕 Nouveau produit",
        message=f"Découvrez \"{product_name}\" sur le market !",
        url="/products",
        type="nouveau_produit",
    )

def notify_promotion(user_id, titre, message):
    return send_notification_to_user(
        user_id,
        titre=f"🎉 {titre}",
        message=message,
        url="/dashboard",
        type="promotion",
    )

def notify_bonus(user_id, montant):
    return send_notification_to_user(
        user_id,
        titre="🎁 Bonus reçu !",
        message=f"Vous avez reçu un bonus de {montant:,.0f} XOF !",
        url="/dashboard",
        type="bonus",
    )

def notify_maintenance(titre, message):
    return notify_all_users(
        titre=f"🔧 {titre}",
        message=message,
        url="/",
        type="maintenance",
    )

def notify_update(version, changelog):
    return notify_all_users(
        titre=f"🔄 Mise à jour v{version}",
        message=changelog[:200],
        url="/",
        type="mise_a_jour",
    )

def notify_admin_announcement(titre, message):
    return notify_all_users(
        titre=f"📣 {titre}",
        message=message,
        url="/dashboard",
        type="annonce_admin",
    )

# ────────────────────────────────────────────────
# 5. STATISTIQUES
# ────────────────────────────────────────────────

def get_push_stats():
    """Retourne un dict de statistiques pour le dashboard admin."""
    db = _get_db()
    PushSubscription, Notification, NotificationQueue = _get_models()

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    total_subs = PushSubscription.query.filter_by(actif=True).count()

    browsers = (
        db.session.query(PushSubscription.browser, db.func.count(PushSubscription.id))
        .filter(PushSubscription.actif == True)
        .group_by(PushSubscription.browser)
        .order_by(db.func.count(PushSubscription.id).desc())
        .all()
    )

    platforms = (
        db.session.query(PushSubscription.platform, db.func.count(PushSubscription.id))
        .filter(PushSubscription.actif == True)
        .group_by(PushSubscription.platform)
        .order_by(db.func.count(PushSubscription.id).desc())
        .all()
    )

    total_envoyees = NotificationQueue.query.filter_by(statut="envoye").count()
    total_echecs = NotificationQueue.query.filter_by(statut="echec").count()

    total_lues = Notification.query.filter_by(lu=True).count()
    total_notifs = Notification.query.count()
    taux_ouverture = round((total_lues / total_notifs * 100), 2) if total_notifs > 0 else 0

    today_notifs = Notification.query.filter(Notification.date_creation >= today_start).count()
    week_notifs = Notification.query.filter(Notification.date_creation >= week_start).count()

    return {
        "total_abonnes": total_subs,
        "navigateurs": [{"nom": b, "total": c} for b, c in browsers if b],
        "plateformes": [{"nom": p, "total": c} for p, c in platforms if p],
        "total_envoyees": total_envoyees,
        "total_echecs": total_echecs,
        "total_lues": total_lues,
        "taux_ouverture": taux_ouverture,
        "today_notifs": today_notifs,
        "week_notifs": week_notifs,
    }

# ────────────────────────────────────────────────
# 6. CRÉATION AUTOMATIQUE DES TABLES
# ────────────────────────────────────────────────

def init_push_tables(app):
    """Crée les tables push si elles n'existent pas déjà."""
    db = _get_db()
    with app.app_context():
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        existing = inspector.get_table_names()
        needed = ["push_subscriptions", "notifications", "notification_queue"]
        missing = [t for t in needed if t not in existing]
        if missing:
            logger.info("Création des tables push manquantes: %s", missing)
            db.create_all()
            logger.info("Tables push créées avec succès.")
        else:
            logger.info("Tables push déjà existantes.")