"""
╔══════════════════════════════════════════════════════════════╗
║           GENIUSPAY - Module Officiel v3.0                  ║
║           Documentation : https://geniuspay.ci/docs/api     ║
║           Base URL : https://geniuspay.ci/api/v1/merchant   ║
╚══════════════════════════════════════════════════════════════╝

Endpoints documentés :
  POST   /api/v1/merchant/payments            → Créer un paiement
  GET    /api/v1/merchant/payments             → Lister les paiements
  GET    /api/v1/merchant/payments/{reference} → Récupérer un paiement
  GET    /api/v1/merchant/pawapay/providers    → Fournisseurs MMO (dynamique)
  POST   /api/v1/merchant/webhooks             → Créer un webhook
  GET    /api/v1/merchant/webhooks             → Lister les webhooks

Authentification : Headers X-API-Key + X-API-Secret

Statuts : pending, processing, completed, failed, expired

Webhook events : payment.success, payment.failed, cashout.completed
"""

import os
import sys
import json
import logging
import time
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple, List

import requests

# ─── LOGGER ──────────────────────────────────────────────────
logger = logging.getLogger("geniuspay")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(
        "[GENIUSPAY] %(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(handler)

# ─── CONFIG ──────────────────────────────────────────────────
BASE_URL = os.getenv("GENIUS_BASE_URL", "https://geniuspay.ci/api/v1/merchant").rstrip("/")
# Correction automatique si le .env a juste /api/v1 sans /merchant
if BASE_URL.endswith("/api/v1"):
    BASE_URL += "/merchant"
    logger.warning(f"GENIUS_BASE_URL corrigé → {BASE_URL} (ajout /merchant manquant)")

API_KEY = os.getenv("GENIUS_API_KEY", "")
API_SECRET = os.getenv("GENIUS_API_SECRET", "")
WEBHOOK_SECRET = os.getenv("GENIUS_WEBHOOK_SECRET", "")
TIMEOUT = int(os.getenv("GENIUS_TIMEOUT", "30"))

# ─── CONSTANTES DE LA DOCUMENTATION ──────────────────────────

# Payment methods supportés (documentation)
PAYMENT_METHODS = ["wave", "pawapay", "paystack", "orange_money", "mtn_money", "card"]

# Gateways supportés (documentation)
GATEWAYS = ["wave", "pawapay", "orange_money", "mtn_momo", "moov_money"]

# Statuts (documentation)
STATUSES = ["pending", "processing", "completed", "failed", "expired"]

# Webhook events (documentation)
WEBHOOK_EVENTS = ["payment.success", "payment.failed", "cashout.completed"]


def _mask(s: str, show: int = 4) -> str:
    """Masque une chaîne sensible pour les logs."""
    if not s or len(s) <= show * 2:
        return "***"
    return f"{s[:show]}***{s[-show:]}"


def _safe_headers(headers: dict) -> dict:
    """Copie les headers en masquant les secrets."""
    safe = {}
    for k, v in headers.items():
        if k.lower() in ("x-api-secret", "x-api-key", "authorization"):
            safe[k] = _mask(str(v))
        else:
            safe[k] = v
    return safe


# ═══════════════════════════════════════════════════════════════
# CLIENT GENIUSPAY
# ═══════════════════════════════════════════════════════════════

class GeniusPay:
    """
    Client GeniusPay basé sur la documentation officielle.
    https://geniuspay.ci/docs/api
    """

    def __init__(self):
        self.base_url = BASE_URL
        self.api_key = API_KEY
        self.api_secret = API_SECRET
        self.webhook_secret = WEBHOOK_SECRET
        self._session: Optional[requests.Session] = None

        if not self.api_key or not self.api_secret:
            logger.warning("GENIUS_API_KEY ou GENIUS_API_SECRET manquant dans .env")

        logger.info(f"GeniusPay initialisé — Base: {self.base_url} | Key: {_mask(self.api_key)}")

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "User-Agent": "NectarPro/3.0 (GeniusPay Integration)",
                "Accept": "application/json",
            })
        return self._session

    def _headers(self) -> Dict[str, str]:
        return {
            "X-API-Key": self.api_key,
            "X-API-Secret": self.api_secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ── REQUÊTE GÉNÉRIQUE ────────────────────────────────────
    def _request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Tuple[bool, Dict[str, Any], float]:
        """Exécute une requête HTTP avec logs détaillés."""
        url = f"{self.base_url}{path}"
        headers = self._headers()

        # LOG: REQUÊTE
        logger.info(f"REQ → {method} {url}")
        logger.info(f"     Headers: {json.dumps(_safe_headers(headers))}")
        if json_data:
            logger.info(f"     Body: {json.dumps(json_data, ensure_ascii=False)[:2000]}")
        if params:
            logger.info(f"     Params: {json.dumps(params)}")

        start = time.time()

        try:
            resp = self.session.request(
                method=method,
                url=url,
                json=json_data,
                params=params,
                headers=headers,
                timeout=TIMEOUT,
            )
            elapsed = round(time.time() - start, 3)

            try:
                body = resp.json()
            except (json.JSONDecodeError, ValueError):
                body = {"raw": resp.text[:500]}

            # LOG: RÉPONSE
            status_icon = "✅" if 200 <= resp.status_code < 300 else "❌"
            logger.info(
                f"RES ← {status_icon} {resp.status_code} | {elapsed}s | {method} {path}"
            )
            logger.info(f"     Body: {json.dumps(body, ensure_ascii=False)[:2000]}")

            if 200 <= resp.status_code < 300:
                return True, body, elapsed
            else:
                return False, {
                    "success": False,
                    "http_status": resp.status_code,
                    "error": body.get("message", resp.text[:300]),
                    "response": body,
                }, elapsed

        except requests.ConnectionError as e:
            elapsed = round(time.time() - start, 3)
            logger.error(f"⛔ Connexion échouée: {e}")
            return False, {"success": False, "error_code": "CONNECTION_ERROR", "error": str(e)}, elapsed
        except requests.Timeout as e:
            elapsed = round(time.time() - start, 3)
            logger.error(f"⛔ Timeout après {TIMEOUT}s")
            return False, {"success": False, "error_code": "TIMEOUT", "error": str(e)}, elapsed
        except Exception as e:
            elapsed = round(time.time() - start, 3)
            logger.exception(f"⛔ Erreur inattendue: {e}")
            return False, {"success": False, "error_code": "UNEXPECTED", "error": str(e)}, elapsed

    # ═══════════════════════════════════════════════════════════
    # 1. CRÉATION D'UN PAIEMENT
    # ═══════════════════════════════════════════════════════════

    def create_payment(
        self,
        amount: float,
        currency: str = "XOF",
        payment_method: Optional[str] = None,
        gateway: Optional[str] = None,
        mmo_provider: Optional[str] = None,
        description: Optional[str] = None,
        customer: Optional[Dict[str, str]] = None,
        success_url: Optional[str] = None,
        error_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Dict[str, Any], float]:
        """
        Crée un paiement via l'API GeniusPay.

        Documentation : POST /api/v1/merchant/payments

        Args:
            amount: Montant du paiement (requis)
            currency: Code devise, défaut XOF
            payment_method: wave, pawapay, paystack, orange_money, mtn_money, card (optionnel)
                           Si omis → page checkout GeniusPay
            gateway: wave, pawapay, orange_money, mtn_momo, moov_money (optionnel)
            mmo_provider: Code fournisseur MMO dynamique (ex: ORANGE_CIV)
            description: Description du paiement
            customer: Dict avec name, email, phone, country
            success_url: URL de redirection après succès
            error_url: URL de redirection après erreur
            metadata: Données personnalisées (order_id, user_id, deposit_id, etc.)

        Returns:
            (success, data, response_time)
        """
        logger.info(f"💳 Création paiement: {amount} {currency}")

        payload = {
            "amount": amount,
            "currency": currency,
        }

        # Ajouter les champs optionnels documentés
        if payment_method:
            if payment_method not in PAYMENT_METHODS:
                logger.warning(f"payment_method '{payment_method}' non standard. Acceptés: {PAYMENT_METHODS}")
            payload["payment_method"] = payment_method
        else:
            logger.info("Aucun payment_method → ouverture page checkout GeniusPay")

        if gateway:
            payload["gateway"] = gateway

        if mmo_provider:
            payload["mmo_provider"] = mmo_provider

        if description:
            payload["description"] = description

        if customer:
            payload["customer"] = customer

        if success_url:
            payload["success_url"] = success_url

        if error_url:
            payload["error_url"] = error_url

        if metadata:
            payload["metadata"] = metadata

        return self._request("POST", "/payments", json_data=payload)

    # ═══════════════════════════════════════════════════════════
    # 2. LISTER LES PAIEMENTS
    # ═══════════════════════════════════════════════════════════

    def list_payments(
        self,
        status: Optional[str] = None,
        payment_method: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Tuple[bool, Dict[str, Any], float]:
        """
        Liste les paiements.

        Documentation : GET /api/v1/merchant/payments

        Args:
            status: pending, completed, failed
            payment_method: wave, pawapay, etc.
            from_date: YYYY-MM-DD
            to_date: YYYY-MM-DD
            page: Numéro de page
            per_page: Résultats par page
        """
        params = {"page": page, "per_page": per_page}
        if status:
            params["status"] = status
        if payment_method:
            params["payment_method"] = payment_method
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        return self._request("GET", "/payments", params=params)

    # ═══════════════════════════════════════════════════════════
    # 3. RÉCUPÉRER UN PAIEMENT PAR RÉFÉRENCE
    # ═══════════════════════════════════════════════════════════

    def get_payment(self, reference: str) -> Tuple[bool, Dict[str, Any], float]:
        """
        Récupère un paiement par sa référence.

        Documentation : GET /api/v1/merchant/payments/{reference}

        La référence est retournée lors de la création du paiement (MTX-...).

        Args:
            reference: Référence de la transaction (ex: MTX-A1B2C3D4E5)

        Returns:
            (success, data, response_time)
        """
        logger.info(f"🔍 Récupération paiement: {reference}")
        return self._request("GET", f"/payments/{reference}")

    # ═══════════════════════════════════════════════════════════
    # 4. FOURNISSEURS MMO (DYNAMIQUE)
    # ═══════════════════════════════════════════════════════════

    def get_providers(self, country: Optional[str] = None) -> Tuple[bool, Dict[str, Any], float]:
        """
        Récupère la liste des fournisseurs MMO disponibles.

        Documentation : GET /api/v1/merchant/pawapay/providers?country=XX

        Args:
            country: Code pays ISO2 (CI, SN, CD...) ou None pour tous

        Returns:
            (success, data, response_time)
        """
        params = {}
        if country:
            params["country"] = country.upper()

        logger.info(f"📡 Récupération providers{' pour ' + country if country else ' (tous pays)'}")
        return self._request("GET", "/pawapay/providers", params=params)

    # ═══════════════════════════════════════════════════════════
    # 5. WEBHOOKS
    # ═══════════════════════════════════════════════════════════

    def verify_webhook_signature(
        self,
        raw_body: bytes,
        signature_header: str,
    ) -> bool:
        """
        Vérifie la signature d'un webhook GeniusPay.

        Documentation : https://geniuspay.ci/docs/api#webhook-security

        La signature est envoyée dans le header X-Genius-Signature.
        GeniusPay utilise HMAC-SHA256 avec le secret webhook.

        Args:
            raw_body: Corps brut de la requête (bytes)
            signature_header: Valeur du header X-Genius-Signature

        Returns:
            True si la signature est valide
        """
        if not self.webhook_secret:
            logger.warning("WEBHOOK_SECRET non configuré — vérification impossible")
            return False

        if not signature_header:
            logger.warning("Header X-Genius-Signature manquant")
            return False

        try:
            # HMAC-SHA256: hexdigest
            computed = hmac.new(
                key=self.webhook_secret.encode("utf-8"),
                msg=raw_body,
                digestmod=hashlib.sha256,
            ).hexdigest()

            # Comparaison sécurisée (timing-attack safe)
            valid = hmac.compare_digest(computed, signature_header)

            if valid:
                logger.info("🔐 Signature webhook vérifiée ✓")
            else:
                logger.warning(f"🔐 Signature webhook invalide! Attendu: {computed[:12]}..., Reçu: {signature_header[:12]}...")

            return valid

        except Exception as e:
            logger.error(f"⛔ Erreur vérification signature: {e}")
            return False

    def process_webhook(
        self,
        raw_body: bytes,
        signature_header: str,
    ) -> Tuple[bool, Dict[str, Any], str]:
        """
        Traite un webhook entrant de GeniusPay.

        Documentation : https://geniuspay.ci/docs/api#webhooks

        Args:
            raw_body: Corps brut de la requête (bytes)
            signature_header: Valeur du header X-Genius-Signature

        Returns:
            (success, data, message)
        """
        try:
            # 1. Vérifier la signature
            if not self.verify_webhook_signature(raw_body, signature_header):
                return False, {}, "Signature webhook invalide"

            # 2. Parser le JSON
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error(f"⛔ Webhook JSON invalide: {e}")
                return False, {}, f"JSON invalide: {e}"

            logger.info(f"📨 Webhook reçu: event={payload.get('event')}, ref={payload.get('reference')}")

            # 3. Extraire les données utiles
            data = {
                "transaction_id": payload.get("transaction_id") or payload.get("reference", ""),
                "reference": payload.get("reference", ""),
                "event": payload.get("event", ""),
                "status": payload.get("status", ""),
                "amount": payload.get("amount", 0),
                "currency": payload.get("currency", "XOF"),
                "fees": payload.get("fees", 0),
                "net_amount": payload.get("net_amount", 0),
                "gateway": payload.get("gateway", ""),
                "payment_method": payload.get("payment_method", ""),
                "metadata": payload.get("metadata", {}),
                "customer": payload.get("customer", {}),
                "raw": payload,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }

            return True, data, "Webhook traité avec succès"

        except Exception as e:
            logger.exception(f"⛔ Erreur traitement webhook: {e}")
            return False, {}, f"Erreur interne: {e}"

    # ═══════════════════════════════════════════════════════════
    # 6. GESTION DES WEBHOOKS (CRUD via API)
    # ═══════════════════════════════════════════════════════════

    def create_webhook(
        self,
        url: str,
        events: List[str],
        name: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any], float]:
        """
        Crée un webhook GeniusPay.

        Documentation : POST /api/v1/merchant/webhooks

        Args:
            url: URL de réception des webhooks
            events: Liste d'événements (payment.success, payment.failed, cashout.completed)
            name: Nom du webhook (optionnel)
        """
        payload = {
            "url": url,
            "events": events,
        }
        if name:
            payload["name"] = name

        logger.info(f"🔗 Création webhook: {url}")
        return self._request("POST", "/webhooks", json_data=payload)

    def list_webhooks(self) -> Tuple[bool, Dict[str, Any], float]:
        """Liste les webhooks configurés."""
        return self._request("GET", "/webhooks")

    def get_webhook(self, webhook_id: str) -> Tuple[bool, Dict[str, Any], float]:
        """Récupère un webhook par ID."""
        return self._request("GET", f"/webhooks/{webhook_id}")

    def delete_webhook(self, webhook_id: str) -> Tuple[bool, Dict[str, Any], float]:
        """Supprime un webhook."""
        return self._request("DELETE", f"/webhooks/{webhook_id}")

    def test_webhook(self, webhook_id: str) -> Tuple[bool, Dict[str, Any], float]:
        """Envoie un test de webhook."""
        return self._request("POST", f"/webhooks/{webhook_id}/test")


# ═══════════════════════════════════════════════════════════════
# INSTANCE GLOBALE
# ═══════════════════════════════════════════════════════════════

genius = GeniusPay()

logger.info(f"GeniusPay v3.0 prêt — {genius.base_url}")