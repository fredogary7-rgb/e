"""
TEST COMPLET DRIMPAY - NECTARPRO

Ce script vérifie :
- chargement du .env
- clé API DrimPay
- secret webhook
- opérateurs disponibles
- signature HMAC
- application Flask
- modèles User / Depot
- route webhook
- PostgreSQL
- connexion à DrimPay
- endpoint de statut
- route dashboard_bloque

IMPORTANT :
Ce script NE crée aucun paiement réel.
"""

import os
import sys
import time
import hmac
import hashlib
import requests

# ================================================================
# 0. CHARGEMENT DU .ENV
# ================================================================

try:
    from dotenv import load_dotenv

    load_dotenv()

except ImportError:
    print("❌ python-dotenv n'est pas installé.")
    print("Installe-le avec : pip install python-dotenv")
    sys.exit(1)


# Lire les variables APRÈS load_dotenv()
DRIMPAY_SECRET_KEY = os.getenv("DRIMPAY_SECRET_KEY", "")
DRIMPAY_WEBHOOK_SECRET = os.getenv("DRIMPAY_WEBHOOK_SECRET", "")
DRIMPAY_BASE_URL = os.getenv(
    "DRIMPAY_BASE_URL",
    "https://drimpay.com/api/v2"
)


def titre(numero, texte):
    print()
    print("=" * 65)
    print(f" {numero}. {texte}")
    print("=" * 65)


# ================================================================
# 1. VARIABLES DRIMPAY
# ================================================================

titre(1, "VARIABLES DRIMPAY")

print("BASE URL :", DRIMPAY_BASE_URL)

if DRIMPAY_SECRET_KEY:
    print("✅ DRIMPAY_SECRET_KEY est configurée.")
else:
    print("❌ DRIMPAY_SECRET_KEY n'est PAS configurée.")

if DRIMPAY_WEBHOOK_SECRET:
    print("✅ DRIMPAY_WEBHOOK_SECRET est configurée.")
else:
    print("❌ DRIMPAY_WEBHOOK_SECRET n'est PAS configurée.")


# ================================================================
# 2. IMPORT DU CLIENT DRIMPAY
# ================================================================

titre(2, "IMPORT DU CLIENT DRIMPAY")

try:
    import drimpay

    print("✅ Module DrimPay importé correctement.")

except Exception as e:
    print("❌ Impossible d'importer drimpay.py")
    print("ERREUR :", e)
    sys.exit(1)


# ================================================================
# 3. OPERATEURS DRIMPAY
# ================================================================

titre(3, "OPERATEURS DRIMPAY")

try:
    operators = drimpay.OPERATORS_BY_COUNTRY

    for country, ops in operators.items():
        print()
        print(f"{country} :")

        for op in ops:
            print(
                f"   - {op['label']} "
                f"(slug={op['slug']})"
            )

except Exception as e:
    print("❌ Erreur récupération opérateurs :", e)


# ================================================================
# 4. TEST OPERATEURS TOGO
# ================================================================

titre(4, "TEST OPERATEURS TOGO")

try:
    tg_operators = drimpay.OPERATORS_BY_COUNTRY.get("TG", [])

    if tg_operators:
        print(
            f"✅ {len(tg_operators)} opérateur(s) trouvé(s) pour TG."
        )

        for op in tg_operators:
            print(
                f"   {op['label']} -> {op['slug']}"
            )

    else:
        print("❌ Aucun opérateur trouvé pour TG.")

except Exception as e:
    print("❌ Erreur :", e)


# ================================================================
# 5. TEST SIGNATURE WEBHOOK
# ================================================================

titre(5, "TEST SIGNATURE WEBHOOK")

if not DRIMPAY_WEBHOOK_SECRET:
    print("❌ Impossible de tester HMAC : secret webhook absent.")

