#!/usr/bin/env python3
# -*- coding: ascii -*-
import pathlib, sys

app_path = pathlib.Path('app.py')
raw = app_path.read_bytes()
content = raw.decode('utf-8')

# Bloc a remplacer (avec \r\n car Windows)
old_block = (
    '    # 2. D\u00c9POTS EN ATTENTE (Filtrage sur les nouveaux utilisateurs)\r\n'
    '    subquery = (\r\n'
    '        db.session.query(func.max(Depot.id).label("last_id"))\r\n'
    '        .join(User, Depot.user_name == User.username)\r\n'
    '        .filter(Depot.statut == "en_attente", User.premier_depot == False)\r\n'
    '        .group_by(Depot.phone).subquery()\r\n'
    '    )\r\n'
    '\r\n'
    '    depots = (\r\n'
    '        Depot.query.filter(Depot.id.in_(db.session.query(subquery.c.last_id)))\r\n'
    '        .join(User, Depot.user_name == User.username)\r\n'
    '        .order_by(Depot.date.desc()).all()\r\n'
    '    )\r\n'
    '\r\n'
    '    # 3. RETRAITS (Version corrig\u00e9e avec jointure)\r\n'
    '    retraits_paginated = (\r\n'
    '        db.session.query(Retrait, User.username)\r\n'
    '        .join(User, Retrait.user_id == User.id)\r\n'
    '        .order_by(Retrait.date.desc())\r\n'
    '        .paginate(page=page, per_page=PER_PAGE, error_out=False)\r\n'
    '    )\r\n'
    '\r\n'
    '    retraits_list = []\r\n'
    '    for r, uname in retraits_paginated.items:\r\n'
    '        r.username_display = uname\r\n'
    '        retraits_list.append(r)\r\n'
    '\r\n'
    '    return render_template(\r\n'
    '        "admin_deposits.html",\r\n'
    '        user=user,\r\n'
    '        users=users_paginated.items,\r\n'
    '        depots=depots,\r\n'
    '        retraits=retraits_list,\r\n'
    '        actifs=actifs,\r\n'
    '        inactifs=inactifs,\r\n'
    '        total_actifs=total_actifs,\r\n'
    '        total_inactifs=total_inactifs,\r\n'
    '        users_paginated=users_paginated,\r\n'
    '        retraits_paginated=retraits_paginated\r\n'
    '    )\r\n'
)

new_block = (
    '    # 2. TOUS LES DEPOTS (pour la liste principale du template)\r\n'
    '    all_deposits = Depot.query.order_by(Depot.date.desc()).all()\r\n'
    '\r\n'
    "    # Stats des depots\r\n"
    "    total_amount = sum(d.montant for d in all_deposits if d.statut == 'valide')\r\n"
    "    pending_count = sum(1 for d in all_deposits if d.statut == 'en_attente')\r\n"
    "    validated_count = sum(1 for d in all_deposits if d.statut == 'valide')\r\n"
    '\r\n'
    "    # Enrichir chaque depot avec l'objet user et payment_method\r\n"
    '    for d in all_deposits:\r\n'
    '        if d.user_name:\r\n'
    '            d.user = User.query.filter_by(username=d.user_name).first()\r\n'
    '        elif d.user_id:\r\n'
    '            d.user = db.session.get(User, d.user_id)\r\n'
    '        else:\r\n'
    '            d.user = None\r\n'
    "        d.payment_method = d.operator or '-'\r\n"
    '\r\n'
    '    # 2b. DEPOTS EN ATTENTE (Filtrage sur les nouveaux utilisateurs)\r\n'
    '    subquery = (\r\n'
    '        db.session.query(func.max(Depot.id).label("last_id"))\r\n'
    '        .join(User, Depot.user_name == User.username)\r\n'
    '        .filter(Depot.statut == "en_attente", User.premier_depot == False)\r\n'
    '        .group_by(Depot.phone).subquery()\r\n'
    '    )\r\n'
    '\r\n'
    '    depots = (\r\n'
    '        Depot.query.filter(Depot.id.in_(db.session.query(subquery.c.last_id)))\r\n'
    '        .join(User, Depot.user_name == User.username)\r\n'
    '        .order_by(Depot.date.desc()).all()\r\n'
    '    )\r\n'
    '\r\n'
    '    # 3. RETRAITS (Version corrigee avec jointure)\r\n'
    '    retraits_paginated = (\r\n'
    '        db.session.query(Retrait, User.username)\r\n'
    '        .join(User, Retrait.user_id == User.id)\r\n'
    '        .order_by(Retrait.date.desc())\r\n'
    '        .paginate(page=page, per_page=PER_PAGE, error_out=False)\r\n'
    '    )\r\n'
    '\r\n'
    '    retraits_list = []\r\n'
    '    for r, uname in retraits_paginated.items:\r\n'
    '        r.username_display = uname\r\n'
    '        retraits_list.append(r)\r\n'
    '\r\n'
    '    return render_template(\r\n'
    '        "admin_deposits.html",\r\n'
    '        user=user,\r\n'
    '        users=users_paginated.items,\r\n'
    '        depots=depots,\r\n'
    '        deposits=all_deposits,\r\n'
    '        total_amount=total_amount,\r\n'
    '        pending_count=pending_count,\r\n'
    '        validated_count=validated_count,\r\n'
    '        retraits=retraits_list,\r\n'
    '        actifs=actifs,\r\n'
    '        inactifs=inactifs,\r\n'
    '        total_actifs=total_actifs,\r\n'
    '        total_inactifs=total_inactifs,\r\n'
    '        users_paginated=users_paginated,\r\n'
    '        retraits_paginated=retraits_paginated\r\n'
    '    )\r\n'
)

if old_block in content:
    new_content = content.replace(old_block, new_block, 1)
    app_path.write_bytes(new_content.encode('utf-8'))
    print("OK - app.py modifie avec succes!")
else:
    print("ERREUR: bloc original introuvable")
    idx = content.find('    # 2. D')
    print(f"Index trouve: {idx}")
    if idx > 0:
        print(repr(content[idx:idx+100]))

# Verification finale
content2 = app_path.read_bytes().decode('utf-8')
checks = ['total_amount', 'pending_count', 'validated_count', 'deposits=all_deposits']
for c in checks:
    status = 'OK' if c in content2 else 'MANQUANT'
    print(f"  [{status}] {c}")
