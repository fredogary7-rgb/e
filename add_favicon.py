import os

templates_dir = r'C:\Users\user\Documents\d\e\templates'
favicon_line = '<link rel="icon" href="/static/images/net.jpg" type="image/jpeg">\n'
count = 0

for f in sorted(os.listdir(templates_dir)):
    if not f.endswith('.html'):
        continue
    path = os.path.join(templates_dir, f)
    
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
        end = content.index('>', idx) + 1
        new_content = content[:end] + '\n' + favicon_line + content[end:]
    elif '<meta charset' in content:
        idx = content.index('<meta charset')
        end = content.index('>', idx) + 1
        new_content = content[:end] + '\n' + favicon_line + content[end:]
    else:
        head_idx = content.index('</head>')
        new_content = content[:head_idx] + favicon_line + content[head_idx:]
    
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(new_content)
    count += 1
    print(f'  OK: {f}')

print(f'\n{count} templates mis a jour avec favicon net.jpg')