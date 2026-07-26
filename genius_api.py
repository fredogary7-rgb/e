"""
╔══════════════════════════════════════════════════════════════╗
║           GENIUSPAY API - Module Officiel                   ║
║           Documentation : geniuspay.ci/docs/api             ║
║           Base URL : https://geniuspay.ci/api/v1/merchant   ║
╚══════════════════════════════════════════════════════════════╝

Endpoints documentés (source : https://geniuspay.ci/docs/api) :
  POST   /api/v1/merchant/payments           → Créer un paiement
  GET    /api/v1/merchant/payments/{ref}      → Récupérer un paiement
  GET    /api/v1/merchant/pawapay/providers   → Lister fournisseurs MMO

Authentification : headers X-API-Key + X-API-Secret

Auteur : NectarPro Team
Version : 2.0.0 — Basé sur la documentation officielle
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple

import requests

# ─── LOGGER ──────────────────────────────────────────────────
logger = logging.getLogger("geniuspay")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter(
    "[GENIUS] %(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))
logger.addHandler(handler)

# ─── CONFIG ──────────────────────────────────────────────────
BASE_URL = os.getenv("GENIUS_BASE_URL", "https://geniuspay.ci/api/v1/merchant").rstrip("/")
# Si le .env a juste /api/v1 (sans /merchant), on corrige automatiquement
if BASE_URL.endswith("/api/v1"):
    BASE_URL += "/merchant"
    logger.warning(f"⚠️  GENIUS_BASE_URL corrigé → {BASE_URL} (ajout /merchant manquant)")
API_KEY = os.getenv("GENIUS_API_KEY", "")
API_SECRET = os.getenv("GENIUS_API_SECRET", "")
TIMEOUT = int(os.getenv("GENIUS_TIMEOUT", "30"))


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

class GeniusAPI:
    """
    Client GeniusPay basé sur la documentation officielle.
    https://geniuspay.ci/docs/api
    """

    def __init__(self):
        self.base_url = BASE_URL.rstrip("/")
        self.api_key = API_KEY
        self.api_secret = API_SECRET
        self._session: Optional[requests.Session] = None

        if not self.api_key or not self.api_secret:
            logger.warning("⚠️  GENIUS_API_KEY ou GENIUS_API_SECRET manquant dans .env")

        logger.info(f"GeniusAPI initialisé — Base: {self.base_url} | Key: {_mask(self.api_key)}")

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
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

        # ═══ LOG: REQUÊTE ═══
        logger.info(f"REQ → {method} {url}")
        logger.info(f"     Headers: {json.dumps(_safe_headers(headers))}")
        if json_data:
            logger.info(f"     Body: {json.dumps(json_data, ensure_ascii=False)}")
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

            # ═══ LOG: RÉPONSE ═══
            logger.info(
                f"RES ← {resp.status_code} | {elapsed}s | {method} {path}"
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
    # ENDPOINTS DOCUMENTÉS
    # ═══════════════════════════════════════════════════════════

    def create_payment(
        self,
        amount: float,
        customer: Optional[Dict[str, str]] = None,
        payment_method: Optional[str] = None,
        currency: Optional[str] = None,
        country: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        callback_url: Optional[str] = None,
        return_url: Optional[str] = None,
        mmo_provider: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any], float]:
        """
        Crée un paiement via l'API GeniusPay.

        Documentation : POST /api/v1/merchant/payments

        Args:
            amount: Montant du paiement (requis)
            customer: Dict avec 'name', 'email', 'phone'
            payment_method: wave, pawapay, paystack, orange_money, mtn_money (optionnel)
            currency: Code devise (XOF par défaut)
            country: Code pays ISO2 (CI, SN, CD...)
            description: Description du paiement
            metadata: Données personnalisées (retournées telles quelles)
            callback_url: URL de callback webhook
            return_url: URL de retour après paiement
            mmo_provider: Code opérateur MMO spécifique (ex: ORANGE_SEN)

        Returns:
            (success, data, response_time)
        """
        payload = {"amount": amount}

        if currency:
            payload["currency"] = currency
        if payment_method:
            payload["payment_method"] = payment_method
        if country:
            payload["country"] = country
        if description:
            payload["description"] = description
        if customer:
            payload["customer"] = customer
        if metadata:
            payload["metadata"] = metadata
        if callback_url:
            payload["callback_url"] = callback_url
        if return_url:
            payload["return_url"] = return_url
        if mmo_provider:
            payload["mmo_provider"] = mmo_provider

        logger.info(f"💳 Création paiement: {amount} {currency or 'XOF'}")
        success, data, response_time = self._request("POST", "/payments", json_data=payload)
        return success, data, response_time

    def get_payment(self, reference: str) -> Tuple[bool, Dict[str, Any], float]:
        """
        Récupère un paiement par sa référence.

        Documentation : GET /api/v1/merchant/payments/{reference}

        Args:
            reference: La référence de la transaction (ex: MTX-A1B2C3D4E5)

        Returns:
            (success, data, response_time)
        """
        logger.info(f"🔍 Récupération paiement: {reference}")
        success, data, response_time = self._request("GET", f"/payments/{reference}")
        return success, data, response_time

    def get_providers(self, country: Optional[str] = None) -> Tuple[bool, Dict[str, Any], float]:
        """
        Liste les fournisseurs MMO disponibles.

        Documentation : GET /api/v1/merchant/pawapay/providers?country=XX

        Args:
            country: Code pays ISO2 (ex: CI, SN). Si None, retourne tous les pays.

        Returns:
            (success, data, response_time)
        """
        params = {}
        if country:
            params["country"] = country.upper()
            logger.info(f"📡 Fournisseurs MMO pour {country.upper()}")
        else:
            logger.info("📡 Tous les fournisseurs MMO")

        success, data, response_time = self._request("GET", "/pawapay/providers", params=params)
        return success, data, response_time


# ═══════════════════════════════════════════════════════════════
# INSTANCE GLOBALE
# ═══════════════════════════════════════════════════════════════

genius = GeniusAPI()


# ═══════════════════════════════════════════════════════════════
# FONCTIONS DE COMPATIBILITÉ
# ═══════════════════════════════════════════════════════════════

def genius_create_payment(**kwargs) -> Dict[str, Any]:
    success, data, rt = genius.create_payment(**kwargs)
    return {"success": success, "data": data, "response_time": rt}


def genius_get_payment(reference: str) -> Dict[str, Any]:
    success, data, rt = genius.get_payment(reference)
    return {"success": success, "data": data, "response_time": rt}


def genius_get_providers(country: str = None) -> Dict[str, Any]:
    success, data, rt = genius.get_providers(country)
    return {"success": success, "data": data, "response_time": rt}