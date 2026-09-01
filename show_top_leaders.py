import psycopg2
import io
from collections import defaultdict, deque

OUT = io.StringIO()
def log(*args):
    print(*args)
    print(*args, file=OUT)

DATABASE_URL = "postgresql://neondb_owner:npg_YaC69HIAGyZn@ep-muddy-darkness-ai9gl7w1-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require"

TARGETS = ["Bénin", "Côte d'Ivoire", "Cameroun"]

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Récupérer tous les utilisateurs avec les infos utiles
cur.execute("""
    SELECT username, parrain, country, phone, email, whatsapp_number,
           wallet_number, wallet_operator, login_count, last_login,
           solde_revenu, solde_parrainage, solde_total, premier_depot, date_creation
    FROM "user"
    WHERE username IS NOT NULL
""")
rows = cur.fetchall()
conn.close()

users = {}
children = defaultdict(list)  # parrain -> liste de usernames enfants (niveau 1)

for r in rows:
    (username, parrain, country, phone, email, wa, wnum, wop,
     login_count, last_login, solde_revenu, solde_parr, solde_total,
     premier_depot, date_creation) = r
    users[username] = {
        "username": username,
        "parrain": parrain,
        "country": (country or "").strip(),
        "phone": phone,
        "email": email,
        "whatsapp": wa,
        "wallet_number": wnum,
        "wallet_operator": wop,
        "login_count": login_count or 0,
        "last_login": last_login,
        "solde_revenu": solde_revenu or 0,
        "solde_parrainage": solde_parr or 0,
        "solde_total": solde_total or 0,
        "premier_depot": bool(premier_depot),
        "date_creation": date_creation,
    }
    if parrain:
        children[parrain].append(username)


def network_size(username):
    """Calcule le nombre total de filleuls (niveau 1 + 2 + 3) et le nombre direct."""
    direct = children.get(username, [])
    total = 0
    queue = deque(direct)
    seen = set(direct)
    while queue:
        u = queue.popleft()
        total += 1
        for child in children.get(u, []):
            if child not in seen:
                seen.add(child)
                queue.append(child)
    return len(direct), total


def fmt_money(v):
    try:
        return f"{float(v):,.0f} F"
    except Exception:
        return "0 F"


for target in TARGETS:
    # Leaders = utilisateurs de ce pays ayant au moins 1 filleul direct
    leaders = []
    for u, info in users.items():
        if info["country"].lower() != target.lower():
            continue
        direct, total = network_size(u)
        if direct == 0:
            continue
        leaders.append((total, direct, info))

    leaders.sort(key=lambda x: (-x[0], -x[1]))

    print("=" * 100)
    print(f"LEADERS LES PLUS ACTIFS — {target.upper()}  ({len(leaders)} leaders avec filleuls)")
    print("=" * 100)

    if not leaders:
        print("  Aucun leader trouvé pour ce pays.\n")
        continue

    for rank, (total, direct, info) in enumerate(leaders[:15], 1):
        print(f"\n#{rank}  @{info['username']}")
        print(f"    Réseau       : {total} filleul(s) au total ({direct} direct(s))")
        print(f"    Téléphone    : {info['phone']}")
        print(f"    WhatsApp     : {info['whatsapp'] or '—'}")
        print(f"    Email        : {info['email']}")
        print(f"    Wallet       : {info['wallet_operator'] or '—'} {info['wallet_number'] or ''}")
        print(f"    Revenus      : total {fmt_money(info['solde_total'])} | parrainage {fmt_money(info['solde_parrainage'])} | revenu {fmt_money(info['solde_revenu'])}")
        print(f"    Connexions   : {info['login_count']} | dernière {info['last_login']}")
        print(f"    Premier dépôt: {'OUI' if info['premier_depot'] else 'non'} | inscrit le {info['date_creation']}")
        print(f"    Parrain      : {info['parrain'] or '—'}")

    print()
