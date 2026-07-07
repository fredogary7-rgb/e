"""
SoleasPay Client - Récupération des services disponibles
Clé API : SOLEAS_API_KEY
Endpoint : GET https://soleaspay.com/api/services-list
"""

import sys
import requests

# ---------- CONFIGURATION ----------
SOLEAS_API_KEY = "SP_y7QKkaamPsVTlw8GDDGyzlJ7bmPUvdLorOQqWUXfRLI_AP"
BASE_URL = "https://soleaspay.com/api"
TIMEOUT = 20  # secondes


def get_services():
    """
    Récupère la liste des services disponibles depuis l'API SoleasPay.
    Retourne le JSON parsé (liste de dicts) en cas de succès.
    Lève une exception en cas d'erreur réseau, HTTP ou JSON.
    """
    url = f"{BASE_URL}/services-list"

    headers = {
        "Authorization": f"Bearer {SOLEAS_API_KEY}",
        "Accept": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT)

        # Erreur HTTP
        if response.status_code != 200:
            raise requests.HTTPError(
                f"Erreur HTTP {response.status_code} : {response.text[:300]}"
            )

        # Parsing JSON
        try:
            data = response.json()
        except ValueError:
            raise ValueError(
                f"Réponse non-JSON reçue : {response.text[:300]}"
            )

        return data

    except requests.ConnectionError:
        raise ConnectionError(
            "Impossible de se connecter à SoleasPay. Vérifiez votre connexion internet."
        )
    except requests.Timeout:
        raise TimeoutError(
            f"L'API SoleasPay ne répond pas (timeout après {TIMEOUT} secondes)."
        )
    except requests.RequestException as e:
        raise RuntimeError(f"Erreur réseau inattendue : {e}")


def display_services(services):
    """
    Affiche les services dans le terminal de manière lisible.
    """
    print("=" * 50)
    print("SOLEASPAY - SERVICES DISPONIBLES")
    print("=" * 50)
    print()

    if not services:
        print("Aucun service trouvé.")
        return

    for service in services:
        sid = service.get("id", "N/A")
        name = service.get("name") or service.get("nom", "N/A")
        stype = service.get("type", "N/A")
        active = service.get("active") or service.get("is_active", False)

        # Convertir le booléen en texte lisible
        if isinstance(active, bool):
            active_str = "Oui" if active else "Non"
        else:
            active_str = str(active)

        print(f"ID    : {sid}")
        print(f"Nom   : {name}")
        print(f"Type  : {stype}")
        print(f"Actif : {active_str}")
        print("-" * 32)
        print()

    print(f"Total des services : {len(services)}")


def main():
    """
    Point d'entrée principal quand le script est exécuté directement.
    """
    try:
        services = get_services()

        # Cas où l'API renvoie un dict avec une clé 'data' ou 'services'
        if isinstance(services, dict):
            services = (
                services.get("data")
                or services.get("services")
                or services.get("results")
                or services
            )

        if not isinstance(services, list):
            print(f"Format de réponse inattendu : {type(services).__name__}")
            print(f"Contenu brut : {services}")
            sys.exit(1)

        display_services(services)

    except (ConnectionError, TimeoutError, RuntimeError, requests.HTTPError, ValueError) as e:
        print(f"[ERREUR] {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrompu par l'utilisateur.")
        sys.exit(0)


if __name__ == "__main__":
    main()