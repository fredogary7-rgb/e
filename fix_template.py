p = r'c:\Users\user\Documents\d\e\tasks.py'
d = open(p, 'rb').read()
d = d.replace(b"taches_clean.html", b"tiktok_v3.html")
open(p, 'wb').write(d)
print('OK')