else:
    try:
        timestamp = str(int(time.time()))
        raw_body = '{"event":"payin.success","reference":"TEST"}'

        # Signature attendue par DrimPay :
        # HMAC_SHA256(secret, timestamp + "." + raw_body)

        signed_payload = f"{timestamp}.{raw_body}"

        expected_signature = hmac.new(
            DRIMPAY_WEBHOOK_SECRET.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        signature_header = (
            f"t={timestamp},v1={expected_signature}"
        )

        valid = drimpay.verify_webhook_signature(
            raw_body,
            signature_header
        )

        if valid:
            print("✅ Signature HMAC validée.")
        else:
            print("❌ La signature HMAC n'a pas été validée.")

    except Exception as e:
        print("❌ Erreur test HMAC :", e)


# ================================================================
# 6. TEST REJET MAUVAISE SIGNATURE
# ================================================================

titre(6, "TEST REJET D'UNE MAUVAISE SIGNATURE")

if not DRIMPAY_WEBHOOK_SECRET:
    print("⚠️ Secret webhook absent, test impossible.")

else:
    try:
        timestamp = str(int(time.time()))
        raw_body = '{"event":"payin.success","reference":"TEST"}'

        bad_signature = (
            f"t={timestamp},v1=SIGNATURE_FAUSSE_123456"
        )

        valid = drimpay.verify_webhook_signature(
            raw_body,
            bad_signature
        )

        if not valid:
            print(
                "✅ Une mauvaise signature est correctement rejetée."
            )
        else:
            print(
                "❌ PROBLÈME : une mauvaise signature a été acceptée !"
            )

    except Exception as e:
        print("❌ Erreur :", e)


# ================================================================
# 7. TEST APPLICATION FLASK
# ================================================================

titre(7, "TEST APPLICATION FLASK")

try:
    from app import app

    print("✅ Application Flask importée.")

except Exception as e:
    print("❌ Impossible d'importer l'application Flask.")
    print("ERREUR :", e)
    app = None


# ================================================================
# 8. TEST MODELES DATABASE
# ================================================================

titre(8, "TEST MODELES DATABASE")

try:
    from app import db
    from models import Depot, User

    print("✅ Modèle Depot importé.")
    print("✅ Modèle User importé.")

except Exception as e:
    print("❌ Erreur import modèles :", e)
    db = None


# ================================================================
# 9. TEST ROUTE WEBHOOK
# ================================================================

titre(9, "TEST ROUTE WEBHOOK")

if app:

    try:
        routes = []

        for rule in app.url_map.iter_rules():
            routes.append(str(rule))

        if "/drimpay/webhook" in routes:
            print("✅ Route /drimpay/webhook trouvée.")
            print("   /drimpay/webhook")
        else:
            print("❌ Route /drimpay/webhook introuvable.")

    except Exception as e:
        print("❌ Erreur :", e)

else:
    print("⚠️ Application Flask indisponible.")


# ================================================================
# 10. TEST DATABASE
# ================================================================

titre(10, "TEST DATABASE")

if app and db:

    try:
        with app.app_context():

            db.session.execute(
                db.text("SELECT 1")
            )

            print("✅ Connexion PostgreSQL réussie.")

    except Exception as e:
        print("❌ Connexion PostgreSQL échouée.")
        print("ERREUR :", e)

else:
    print("⚠️ Test DB impossible.")


# ================================================================
# 11. TEST TABLE DEPOT
# ================================================================

titre(11, "TEST TABLE DEPOT")

if app and db:

    try:
        with app.app_context():

            count = Depot.query.count()

            print("✅ Table Depot accessible.")
            print(
                "Nombre de dépôts actuellement :",
                count
            )

    except Exception as e:
        print("❌ Table Depot inaccessible.")
        print("ERREUR :", e)

else:
    print("⚠️ Test Depot impossible.")


# ================================================================
# 12. CONFIGURATION FLASK
# ================================================================

titre(12, "CONFIGURATION FLASK")

if app:

    try:
        print("ENV :", app.config.get("ENV"))
        print("DEBUG :", app.config.get("DEBUG"))
        print("✅ Configuration Flask accessible.")

    except Exception as e:
        print("❌ Erreur configuration :", e)

else:
    print("⚠️ Application Flask indisponible.")


# ================================================================
# 13. TEST CONNEXION DRIMPAY
# ================================================================

titre(13, "TEST CONNEXION DRIMPAY")

try:

    response = requests.get(
        DRIMPAY_BASE_URL,
        timeout=15
    )

    print("HTTP STATUS :", response.status_code)

    print("Réponse :")
    print(response.text[:500])

    if response.status_code in (200, 401, 403, 404):
        print("✅ DrimPay est joignable depuis ton serveur.")
    else:
        print(
            "⚠️ DrimPay répond avec un statut inattendu."
        )

except requests.exceptions.Timeout:
    print("❌ Timeout : DrimPay ne répond pas.")

except requests.RequestException as e:
    print("❌ Erreur réseau :", e)


# ================================================================
# 14. TEST ENDPOINT STATUS
# ================================================================

titre(14, "TEST ENDPOINT STATUS")

print("ℹ️ Aucun paiement réel ne sera créé.")
print("ℹ️ On utilise volontairement une référence fictive.")

FAKE_REFERENCE = "TEST-REFERENCE-NECTARPRO"

try:

    success, response = drimpay.get_payin_status(
        FAKE_REFERENCE
    )

    print("success =", success)
    print("response =", response)

    if not DRIMPAY_SECRET_KEY:
        print(
            "⚠️ Test limité : API Key absente."
        )

    elif response.get("error") == "NO_API_KEY":
        print(
            "❌ DrimPay pense toujours que la clé API est absente."
        )

    elif (
        response.get("error") == "NOT_FOUND"
        or response.get("message", "").lower().find("not found") >= 0
    ):
        print(
            "✅ Endpoint get_payin_status accessible."
        )
        print(
            "ℹ️ La référence fictive n'existe normalement pas."
        )

    elif success:
        print(
            "✅ Endpoint get_payin_status fonctionne."
        )

    else:
        print(
            "⚠️ DrimPay a répondu avec une erreur :",
            response
        )

except Exception as e:
    print("❌ Erreur endpoint status :", e)


# ================================================================
# 15. TEST ROUTE DASHBOARD BLOQUE
# ================================================================

titre(15, "TEST ROUTE DASHBOARD BLOQUE")

if app:

    try:
        routes = [
            str(rule)
            for rule in app.url_map.iter_rules()
        ]

        if "/dashboard_bloque" in routes:
            print(
                "✅ Route /dashboard_bloque trouvée."
            )
        else:
            print(
                "❌ Route /dashboard_bloque introuvable."
            )

    except Exception as e:
        print("❌ Erreur :", e)

else:
    print("⚠️ Application Flask indisponible.")


# ================================================================
# RESUME
# ================================================================

titre("✓", "RESUME DU TEST")

print()
print(
    "DrimPay BASE URL       :",
    DRIMPAY_BASE_URL
)

print(
    "API KEY configurée     :",
    "OUI" if DRIMPAY_SECRET_KEY else "NON"
)

print(
    "WEBHOOK SECRET         :",
    "OUI" if DRIMPAY_WEBHOOK_SECRET else "NON"
)

try:
    tg_count = len(
        drimpay.OPERATORS_BY_COUNTRY.get("TG", [])
    )
except Exception:
    tg_count = 0

print(
    "Opérateurs TG          :",
    tg_count
)

print()

if DRIMPAY_SECRET_KEY and DRIMPAY_WEBHOOK_SECRET:
    print(
        "✅ Les deux secrets DrimPay sont configurés."
    )
else:
    print(
        "❌ Il manque au moins une variable secrète DrimPay."
    )

print()
print(
    "IMPORTANT : ce script n'a créé AUCUN paiement réel."
)
print()
print("=" * 65)