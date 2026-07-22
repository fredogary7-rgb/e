import re
with open("app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "def connexion_page" in line:
        print(f"LIGNE {i+1}: {line.rstrip()}")
        # Afficher 40 lignes suivantes
        for j in range(i+1, min(i+41, len(lines))):
            print(f"  {j+1}: {lines[j].rstrip()}")
        break