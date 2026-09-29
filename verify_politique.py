# -*- coding: utf-8 -*-
import re

# Verification politique_v2.html
with open('templates/politique_v2.html', 'r', encoding='utf-8') as f:
    s = f.read()

nums = re.findall(r'section-num">([0-9]+)<', s)
print("Politique v2 - numeros:", nums)
print("Sequence 1..13 OK:", nums == [str(i) for i in range(1, 14)])
# Verifier pas de doublon 'Retraits'/'Paiements'
print("Contient 'Paiements et retraits' (ancien doublon):", 'Paiements et retraits' in s)
print("Contient 'Retraits automatiques':", 'Retraits automatiques' in s)

# Verification inscription.html
with open('templates/inscription.html', 'r', encoding='utf-8') as f:
    s2 = f.read()
h4 = re.findall(r'<h4>(\d+)\.', s2)
print("\nInscription modale - sections:", h4)
print("Sequence 1..13 OK:", h4 == [str(i) for i in range(1, 14)])
print("dl div ouverts:", s2.count('<div'), "fermes:", s2.count('</div>'))
