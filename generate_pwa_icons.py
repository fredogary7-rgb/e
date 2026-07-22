"""Génère les icônes PWA à partir de static/images/net.jpg"""
import os
from PIL import Image

BASE = r'c:\Users\user\Documents\d\e'
SIZES = [72, 96, 128, 144, 152, 192, 384, 512]
SRC = os.path.join(BASE, 'static', 'images', 'net.jpg')
OUT = os.path.join(BASE, 'static', 'images', 'pwa')

os.makedirs(OUT, exist_ok=True)

img = Image.open(SRC).convert('RGBA')
print(f"Source: {SRC} ({img.size[0]}x{img.size[1]})")

for s in SIZES:
    path = os.path.join(OUT, f'icon-{s}.png')
    img.resize((s, s), Image.LANCZOS).save(path, 'PNG')
    print(f"  OK {path} ({s}x{s})")

print("Termine.")