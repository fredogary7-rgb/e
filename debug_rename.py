import os

ROOT = os.getcwd()
print(f"ROOT: {ROOT}")

SKIP_EXTS = {'.exe', '.jpg', '.jpeg', '.png', '.gif', '.ico',
             '.mp4', '.webm', '.mp3', '.pdf', '.db', '.pyc', '.webp', '.tmp', '.ps1', '.cmd'}

count = 0
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'migrations'} and not d.startswith('.')]
    for filename in filenames:
        if filename in {'rename_nectarpro.py', 'debug_rename.py', 'rename.ps1', 'run_rename.cmd'}:
            continue
        ext = os.path.splitext(filename)[1].lower()
        if ext in SKIP_EXTS:
            continue
        filepath = os.path.join(dirpath, filename)
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            if b'NovaTrade' in content:
                rel = os.path.relpath(filepath, ROOT)
                print(f"Found: {rel} ({content.count(b'NovaTrade')} hits)")
                count += 1
        except Exception as e:
            print(f"Error: {filepath}: {e}")

print(f"Total files with NovaTrade: {count}")