import os

templates_dir = '/data/data/com.termux/files/home/e/templates'
favicon_line = '    <link rel="icon" href="/static/images/net.jpg" type="image/jpeg">\n'
count = 0

for f in sorted(os.listdir(templates_dir)):
    if not f.endswith('.html'):
        continue
    path = os.path.join(templates_dir, f)
    
    try:
        with open(path, 'rb') as fh:
            raw = fh.read()
        
        try:
            content = raw.decode('utf-8')
        except UnicodeDecodeError:
            content = raw.decode('latin-1')
        
        if 'rel="icon"' in content or "rel='icon'" in content:
            print(f'  SKIP (deja): {f}')
            continue
        
        if '<meta name="viewport"' in content:
            idx = content.index('<meta name="viewport"')
            end = content.find('>', idx) + 1
            new_content = content[:end] + '\n' + favicon_line + content[end:]
        elif '<meta charset' in content:
            idx = content.index('<meta charset')
            end = content.find('>', idx) + 1
            new_content = content[:end] + '\n' + favicon_line + content[end:]
        elif '</head>' in content:
            head_idx = content.index('</head>')
            new_content = content[:head_idx] + favicon_line + content[head_idx:]
        else:
            new_content = favicon_line + content
        
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(new_content)
        count += 1
        print(f'  OK: {f}')
        
    except Exception as e:
        print(f'  ERREUR (ignore): {f} -> {e}')

print(f'\n{count} templates mis a jour avec favicon net.jpg')

