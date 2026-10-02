"""
DrimPay Pay-in v2 client.

Endpoint: POST /v2/payin/initiate
Statut:   GET /v2/payin/{reference}
Webhook:  HMAC-SHA256 (X-DrimPay-Signature: t={ts},v1={hex})
"""

import os
import hmac
import hashlib
import time
import logging

import requests

logger = logging.getLogger(__name__)

# ── Configuration (via .env) ──
SECRET_KEY = os.getenv("DRIMPAY_SECRET_KEY", "")
WEBHOOK_SECRET = os.getenv("DRIMPAY_WEBHOOK_SECRET", "")
BASE_URL = os.getenv("DRIMPAY_BASE_URL", "https://drimpay.com/api/v2")

# ── Opérateurs supportés par pays (d'après la doc DrimPay) ──
OPERATORS_BY_COUNTRY = {
    "TG": [{"slug": "tmoney", "label": "TMoney"}, {"slug": "moov", "label": "Moov Money"}],
    "BJ": [{"slug": "mtn", "label": "MTN MoMo"}, {"slug": "moov", "label": "Moov Money"}],
    "CM": [{"slug": "mtn", "label": "MTN MoMo"}, {"slug": "orange", "label": "Orange Money"}],
    "BF": [{"slug": "orange", "label": "Orange Money"}, {"slug": "moov", "label": "Moov Money"}],
    "ML": [{"slug": "orange", "label": "Orange Money"}, {"slug": "moov", "label": "Moov Money"}],
    "SN": [{"slug": "wave", "label": "Wave"}, {"slug": "orange", "label": "Orange Money"}, {"slug": "wizall", "label": "Wizall"}],
    "CI": [{"slug": "mtn", "label": "MTN MoMo"}, {"slug": "orange", "label": "Orange Money"}, {"slug": "wave", "label": "Wave"}],
    "NG": [{"slug": "airtel", "label": "Airtel"}, {"slug": "vodacom", "label": "Vodacom"}],
    "CD": [{"slug": "airtel", "label": "Airtel"}, {"slug": "vodacom", "label": "Vodacom"}],
}

# ── Pays nécessitant un OTP Orange ──
OTP_COUNTRIES = {"CI", "SN", "BF", "ML"}


def _headers():
    return {
        "Authorization": f"Bearer {SECRET_KEY}",
        "Content-Type": "application/json",
    }


def initiate_payin(amount, currency, country_code, operator, phone, order_id,
                   webhook_url=None, description=None, expires_in_minutes=5,
                   operator_otp=None, metadata=None):
    """Crée une demande de collecte Mobile Money via DrimPay.

    Retourne (success: bool, data: dict). data contient la réponse JSON ou l'erreur.
    """
    if not SECRET_KEY:
        return False, {"error": "NO_API_KEY", "message": "DRIMPAY_SECRET_KEY non configuré."}

    payload = {
        "amount": int(amount),
        "currency": currency,
        "country_code": country_code,
        "operator": operator,
        "phone": phone,
        "order_id": order_id,
        "expires_in_minutes": int(expires_in_minutes),
    }
    if webhook_url:
        payload["webhook_url"] = webhook_url
    if description:
        payload["description"] = description[:255]
    if operator_otp:
        payload["operator_otp"] = str(operator_otp)
    if metadata:
        payload["metadata"] = metadata

    try:
        r = requests.post(
            f"{BASE_URL}/payin/initiate",
            headers=_headers(),
            json=payload,
            timeout=30,
        )
    except requests.exceptions.ReadTimeout:
        return False, {"error": "TIMEOUT", "message": "DrimPay ne répond pas (délai dépassé). Réessayez plus tard."}
    except requests.exceptions.ConnectTimeout:
        return False, {"error": "TIMEOUT", "message": "Connexion à DrimPay impossible (délai dépassé)."}
    except requests.RequestException as e:
        logger.error("[DRIMPAY] initiate réseau: %s", e)
        return False, {"error": "NETWORK_ERROR", "message": "Erreur de connexion au service de paiement."}

    try:
        data = r.json()
    except ValueError:
        return False, {"error": "BAD_RESPONSE", "message": r.text[:300], "status_code": r.status_code}

    if r.status_code not in (200, 201):
        return False, data

    return True, data


def get_payin_status(reference):
    """Récupère le statut d'une transaction."""
    if not SECRET_KEY:
        return False, {"error": "NO_API_KEY", "message": "DRIMPAY_SECRET_KEY non configuré."}

    try:
        r = requests.get(
            f"{BASE_URL}/payin/{reference}",
            headers=_headers(),
            timeout=30,
        )
    except requests.exceptions.ReadTimeout:
        return False, {"error": "TIMEOUT", "message": "DrimPay ne répond pas (délai dépassé)."}
    except requests.RequestException as e:
        return False, {"error": "NETWORK_ERROR", "message": "Erreur de connexion au service de paiement."}

    try:
        data = r.json()
    except ValueError:
        return False, {"error": "BAD_RESPONSE", "message": r.text[:300], "status_code": r.status_code}

    if r.status_code != 200:
        return False, data

    return True, data


def verify_webhook_signature(raw_body, signature_header, tolerance=300):
    """Vérifie la signature HMAC-SHA256 d'un webhook DrimPay.

    signature_header: "t={timestamp},v1={hex_signature}"
    raw_body: corps brut de la requête (str/bytes)
    """
    if not WEBHOOK_SECRET:
        logger.warning("[DRIMPAY] Webhook secret non configuré.")
        return False

    if not signature_header:
        return False

    parts = {}
    for part in signature_header.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            parts[k.strip()] = v.strip()

    timestamp = parts.get("t")
    signature = parts.get("v1")
    if not timestamp or not signature:
        return False

    # Protection contre le rejeu (5 minutes)
    try:
        ts = int(timestamp)
        if abs(time.time() - ts) > tolerance:
            logger.warning("[DRIMPAY] Webhook timestamp hors tolérance.")
            return False
    except ValueError:
        return False

    if isinstance(raw_body, bytes):
        raw_body = raw_body.decode("utf-8")

    expected = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        f"{timestamp}.{raw_body}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)
