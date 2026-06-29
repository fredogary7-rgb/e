import os, sys, pathlib

filepath = pathlib.Path("c:/Users/user/Documents/d/e/app.py")

lines = filepath.read_text(encoding="utf-8").splitlines(keepends=True)

print("Total lignes avant:", len(lines))

# Supprimer les lignes doublon (index base 0 = lignes 2687 et 2688 du fichier)
lines_to_remove = set([2686, 2687])
new_lines = [l for i, l in enumerate(lines) if i not in lines_to_remove]

print("Total lignes apres:", len(new_lines))
print("Lignes autour de 2684-2690:")
for i, l in enumerate(new_lines[2683:2691], start=2684):
    print(i, repr(l))

content_str = "".join(new_lines)
filepath.write_text(content_str, encoding="utf-8")
print("Fichier ecrit avec succes via pathlib!")


