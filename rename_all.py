import os
import glob

base_dir = r'c:\Users\user\Documents\d\e\templates'
files = glob.glob(os.path.join(base_dir, '*.html'))
count = 0

for filepath in files:
    try:
        with open(filepath, 'r', encoding='utf-8') as fh:
            content = fh.read()
        
        original = content
        content = content.replace('novatrade', 'NectarPro')
        content = content.replace('NovaTrade', 'NectarPro')
        content = content.replace('NOVATRADE', 'NectarPro')
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as fh:
                fh.write(content)
            fname = os.path.basename(filepath)
            print(f'Modifie: {fname}')
            count += 1
        else:
            fname = os.path.basename(filepath)
            print(f'Aucun changement: {fname}')
    except Exception as e:
        print(f'ERREUR sur {filepath}: {e}')

print(f'\n{count} fichiers modifies sur {len(files)}')