"""Génère les icônes PWA à partir de static/images/net.jpg - écrit dans static/images/"""
import os
from PIL import Image

os.chdir(r'c:\Users\user\Documents\d\e')

SIZES = [72, 96, 128, 144, 152, 192, 384, 512]
SRC = os.path.join('static', 'images', 'net.jpg')

img = Image.open(SRC).convert('RGBA')
print(f"Source: {SRC} ({img.size[0]}x{img.size[1]})")

for s in SIZES:
    path = os.path.join('static', 'images', f'icon-{s}.png')
    img.resize((s, s), Image.LANCZOS).save(path, 'PNG')
    print(f"  OK {path} ({s}x{s})")

print("Termine.")