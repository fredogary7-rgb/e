"""
DrimPay Pay-in v2 client.

Endpoint: POST /v2/payin/initiate
Statut:   GET /v2/payin/{reference}
Webhook:  HMAC-SHA256 (X-DrimPay-Signature: t={ts},v1={hex})
"""
import os
from dotenv import load_dotenv

# Charger le fichier .env
load_dotenv()

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

def verify_webhook_signature(
    raw_body,
    signature_header,
    timestamp_header=None,
    tolerance=300
):
    """
    Vérifie la signature HMAC-SHA256 des webhooks DrimPay.

    Signature DrimPay :

        HMAC_SHA256(
            DRIMPAY_WEBHOOK_SECRET,
            timestamp + "." + raw_body
        )

    Header :
        X-DrimPay-Signature: t=TIMESTAMP,v1=SIGNATURE

    Header complémentaire :
        X-DrimPay-Timestamp
    """

    # =========================================================
    # 1. SECRET
    # =========================================================

    if not WEBHOOK_SECRET:
        logger.error(
            "[DRIMPAY] DRIMPAY_WEBHOOK_SECRET absent."
        )
        return False

    # =========================================================
    # 2. SIGNATURE
    # =========================================================

    if not signature_header:
        logger.error(
            "[DRIMPAY] Header X-DrimPay-Signature absent."
        )
        return False

    # =========================================================
    # 3. RAW BODY
    # =========================================================

    if raw_body is None:
        logger.error(
            "[DRIMPAY] raw_body absent."
        )
        return False

    if isinstance(raw_body, bytes):
        raw_body = raw_body.decode("utf-8")

    # =========================================================
    # 4. PARSING SIGNATURE
    # =========================================================

    timestamp = None
    signature = None

    for part in signature_header.split(","):

        part = part.strip()

        if "=" not in part:
            continue

        key, value = part.split("=", 1)

        key = key.strip()
        value = value.strip()

        if key == "t":
            timestamp = value

        elif key == "v1":
            signature = value

    # =========================================================
    # 5. TIMESTAMP DE SECOURS
    # =========================================================

    if not timestamp and timestamp_header:
        timestamp = str(timestamp_header).strip()

    if not timestamp:
        logger.error(
            "[DRIMPAY] Timestamp absent."
        )
        return False

    if not signature:
        logger.error(
            "[DRIMPAY] Signature v1 absente."
        )
        return False

    # =========================================================
    # 6. VALIDATION TIMESTAMP
    # =========================================================

    try:
        timestamp_int = int(timestamp)

    except (TypeError, ValueError):

        logger.error(
            "[DRIMPAY] Timestamp invalide : %s",
            timestamp
        )

        return False

    # =========================================================
    # 7. PROTECTION ANTI-REJEU
    # =========================================================

    current_time = int(time.time())

    difference = abs(
        current_time - timestamp_int
    )

    if difference > tolerance:

        logger.warning(
            "[DRIMPAY] Timestamp hors tolérance : "
            "difference=%ss tolerance=%ss",
            difference,
            tolerance
        )

        return False

    # =========================================================
    # 8. PAYLOAD SIGNÉ
    # =========================================================

    signed_payload = (
        f"{timestamp}.{raw_body}"
    )

    # =========================================================
    # 9. CALCUL HMAC
    # =========================================================

    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    # =========================================================
    # 10. COMPARAISON SÉCURISÉE
    # =========================================================

    valid = hmac.compare_digest(
        expected_signature.lower(),
        signature.lower()
    )

    if valid:

        logger.info(
            "[DRIMPAY] Signature HMAC valide | "
            "timestamp=%s body_length=%s",
            timestamp,
            len(raw_body)
        )

    else:

        logger.error(
            "[DRIMPAY] Signature HMAC invalide | "
            "timestamp=%s body_length=%s signature_length=%s",
            timestamp,
            len(raw_body),
            len(signature)
        )

    return valid