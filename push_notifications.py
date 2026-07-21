"""
============================================================
NectarPro – Système de Notifications Web Push VAPID
============================================================
Modèles SQLAlchemy, helpers VAPID, file d'attente,
notifications automatiques et nettoyage.
Compatibilité : Android, Windows, Linux, macOS, Chrome,
Edge, Brave, Firefox, Samsung Internet.
Technologie : Web Push VAPID uniquement (pas de Firebase).
============================================================
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from threading import Thread, Lock

from flask import current_app, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB

# Logger dédié
logger = logging.getLogger("nectarpro.push")
logger.setLevel(logging.INFO)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
    logger.addHandler(h)

db = SQLAlchemy()  # sera lié au même db que app.py

# ── Verrou pour éviter les doublons d'envoi concurrents ──
_send_lock = Lock()

# ────────────────────────────────────────────────
# 1. MODÈLES SQLALCHEMY
# ────────────────────────────────────────────────

class PushSubscription(db.Model):
    """Abonnement Web Push d'un utilisateur (endpoint + clés VAPID)."""
    __tablename__ = "push_subscriptions"
    __table_args__ = (
        # Empêche les doublons (même endpoint + même user)
        db.UniqueConstraint("user_id", "endpoint", name="uq_user_endpoint"),
        # Index pour les recherches fréquentes
        db.Index("ix_push_sub_user_id", "user_id"),
        db.Index("ix_push_sub_endpoint", "endpoint"),
        db.Index("ix_push_sub_actif", "actif"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Clé étrangère vers la table user (à adapter selon le nom réel dans app.py)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Données de l'abonnement Web Push (obligatoires)
    endpoint = db.Column(db.Text, nullable=False)
    p256dh = db.Column(db.Text, nullable=False)
    auth = db.Column(db.Text, nullable=False)

    # Métadonnées du navigateur / appareil (pour analytics)
    user_agent = db.Column(db.Text)
    browser = db.Column(db.String(80))
    platform = db.Column(db.String(80))
    language = db.Column(db.String(20))
    timezone = db.Column(db.String(60))
    ip = db.Column(db.String(45))

    # Statut
    actif = db.Column(db.Boolean, default=True, nullable=False, index=True)

    # Dates
    date_creation = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    derniere_utilisation = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relation vers l'utilisateur
    user = db.relationship("User", backref=db.backref("push_subscriptions", lazy="dynamic", cascade="all, delete-orphan"))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "endpoint": self.endpoint,
            "browser": self.browser,
            "platform": self.platform,
            "actif": self.actif,
            "date_creation": self.date_creation.isoformat() if self.date_creation else None,
        }


class Notification(db.Model):
    """Notification envoyée (ou à envoyer) à un utilisateur."""
    __tablename__ = "notifications"
    __table_args__ = (
        db.Index("ix_notif_user_id", "user_id"),
        db.Index("ix_notif_lu", "lu"),
        db.Index("ix_notif_type", "type"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    titre = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    icon = db.Column(db.Text)
    image = db.Column(db.Text)
    url = db.Column(db.Text)
    type = db.Column(db.String(50))  # "depot", "retrait", "commande", "annonce", etc.
    lu = db.Column(db.Boolean, default=False, nullable=False)

    date_creation = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    date_envoi = db.Column(db.DateTime(timezone=True))

    # Relation
    user = db.relationship("User", backref=db.backref("notifications", lazy="dynamic", cascade="all, delete-orphan"))

    def to_dict(self):
        return {
            "id": self.id,
            "titre": self.titre,
            "message": self.message,
            "icon": self.icon,
            "image": self.image,
            "url": self.url,
            "type": self.type,
            "lu": self.lu,
            "date_creation": self.date_creation.isoformat() if self.date_creation else None,
        }


class NotificationQueue(db.Model):
    """File d'attente pour l'envoi asynchrone des notifications push."""
    __tablename__ = "notification_queue"
    __table_args__ = (
        db.Index("ix_nq_statut", "statut"),
        db.Index("ix_nq_notification_id", "notification_id"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    notification_id = db.Column(
        db.Integer,
        db.ForeignKey("notifications.id", ondelete="CASCADE"),
        nullable=True,
    )
    statut = db.Column(
        db.String(20),
        default="en_attente",
    )  # en_attente | en_cours | envoye | echec
    tentative = db.Column(db.Integer, default=0)
    erreur = db.Column(db.Text)
    date_creation = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    date_traitement = db.Column(db.DateTime(timezone=True))


# ────────────────────────────────────────────────
# 2. HELPERS VAPID (clés, vérification, pywebpush)
# ────────────────────────────────────────────────

def _get_vapid_private_key():
    """Retourne la clé privée VAPID depuis les variables d'environnement."""
    return os.environ.get("VAPID_PRIVATE_KEY")


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
        logger.error("cryptography non installé – pip install cryptography")
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
    # Encodage URL-safe base64 sans padding
    import base64

    public_b64 = base64.urlsafe_b64encode(public_raw).rstrip(b"=").decode("ascii")

    return public_b64, private_pem


def get_vapid_public_key():
    """Retourne la clé publique VAPID (générée ou depuis l'env)."""
    from_env = os.environ.get("VAPID_PUBLIC_KEY")
    if from_env:
        return from_env
    # Fallback : génère une paire temporaire (stocke dans l'env pour la session)
    pub, priv = generate_vapid_keys()
    if pub:
        os.environ["VAPID_PUBLIC_KEY"] = pub
        os.environ["VAPID_PRIVATE_KEY"] = priv
    return pub


def _send_webpush_single(subscription_data, payload_dict):
    """
    Envoi unitaire via pywebpush.
    subscription_data: dict avec endpoint, keys.p256dh, keys.auth
    payload_dict: dict avec title, body, icon, image, url, tag, etc.
    Retourne True si succès, False sinon.
    """
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.error("pywebpush non installé – pip install pywebpush")
        return False

    priv_key = _get_vapid_private_key()
    if not priv_key:
        logger.error("VAPID_PRIVATE_KEY absente de l'environnement")
        return False

    try:
        webpush(
            subscription_info={
                "endpoint": subscription_data["endpoint"],
                "keys": {
                    "p256dh": subscription_data["p256dh"],
                    "auth": subscription_data["auth"],
                },
            },
            data=json.dumps(payload_dict),
            vapid_private_key=priv_key,
            vapid_claims=_get_vapid_claims(),
            timeout=15,
        )
        return True
    except WebPushException as e:
        logger.warning("WebPushException: %s", e)
        if hasattr(e, "response") and e.response is not None:
            status = e.response.status_code
            # 404 / 410 → abonnement expiré ou invalide
            if status in (404, 410):
                _invalidate_subscription(subscription_data.get("endpoint"))
        return False
    except Exception as e:
        logger.error("Erreur push inconnue: %s", e)
        return False


def _invalidate_subscription(endpoint):
    """Désactive (actif=False) l'abonnement correspondant à un endpoint."""
    try:
        sub = PushSubscription.query.filter_by(endpoint=endpoint, actif=True).first()
        if sub:
            sub.actif = False
            db.session.commit()
            logger.info("Abonnement désactivé (endpoint invalide): %s", endpoint[:80])
    except Exception as e:
        db.session.rollback()
        logger.error("Erreur désactivation abonnement: %s", e)


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
# 3. ENVOI (batch, asynchrone, file d'attente)
# ────────────────────────────────────────────────

def send_notification_to_user(user_id, titre, message, **kwargs):
    """
    Crée une Notification + met en file d'attente pour envoi push.
    Paramètres optionnels: icon, image, url, type.
    Retourne l'objet Notification créé.
    """
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
    db.session.flush()  # obtient l'id

    # Ajout en file d'attente
    queue_entry = NotificationQueue(
        notification_id=notification.id,
        statut="en_attente",
    )
    db.session.add(queue_entry)
    db.session.commit()

    # Lancement asynchrone (thread séparé, non-bloquant)
    Thread(
        target=_process_single_notification,
        args=(notification.id,),
        daemon=True,
    ).start()

    return notification


def _process_single_notification(notification_id):
    """Traite une notification de la file d'attente (appelée par le thread)."""
    from app import app  # import ici pour éviter circulaire

    with app.app_context():
        queue_entry = (
            NotificationQueue.query
            .filter_by(notification_id=notification_id, statut="en_attente")
            .order_by(NotificationQueue.id.asc())
            .first()
        )
        if not queue_entry:
            return

        queue_entry.statut = "en_cours"
        db.session.commit()

        notification = Notification.query.get(notification_id)
        if not notification:
            queue_entry.statut = "echec"
            queue_entry.erreur = "Notification introuvable"
            db.session.commit()
            return

        payload = _build_payload(notification)

        # Récupère tous les abonnements actifs de l'utilisateur
        subs = (
            PushSubscription.query
            .filter_by(user_id=notification.user_id, actif=True)
            .all()
        )

        success_count = 0
        for sub in subs:
            sub_data = {
                "endpoint": sub.endpoint,
                "p256dh": sub.p256dh,
                "auth": sub.auth,
            }
            if _send_webpush_single(sub_data, payload):
                success_count += 1
                sub.derniere_utilisation = datetime.now(timezone.utc)

        if success_count > 0:
            queue_entry.statut = "envoye"
            notification.date_envoi = datetime.now(timezone.utc)
        else:
            queue_entry.statut = "echec"
            queue_entry.erreur = "Aucun envoi réussi"

        queue_entry.date_traitement = datetime.now(timezone.utc)
        db.session.commit()


def send_bulk_notification(user_ids, titre, message, **kwargs):
    """
    Envoi par lots à une liste d'utilisateurs.
    Lance un thread unique pour ne pas saturer.
    """
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

    # Traitement en arrière-plan
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
            time.sleep(0.05)  # 50ms de pause pour ne pas surcharger


def notify_all_users(titre, message, **kwargs):
    """
    Envoie une notification à TOUS les utilisateurs ayant un abonnement actif.
    """
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
# 4. NETTOYAGE AUTOMATIQUE
# ────────────────────────────────────────────────

def cleanup_expired_subscriptions():
    """Supprime les abonnements inactifs depuis plus de 90 jours."""
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
# 5. TRIGGERS AUTOMATIQUES (appelés depuis app.py)
# ────────────────────────────────────────────────

def notify_deposit_accepted(user_id, montant, reference):
    """Notification lors de la validation d'un dépôt."""
    return send_notification_to_user(
        user_id,
        titre="✅ Dépôt validé !",
        message=f"Votre dépôt de {montant:,.0f} XOF (réf. {reference}) a été validé avec succès.",
        url="/dashboard",
        type="depot_valide",
    )


def notify_deposit_rejected(user_id, montant, reference, motif=""):
    """Notification lors du refus d'un dépôt."""
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
    """Notification lors de la validation d'un retrait."""
    return send_notification_to_user(
        user_id,
        titre="💰 Retrait validé !",
        message=f"Votre retrait de {montant:,.0f} XOF a été traité avec succès.",
        url="/mes-retraits",
        type="retrait_valide",
    )


def notify_retrait_rejected(user_id, montant, motif=""):
    """Notification lors du refus d'un retrait."""
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
    """Notification lorsqu'une nouvelle commande est passée."""
    return send_notification_to_user(
        user_id,
        titre="🛒 Nouvelle commande",
        message=f"Votre commande #{commande_id} a bien été enregistrée.",
        url=f"/boutique/commandes/{commande_id}",
        type="nouvelle_commande",
    )


def notify_order_shipped(user_id, commande_id):
    """Notification lorsque la commande est livrée."""
    return send_notification_to_user(
        user_id,
        titre="📦 Commande livrée",
        message=f"Votre commande #{commande_id} a été livrée !",
        url=f"/boutique/commandes/{commande_id}",
        type="commande_livree",
    )


def notify_new_message(user_id, expediteur, message_preview):
    """Notification d'un nouveau message."""
    return send_notification_to_user(
        user_id,
        titre=f"💬 Message de {expediteur}",
        message=message_preview[:200],
        url="/dashboard",
        type="nouveau_message",
    )


def notify_new_follower(user_id, follower_name):
    """Notification lorsqu'un utilisateur s'abonne."""
    return send_notification_to_user(
        user_id,
        titre="👤 Nouvel abonné",
        message=f"{follower_name} s'est abonné à votre profil.",
        url="/profile",
        type="nouveau_follower",
    )


def notify_new_comment(user_id, commenter_name, preview):
    """Notification d'un nouveau commentaire."""
    return send_notification_to_user(
        user_id,
        titre="💬 Nouveau commentaire",
        message=f"{commenter_name}: {preview[:200]}",
        url="/dashboard",
        type="nouveau_commentaire",
    )


def notify_new_like(user_id, liker_name):
    """Notification d'un nouveau like."""
    return send_notification_to_user(
        user_id,
        titre="❤️ Nouveau like",
        message=f"{liker_name} a aimé votre contenu.",
        url="/dashboard",
        type="nouveau_like",
    )


def notify_new_publicite(user_id, pub_titre):
    """Notification d'une nouvelle publicité."""
    return send_notification_to_user(
        user_id,
        titre="📢 Nouvelle publicité",
        message=f"La publicité \"{pub_titre}\" est maintenant en ligne.",
        url="/publicites",
        type="nouvelle_publicite",
    )


def notify_new_product(user_id, product_name):
    """Notification d'un nouveau produit."""
    return send_notification_to_user(
        user_id,
        titre="🆕 Nouveau produit",
        message=f"Découvrez \"{product_name}\" sur le market !",
        url="/products",
        type="nouveau_produit",
    )


def notify_promotion(user_id, titre, message):
    """Notification promotionnelle."""
    return send_notification_to_user(
        user_id,
        titre=f"🎉 {titre}",
        message=message,
        url="/dashboard",
        type="promotion",
    )


def notify_bonus(user_id, montant):
    """Notification de bonus."""
    return send_notification_to_user(
        user_id,
        titre="🎁 Bonus reçu !",
        message=f"Vous avez reçu un bonus de {montant:,.0f} XOF !",
        url="/dashboard",
        type="bonus",
    )


def notify_maintenance(titre, message):
    """Notification de maintenance (tous les utilisateurs)."""
    return notify_all_users(
        titre=f"🔧 {titre}",
        message=message,
        url="/",
        type="maintenance",
    )


def notify_update(version, changelog):
    """Notification de mise à jour (tous les utilisateurs)."""
    return notify_all_users(
        titre=f"🔄 Mise à jour v{version}",
        message=changelog[:200],
        url="/",
        type="mise_a_jour",
    )


def notify_admin_announcement(titre, message):
    """Annonce administrateur (tous les utilisateurs)."""
    return notify_all_users(
        titre=f"📣 {titre}",
        message=message,
        url="/dashboard",
        type="annonce_admin",
    )


# ────────────────────────────────────────────────
# 6. STATISTIQUES (pour le dashboard admin)
# ────────────────────────────────────────────────

def get_push_stats():
    """Retourne un dict de statistiques pour le dashboard admin."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    total_subs = PushSubscription.query.filter_by(actif=True).count()

    # Navigateurs
    browsers = (
        db.session.query(PushSubscription.browser, db.func.count(PushSubscription.id))
        .filter(PushSubscription.actif == True)
        .group_by(PushSubscription.browser)
        .order_by(db.func.count(PushSubscription.id).desc())
        .all()
    )

    # Plateformes
    platforms = (
        db.session.query(PushSubscription.platform, db.func.count(PushSubscription.id))
        .filter(PushSubscription.actif == True)
        .group_by(PushSubscription.platform)
        .order_by(db.func.count(PushSubscription.id).desc())
        .all()
    )

    # Notifications envoyées
    total_envoyees = NotificationQueue.query.filter_by(statut="envoye").count()
    total_echecs = NotificationQueue.query.filter_by(statut="echec").count()

    # Notifications ouvertes (lu = True)
    total_lues = Notification.query.filter_by(lu=True).count()

    # Taux d'ouverture
    total_notifs = Notification.query.count()
    taux_ouverture = round((total_lues / total_notifs * 100), 2) if total_notifs > 0 else 0

    # Aujourd'hui / cette semaine
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
# 7. CRÉATION AUTOMATIQUE DES TABLES
# ────────────────────────────────────────────────

def init_push_tables(app):
    """Crée les tables push si elles n'existent pas déjà."""
    with app.app_context():
        # Vérifie si les tables existent déjà
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