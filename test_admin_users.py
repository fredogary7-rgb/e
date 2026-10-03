import os
import time
import hmac
import hashlib
import json
import requests

from dotenv import load_dotenv

load_dotenv()

WEBHOOK_SECRET = os.getenv("DRIMPAY_WEBHOOK_SECRET", "")

URL = "http://127.0.0.1:10000/drimpay/webhook"

if not WEBHOOK_SECRET:
    print("❌ DRIMPAY_WEBHOOK_SECRET absent.")
    raise SystemExit(1)

# ============================================================
# FAUX WEBHOOK DRIMPAY
# ============================================================

payload = {
    "event": "payin.success",
    "reference": "TEST-DRIMPAY-LOCAL-001",
    "order_id": "E-43391",
    "status": "success",
    "amount": 4800,
    "fee": 216,
    "net_amount": 4584,
    "currency": "XOF",
    "country_code": "TG",
    "operator": "tmoney",
    "phone": "90688116",
    "mode": "test",
    "failure_reason": None,
    "metadata": {},
    "created_at": "2026-10-03T21:00:00.000Z",
    "updated_at": "2026-10-03T21:00:00.000Z"
}

# ============================================================
# JSON EXACTEMENT UTILISÉ POUR LA SIGNATURE
# ============================================================

raw_body = json.dumps(
    payload,
    separators=(",", ":"),
    ensure_ascii=False
)

# ============================================================
# TIMESTAMP
# ============================================================

timestamp = str(int(time.time()))

# ============================================================
# SIGNATURE DRIMPAY
#
# HMAC_SHA256(
#     SECRET,
#     timestamp + "." + raw_body
# )
# ============================================================

signed_payload = f"{timestamp}.{raw_body}"

signature = hmac.new(
    WEBHOOK_SECRET.encode("utf-8"),
    signed_payload.encode("utf-8"),
    hashlib.sha256
).hexdigest()

signature_header = f"t={timestamp},v1={signature}"

# ============================================================
# HEADERS
# ============================================================

headers = {
    "Content-Type": "application/json",
    "X-DrimPay-Signature": signature_header,
    "X-DrimPay-Timestamp": timestamp,
    "X-DrimPay-Event": "payin.success",
}

# ============================================================
# AFFICHAGE
# ============================================================

print("=" * 70)
print("       TEST WEBHOOK DRIMPAY — SANS ARGENT")
print("=" * 70)

print()
print("URL :", URL)
print("Order ID :", payload["order_id"])
print("Amount :", payload["amount"], payload["currency"])
print("Event :", payload["event"])
print("Status :", payload["status"])
print()

print("Signature générée :")
print(signature_header)

print()
print("Envoi du faux webhook...")
print()

# ============================================================
# ENVOI
# ============================================================

try:
    response = requests.post(
        URL,
        headers=headers,
        data=raw_body.encode("utf-8"),
        timeout=15
    )

except requests.exceptions.ConnectionError:
    print("❌ Impossible de contacter Flask.")
    print()
    print("Vérifie que ton application fonctionne sur :")
    print("http://127.0.0.1:10000")
    raise SystemExit(1)

except requests.exceptions.Timeout:
    print("❌ Timeout.")
    raise SystemExit(1)

except requests.RequestException as e:
    print("❌ Erreur réseau :", e)
    raise SystemExit(1)

# ============================================================
# RESULTAT
# ============================================================

print("=" * 70)
print("RESULTAT")
print("=" * 70)

print()
print("HTTP STATUS :", response.status_code)

print()
print("REPONSE SERVEUR :")

try:
    print(
        json.dumps(
            response.json(),
            indent=4,
            ensure_ascii=False
        )
    )
except ValueError:
    print(response.text)

print()

if response.status_code == 200:

    print("✅ WEBHOOK ACCEPTÉ")
    print()
    print("La signature HMAC est correcte.")
    print("Ton endpoint accepte le webhook simulé.")

elif response.status_code == 403:

    print("❌ WEBHOOK REFUSÉ : HTTP 403")
    print()
    print("La vérification HMAC échoue.")
    print("Regarde les logs Flask.")

elif response.status_code == 404:

    print("❌ HTTP 404")
    print()
    print("La route /drimpay/webhook n'est pas accessible.")

elif response.status_code == 400:

    print("⚠️ HTTP 400")
    print()
    print("La signature semble probablement avoir été acceptée,")
    print("mais une validation du contenu du webhook a échoué.")

else:

    print(
        f"⚠️ Réponse inattendue : HTTP {response.status_code}"
    )

print()
print("=" * 70)
print("FIN DU TEST")
print("=" * 70)