#!/usr/bin/env python3
# Patch pour corriger la fonction admin_deposits dans app.py

path = r'c:\Users\user\Documents\d\e\app.py'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Chercher et remplacer le bloc render_template de admin_deposits
old = (
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
    '    )'
)

new = (
    '    # Stats des dépôts\r\n'
    '    all_deposits = Depot.query.order_by(Depot.date.desc()).all()\r\n'
    '    total_amount = sum(d.montant for d in all_deposits if d.statut == \'valide\')\r\n'
    '    pending_count = sum(1 for d in all_deposits if d.statut == \'en_attente\')\r\n'
    '    validated_count = sum(1 for d in all_deposits if d.statut == \'valide\')\r\n'
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
    '    )'
)

if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('✅ Patch appliqué avec succès !')
else:
    print('❌ Texte cible non trouvé, vérification des fins de ligne...')
    # Essai sans \r
    old2 = old.replace('\r\n', '\n')
    if old2 in content:
        new2 = new.replace('\r\n', '\n')
        content = content.replace(old2, new2)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print('✅ Patch appliqué (fins de ligne LF) !')
    else:
        print('❌ Toujours non trouvé.')
