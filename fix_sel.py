p = r'c:\Users\user\Documents\d\e\tasks.py'
with open(p, 'rb') as f:
    d = f.read()
old = b"def _sel(date_obj):\r\n    prods=Produit.query.filter_by(est_actif=True).order_by((Produit.vues+Produit.ventes*10).desc()).limit(7).all()\r\n    pubs=Publicite.query.filter_by(est_actif=True).order_by((Publicite.vues+Publicite.partages*5).desc()).limit(5).all()\r\n    items=[('produit',p.id) for p in prods]+[('publicite',pub.id) for pub in pubs]\r\n    import random; random.seed(str(date_obj)); random.shuffle(items)\r\n    return items[:TASK_COUNT]"
new = b"def _sel(date_obj):\r\n    from app import Produit, Publicite\r\n    from sqlalchemy import func as sf\r\n    prods=Produit.query.filter_by(est_actif=True).order_by(sf.random()).limit(6).all()\r\n    pubs=Publicite.query.filter_by(est_actif=True).order_by(sf.random()).limit(6).all()\r\n    items=[('produit',p.id) for p in prods]+[('publicite',pub.id) for pub in pubs]\r\n    import random; random.shuffle(items)\r\n    return items[:TASK_COUNT]"
d = d.replace(old, new)
with open(p, 'wb') as f:
    f.write(d)
print('done')
