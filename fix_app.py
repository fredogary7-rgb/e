import os

filepath = r'c:\Users\user\Documents\d\e\app.py'

with open(filepath, 'rb') as f:
    data = f.read()

bad = b'        is_blocked_500=(is_blocked_500 or no_rounds_left)\r\n    )\r\n'

if bad in data:
    data = data.replace(bad, b'', 1)
    result_path = r'c:\Users\user\Documents\d\e\app_new.py'
    with open(result_path, 'wb') as f:
        f.write(data)
    print('Ecrit dans app_new.py')
    # Remplacer l'original
    os.remove(filepath)
    os.rename(result_path, filepath)
    print('OK!')
else:
    print('ECHEC - doublon CRLF non trouve')

