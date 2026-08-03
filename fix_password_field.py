#!/usr/bin/env python3
"""Fix the /new-password route: change 'password' → 'new_password'."""
import sys

FILE = 'app.py'
TARGET_LINE_1 = "        password = request.form.get('password')"
REPLACEMENT_1 = "        password = request.form.get('new_password')"

with open(FILE, 'r', encoding='utf-8') as f:
    lines = f.readlines()

changed = False
for i, line in enumerate(lines):
    if line.rstrip('\n\r') == TARGET_LINE_1.rstrip('\n\r'):
        lines[i] = line.replace("request.form.get('password')", "request.form.get('new_password')")
        print(f"Fixed line {i+1}: {TARGET_LINE_1} → {REPLACEMENT_1}")
        changed = True
        break

if not changed:
    print("Line not found, searching for partial match...")
    for i, line in enumerate(lines):
        if "request.form.get('password')" in line and "new_password" not in line:
            lines[i] = line.replace("request.form.get('password')", "request.form.get('new_password')")
            print(f"Fixed line {i+1} (partial match): {lines[i].rstrip()}")
            changed = True
            break

if changed:
    with open(FILE, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("File written successfully.")
else:
    print("No line found to fix.", file=sys.stderr)
    sys.exit(1)