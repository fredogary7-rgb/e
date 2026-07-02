import os
import sys

SKIP_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'migrations'}
SKIP_EXTS = {'.exe', '.dll', '.jpg', '.jpeg', '.png', '.gif', '.ico',
             '.mp4', '.webm', '.mov', '.avi', '.mp3', '.wav', '.ogg',
             '.pdf', '.db', '.pyc', '.webp', '.tmp', '.ps1', '.cmd'}
SKIP_NAMES = {'rename_nectarpro.py', 'debug_rename.py', 'rename.ps1', 'run_rename.cmd'}

ROOT = os.getcwd()
print(f"ROOT: {ROOT}")

def process_file(filepath):
    content = None
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        print(f"READ ERROR: {filepath}: {e}")
        return False

    if content is None:
        return False

    new_content = content
    new_content = new_content.replace('NovaTrade', 'NectarPro')
    new_content = new_content.replace('nova-trade', 'nectarpro')
    new_content = new_content.replace('nova_trade', 'nectar_pro')
    new_content = new_content.replace('novatrade', 'nectarpro')
    new_content = new_content.replace('NOVATRADE', 'NECTARPRO')

    if new_content == content:
        return False

    # Write using a temp file approach to avoid locking issues
    tmp_path = filepath + '.tmp'
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        os.replace(tmp_path, filepath)
        return True
    except Exception as e:
        print(f"WRITE ERROR: {filepath}: {e}")
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except:
            pass
        return False

def main():
    count = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')]
        for filename in filenames:
            if filename in SKIP_NAMES:
                continue
            ext = os.path.splitext(filename)[1].lower()
            if ext in SKIP_EXTS:
                continue
            filepath = os.path.join(dirpath, filename)
            if process_file(filepath):
                rel = os.path.relpath(filepath, ROOT)
                print(f'OK: {rel}')
                count += 1
    print(f'Total: {count}')

if __name__ == '__main__':
    main()