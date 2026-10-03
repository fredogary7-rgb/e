"""
Vérification de transactions DrimPay Pay-in.

Transactions testées :
- TG-A06376D6F3AC85D7
- TG-26AFC8D9DBB960A2

IMPORTANT :
Ce script ne crée aucun paiement.
Il fait uniquement des GET /payin/{reference}.
"""

import os
import json
import requests
from dotenv import load_dotenv

# ============================================================
# CHARGEMENT .ENV
# ============================================================

load_dotenv()

API_KEY = os.getenv("DRIMPAY_SECRET_KEY", "")
BASE_URL = os.getenv(
    "DRIMPAY_BASE_URL",
    "https://drimpay.com/api/v2"
).rstrip("/")


# ============================================================
# TRANSACTIONS À VÉRIFIER
# ============================================================

REFERENCES = [
    "TG-A06376D6F3AC85D7",
    "TG-26AFC8D9DBB960A2",
]


# ============================================================
# VÉRIFICATION CONFIGURATION
# ============================================================

print("=" * 70)
print("       VERIFICATION TRANSACTIONS DRIMPAY")
print("=" * 70)

print()
print("BASE URL :", BASE_URL)

if not API_KEY:
    print("❌ DRIMPAY_SECRET_KEY absente.")
    print()
    print("Vérifie ton fichier .env.")
    raise SystemExit(1)

print("✅ DRIMPAY_SECRET_KEY chargée.")
print()


# ============================================================
# HEADERS
# ============================================================

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


# ============================================================
# FONCTION DE VÉRIFICATION
# ============================================================

def check_transaction(reference):

    print()
    print("=" * 70)
    print(f"TRANSACTION : {reference}")
    print("=" * 70)

    url = f"{BASE_URL}/payin/{reference}"

    print()
    print("GET :", url)

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30,
        )

    except requests.exceptions.Timeout:
        print("❌ Timeout DrimPay.")
        return

    except requests.RequestException as e:
        print("❌ Erreur réseau :", e)
        return

    print()
    print("HTTP STATUS :", response.status_code)

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    try:
        data = response.json()

    except ValueError:
        print()
        print("❌ Réponse non JSON :")
        print(response.text[:2000])
        return

    print()
    print("REPONSE COMPLETE :")
    print(json.dumps(
        data,
        indent=4,
        ensure_ascii=False
    ))

    # --------------------------------------------------------
    # ERREUR
    # --------------------------------------------------------

    if response.status_code != 200:

        print()
        print("❌ DrimPay a retourné une erreur.")

        if isinstance(data, dict):
            print(
                "Erreur :",
                data.get("error")
            )

            print(
                "Message :",
                data.get("message")
            )

        return

    # --------------------------------------------------------
    # EXTRACTION
    # --------------------------------------------------------

    status = data.get("status")
    order_id = data.get("order_id")
    amount = data.get("amount")
    fee = data.get("fee")
    net_amount = data.get("net_amount")
    currency = data.get("currency")
    country = data.get("country_code")
    operator = data.get("operator")
    phone = data.get("phone")
    mode = data.get("mode")

    webhook_status = data.get(
        "webhook_status_code"
    )

    webhook_retry_count = data.get(
        "webhook_retry_count"
    )

    failure_reason = data.get(
        "failure_reason"
    )

    created_at = data.get(
        "created_at"
    )

    updated_at = data.get(
        "updated_at"
    )

    expires_at = data.get(
        "expires_at"
    )

    # --------------------------------------------------------
    # AFFICHAGE
    # --------------------------------------------------------

    print()
    print("-" * 70)
    print("RESUME")
    print("-" * 70)

    print("Reference           :", reference)
    print("Order ID            :", order_id)
    print("Status              :", status)
    print("Amount              :", amount, currency)
    print("Fee                 :", fee, currency)
    print("Net Amount          :", net_amount, currency)
    print("Country             :", country)
    print("Operator            :", operator)
    print("Phone               :", phone)
    print("Mode                :", mode)

    print()
    print("Webhook HTTP        :", webhook_status)
    print("Webhook retries     :", webhook_retry_count)

    print()
    print("Failure reason      :", failure_reason)

    print()
    print("Created at          :", created_at)
    print("Updated at          :", updated_at)
    print("Expires at          :", expires_at)

    # --------------------------------------------------------
    # INTERPRETATION
    # --------------------------------------------------------

    print()
    print("-" * 70)
    print("INTERPRETATION")
    print("-" * 70)

    if status == "success":
        print("✅ PAIEMENT RÉUSSI")

    elif status == "pending":
        print("⏳ PAIEMENT EN ATTENTE")
        print("   Le client doit encore confirmer le paiement.")

    elif status == "processing":
        print("🔄 PAIEMENT EN COURS DE TRAITEMENT")

    elif status == "queued":
        print("⏳ PAIEMENT EN FILE D'ATTENTE")

    elif status == "failed":
        print("❌ PAIEMENT ÉCHOUÉ")

    elif status == "expired":
        print("⌛ PAIEMENT EXPIRÉ")

    elif status == "cancelled":
        print("❌ PAIEMENT ANNULÉ")

    elif status == "reversed":
        print("↩️ PAIEMENT INVERSÉ / REMBOURSÉ")

    else:
        print("⚠️ STATUT INCONNU :", status)

    # --------------------------------------------------------
    # WEBHOOK
    # --------------------------------------------------------

    print()

    if webhook_status == 200:
        print("✅ DrimPay indique que le webhook a reçu HTTP 200.")

    elif webhook_status:
        print(
            f"❌ DrimPay indique que le webhook a reçu HTTP {webhook_status}."
        )

        if webhook_retry_count:
            print(
                f"⚠️ Nombre de tentatives webhook : {webhook_retry_count}"
            )

    else:
        print("ℹ️ Aucun code HTTP webhook disponible.")


# ============================================================
# TEST DES DEUX TRANSACTIONS
# ============================================================

for reference in REFERENCES:
    check_transaction(reference)


# ============================================================
# FIN
# ============================================================

print()
print("=" * 70)
print("FIN DE LA VERIFICATION")
print("=" * 70)
print()
print("Aucun paiement n'a été créé.")
print("Aucune transaction n'a été modifiée.")
print("=" * 70)