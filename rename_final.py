import glob, os

files = glob.glob(os.path.join('templates', '*.html'))
modified = 0
root_dir = os.getcwd()
templates_dir = os.path.join(root_dir, 'templates')

for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as fh:
            content = fh.read()
        new = content.replace('NovaTrade', 'NectarPro').replace('novatrade', 'NectarPro').replace('NOVATRADE', 'NectarPro')
        if new != content:
            basename = os.path.basename(f)
            tmp_path = os.path.join(root_dir, basename + '.nectar_tmp')
            with open(tmp_path, 'w', encoding='utf-8') as tmpf:
                tmpf.write(new)
            os.replace(tmp_path, f)
            print(f'MODIFIE: {basename}')
            modified += 1
        else:
            print(f'AUCUN: {os.path.basename(f)}')
    except Exception as e:
        print(f'ERREUR {os.path.basename(f)}: {e}')

print(f'\n{modified} fichiers modifies sur {len(files)}')