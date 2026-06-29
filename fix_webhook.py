#!/usr/bin/env python3
path = r'c:\Users\user\Documents\d\e\app.py'

with open(path, 'rb') as f:
    content = f.read()

# On repere le debut et la fin du bloc a remplacer
DEBUT = b'    data = request.get_json()\r\n    details = data.get("data", {})'
FIN   = b'    db.session.commit()\r\n    return jsonify({"received": True})\r\n'

idx_debut = content.find(DEBUT)
idx_fin   = content.find(FIN, idx_debut) + len(FIN)

if idx_debut == -1:
    print('ECHEC - debut non trouve')
    exit(1)
if idx_fin == -1:
    print('ECHEC - fin non trouvee')
    exit(1)

print(f'Bloc localise : lignes {content[:idx_debut].count(b"\\n")+1} a {content[:idx_fin].count(b"\\n")+1}')
