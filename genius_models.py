"""
╔══════════════════════════════════════════════════════════════╗
║           GENIUSPAY MODELS — SQLAlchemy                     ║
║           Tables dédiées à l'intégration GeniusPay          ║
╚══════════════════════════════════════════════════════════════╝

Ces modèles sont utilisés pour :
- Stocker les transactions GeniusPay
- Tracer tous les appels API (requêtes/réponses)
- Journaliser les webhooks reçus
- Enregistrer les erreurs

Compatibilité : Flask-SQLAlchemy + PostgreSQL
Usage :
    from genius_models import GeniusTransaction, GeniusApiLog, GeniusWebhookLog, GeniusErrorLog
"""

from datetime import datetime, timezone
from app import db

# ═══════════════════════════════════════════════════════════════
# TABLE : GENIUS_TRANSACTIONS
# ═══════════════════════════════════════════════════════════════

class GeniusTransaction(db.Model):
    """
    Transactions de paiement GeniusPay.
    Stocke toutes les informations relatives à une transaction.
    """
    __tablename__ = "genius_transactions"

    id = db.Column(db.Integer, primary_key=True)
    # Références GeniusPay
    transaction_id = db.Column(db.String(100), unique=True, nullable=False, index=True)  # ID fourni par GeniusPay
    reference = db.Column(db.String(100), unique=True, nullable=False, index=True)        # Référence NectarPro
    # Détails de la transaction
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default="XOF")
    description = db.Column(db.Text, nullable=True)
    # Statut
    status = db.Column(db.String(50), default="pending", index=True)  # pending, processing, success, failed, cancelled
    status_message = db.Column(db.Text, nullable=True)
    # URL de paiement
    payment_url = db.Column(db.Text, nullable=True)
    # QR Code (si fourni par l'API)
    qr_code = db.Column(db.Text, nullable=True)
    # Informations client
    customer_name = db.Column(db.String(200), nullable=True)
    customer_email = db.Column(db.String(200), nullable=True)
    customer_phone = db.Column(db.String(50), nullable=True)
    # Lien vers l'utilisateur NectarPro (optionnel, pas de FK pour éviter les contraintes)
    user_id = db.Column(db.Integer, nullable=True)
    user_reference = db.Column(db.String(50), nullable=True)  # username ou uid
    # Métadonnées brutes (JSON)
    raw_request = db.Column(db.JSON, nullable=True)    # Payload envoyé à Genius
    raw_response = db.Column(db.JSON, nullable=True)   # Réponse reçue de Genius
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    # Liens callback
    callback_url = db.Column(db.Text, nullable=True)
    return_url = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<GeniusTransaction {self.reference} | {self.status} | {self.amount} {self.currency}>"

    def to_dict(self):
        """Sérialise la transaction en dictionnaire pour l'affichage."""
        return {
            "id": self.id,
            "transaction_id": self.transaction_id,
            "reference": self.reference,
            "amount": self.amount,
            "currency": self.currency,
            "description": self.description,
            "status": self.status,
            "status_message": self.status_message,
            "payment_url": self.payment_url,
            "qr_code": self.qr_code,
            "customer_name": self.customer_name,
            "customer_email": self.customer_email,
            "customer_phone": self.customer_phone,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "callback_url": self.callback_url,
            "return_url": self.return_url,
        }


# ═══════════════════════════════════════════════════════════════
# TABLE : GENIUS_API_LOGS
# ═══════════════════════════════════════════════════════════════

class GeniusApiLog(db.Model):
    """
    Historique de tous les appels à l'API GeniusPay.
    Chaque requête et réponse est journalisée.
    """
    __tablename__ = "genius_api_logs"

    id = db.Column(db.Integer, primary_key=True)
    # Détails de la requête
    method = db.Column(db.String(10), nullable=False)         # GET, POST, etc.
    endpoint = db.Column(db.String(255), nullable=False)      # Chemin de l'API
    request_data = db.Column(db.JSON, nullable=True)          # Payload envoyé
    request_headers = db.Column(db.JSON, nullable=True)        # Headers (sans les clés sensibles)
    # Détails de la réponse
    response_status = db.Column(db.Integer, nullable=True)     # Code HTTP
    response_data = db.Column(db.JSON, nullable=True)          # Corps de la réponse
    response_time = db.Column(db.Float, nullable=True)         # Temps de réponse en secondes
    # Statut de l'appel
    success = db.Column(db.Boolean, default=False, index=True)
    error_message = db.Column(db.Text, nullable=True)
    error_code = db.Column(db.String(50), nullable=True)
    # Lien transactionnel
    transaction_reference = db.Column(db.String(100), nullable=True, index=True)
    # Timestamp
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def __repr__(self):
        return f"<GeniusApiLog {self.method} {self.endpoint} | {self.response_status} | {self.response_time}s>"


