# -*- coding: utf-8 -*-
"""Remplace les anciens domaines par le nouveau domaine nectar-pro.cc"""
import os

FILES = [
    r"c:\Users\user\Documents\d\e\static\manifest.json",
    r"c:\Users\user\Documents\d\e\static\pwa-register.js",
    r"c:\Users\user\Documents\d\e\static\robots.txt",
    r"c:\Users\user\Documents\d\e\templates\connexion.html",
    r"c:\Users\user\Documents\d\e\templates\index.html",
    r"c:\Users\user\Documents\d\e\templates\inscription.html",
    r"c:\Users\user\Documents\d\e\templates\market.html",
    r"c:\Users\user\Documents\d\e\app.py",
    r"c:\Users\user\Documents\d\e\monitor.py",
    r"c:\Users\user\Documents\d\e\push_notifications.py",
]

REPLACEMENTS = [
    ("web-production-d52c9.up.railway.app", "nectar-pro.cc"),
    ("nectarpro.cc", "nectar-pro.cc"),
]

for path in FILES:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    for old, new in REPLACEMENTS:
        content = content.replace(old, new)

    if content != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[MODIFIE] {path}")
    else:
        print(f"[AUCUN CHANGEMENT] {path}")