# ═══════════════════════════════════════════════════════════════
# TABLE : GENIUS_WEBHOOK_LOGS
# ═══════════════════════════════════════════════════════════════

class GeniusWebhookLog(db.Model):
    """
    Historique des webhooks reçus de GeniusPay.
    Chaque webhook est enregistré pour audit et debug.
    """
    __tablename__ = "genius_webhook_logs"

    id = db.Column(db.Integer, primary_key=True)
    # Identifiants du webhook
    transaction_id = db.Column(db.String(100), nullable=True, index=True)
    reference = db.Column(db.String(100), nullable=True, index=True)
    # Contenu du webhook
    event_type = db.Column(db.String(50), nullable=True)       # Type d'événement
    raw_payload = db.Column(db.JSON, nullable=True)            # Payload brut reçu
    status = db.Column(db.String(50), nullable=True)           # Statut extrait du webhook
    # Validation
    signature_valid = db.Column(db.Boolean, default=False)     # Signature vérifiée ?
    signature_header = db.Column(db.String(500), nullable=True) # Header de signature
    # Traitement
    processed = db.Column(db.Boolean, default=False)            # Traité avec succès ?
    processing_error = db.Column(db.Text, nullable=True)        # Erreur éventuelle
    # Timestamps
    received_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    processed_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<GeniusWebhookLog {self.transaction_id} | {self.event_type} | {'OK' if self.processed else 'ERR'}>"


# ═══════════════════════════════════════════════════════════════
# TABLE : GENIUS_ERROR_LOGS
# ═══════════════════════════════════════════════════════════════

class GeniusErrorLog(db.Model):
    """
    Journal des erreurs spécifiques à l'intégration GeniusPay.
    Centralise toutes les erreurs pour faciliter le debugging.
    """
    __tablename__ = "genius_error_logs"

    id = db.Column(db.Integer, primary_key=True)
    # Contexte de l'erreur
    error_source = db.Column(db.String(100), nullable=True, index=True)  # Module ou fonction source
    error_type = db.Column(db.String(100), nullable=True)                # Type d'erreur (ConnectionError, Timeout, etc.)
    error_message = db.Column(db.Text, nullable=True)                    # Message d'erreur
    error_code = db.Column(db.String(50), nullable=True)                 # Code d'erreur HTTP ou code GeniusPay
    # Contexte additionnel
    transaction_reference = db.Column(db.String(100), nullable=True)
    endpoint = db.Column(db.String(255), nullable=True)
    request_data = db.Column(db.JSON, nullable=True)
    response_data = db.Column(db.JSON, nullable=True)
    # Traceback complet
    traceback = db.Column(db.Text, nullable=True)
    # Timestamp
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    # Résolu ?
    resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f"<GeniusErrorLog {self.error_type} | {self.error_code} | {self.created_at}>"


# ═══════════════════════════════════════════════════════════════
# FONCTION D'INITIALISATION DES TABLES
# ═══════════════════════════════════════════════════════════════

def init_genius_tables():
    """
    Crée les tables Genius si elles n'existent pas déjà.
    À appeler au démarrage de l'application.
    """
    try:
        existing_tables = db.inspect(db.engine).get_table_names()

        created = []
        for table_name, model in [
            ("genius_transactions", GeniusTransaction),
            ("genius_api_logs", GeniusApiLog),
            ("genius_webhook_logs", GeniusWebhookLog),
            ("genius_error_logs", GeniusErrorLog),
        ]:
            if table_name not in existing_tables:
                model.__table__.create(db.engine)
                created.append(table_name)

        if created:
            print(f"[GENIUS DB] Tables créées : {', '.join(created)}")
        else:
            print("[GENIUS DB] Toutes les tables Genius existent déjà.")

    except Exception as e:
        print(f"[GENIUS DB] Erreur création tables : {e}")