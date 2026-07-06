"""Module Tâches Quotidiennes - NovaTrade.
Tous les imports sont lazy (dans les fonctions) pour éviter l'import circulaire avec app.py.
Les modèles DailyTask, UserTask, TaskReward sont définis dans app.py.
Les routes sont définies dans app.py et délèguent vers ce module.
"""

TASK_COUNT = 10
TASK_REWARD_MIN = 25
TASK_REWARD_MAX = 100


def _sel(date_obj):
    """Sélectionne aléatoirement TASK_COUNT produits/publicités pour la date donnée."""
    import random
    from sqlalchemy import func as sf
    from app import Produit, Publicite

    prods = Produit.query.filter_by(est_actif=True).order_by(sf.random()).limit(6).all()
    pubs = Publicite.query.filter_by(est_actif=True).order_by(sf.random()).limit(6).all()
    items = [('produit', p.id) for p in prods] + [('publicite', pub.id) for pub in pubs]
    random.shuffle(items)
    return items[:TASK_COUNT]


def _tasks(date_obj):
    """Récupère ou crée les tâches de la date donnée."""
    from app import db, DailyTask

    tasks = DailyTask.query.filter_by(date=date_obj, actif=True).order_by(DailyTask.ordre).all()
    if not tasks:
        for i, (ctype, cid) in enumerate(_sel(date_obj)):
            t = (
                DailyTask(produit_id=cid, content_type='produit', date=date_obj, ordre=i)
                if ctype == 'produit'
                else DailyTask(publicite_id=cid, content_type='publicite', date=date_obj, ordre=i)
            )
            db.session.add(t)
        db.session.commit()
        tasks = DailyTask.query.filter_by(date=date_obj, actif=True).order_by(DailyTask.ordre).all()
    return tasks


def _prog(user_id, date_obj):
    """Calcule la progression (nb de partages, mapping task_id -> UserTask)."""
    from app import DailyTask, UserTask

    tasks = DailyTask.query.filter_by(date=date_obj, actif=True).all()
    ids = [t.id for t in tasks]
    uts = UserTask.query.filter(UserTask.user_id == user_id, UserTask.task_id.in_(ids)).all()
    return sum(1 for u in uts if u.shared), {u.task_id: u for u in uts}


# ─── Fonctions de vue (appelées par les routes dans app.py) ───

def taches_page():
    """Page /taches - affiche les tâches quotidiennes."""
    from datetime import datetime, date
    from flask import render_template, redirect, url_for, flash
    from app import get_logged_in_user, user_is_activated, db, DailyTask, TaskReward

    user = get_logged_in_user()
    if not user:
        flash("Connectez-vous.", "danger")
        return redirect(url_for('connexion_page'))
    if not user_is_activated(user):
        flash("Compte non activé.", "warning")
        return redirect(url_for('dashboard_page'))

    now = datetime.now()
    today = now.date()

    if now.weekday() >= 5:
        return render_template('tiktok_v3.html', user=user, taches=[], shared_count=0,
                               total=TASK_COUNT, can_start=False, message="⏸️ Lun-Ven uniquement.")
    if now.hour < 8:
        return render_template('tiktok_v3.html', user=user, taches=[], shared_count=0,
                               total=TASK_COUNT, can_start=False, message="⏰ Ouvre à 08h00.")
    if now.hour >= 23:
        return render_template('tiktok_v3.html', user=user, taches=[], shared_count=0,
                               total=TASK_COUNT, can_start=False, message="🌙 Terminé.")

    rw = TaskReward.query.filter_by(user_id=user.id, date=today).first()
    if rw:
        return render_template('tiktok_v3.html', user=user, taches=[], shared_count=TASK_COUNT,
                               total=TASK_COUNT, can_start=False, reward_amount=rw.montant,
                               message=f"✅ +{int(rw.montant)} FCFA aujourd'hui!")

    # Régénérer les tâches du jour
    DailyTask.query.filter_by(date=today).delete()
    for i, (ctype, cid) in enumerate(_sel(today)):
        t = (
            DailyTask(produit_id=cid, content_type='produit', date=today, ordre=i)
            if ctype == 'produit'
            else DailyTask(publicite_id=cid, content_type='publicite', date=today, ordre=i)
        )
        db.session.add(t)
    db.session.commit()

    tasks = _tasks(today)
    sc, utm = _prog(user.id, today)
    td = []
    for task in tasks:
        ut = utm.get(task.id)
        if task.content_type == 'publicite' and task.publicite:
            p = task.publicite
            td.append({
                'task_id': task.id, 'type': 'publicite', 'nom': p.titre,
                'image': p.video_url,
                'boutique_nom': p.boutique.nom if p.boutique else 'NovaTrade',
                'shared': ut.shared if ut else False
            })
        else:
            p = task.produit
            td.append({
                'task_id': task.id, 'type': 'produit', 'nom': p.nom if p else '?',
                'image': (p.liste_images[0] if p and p.liste_images else None),
                'boutique_nom': p.boutique.nom if p and p.boutique else 'NovaTrade',
                'shared': ut.shared if ut else False
            })

    import random
    est = random.randint(TASK_REWARD_MIN, TASK_REWARD_MAX)
    return render_template('tiktok_v3.html', user=user, taches=td, shared_count=sc,
                           total=TASK_COUNT, can_start=True, estimated_reward=est)


def api_share_task():
    """API pour partager une tâche."""
    from datetime import datetime, date
    from flask import request, jsonify, session
    from app import get_logged_in_user, user_is_activated, db, DailyTask, UserTask, Publicite

    user = get_logged_in_user()
    if not user or not user_is_activated(user):
        return jsonify({'success': False}), 403

    data = request.get_json()
    task_id = data.get('task_id')
    if not task_id:
        return jsonify({'success': False}), 400

    now = datetime.now()
    today = now.date()
    if now.weekday() >= 5 or now.hour < 8 or now.hour >= 23:
        return jsonify({'success': False}), 400

    task = DailyTask.query.get(task_id)
    if not task or not task.actif or task.date != today:
        return jsonify({'success': False}), 400

    ut = UserTask.query.filter_by(user_id=user.id, task_id=task_id).first()
    if ut and ut.shared:
        return jsonify({'success': False}), 400

    if ut:
        ut.shared = True
        ut.shared_at = datetime.utcnow()
    else:
        db.session.add(UserTask(user_id=user.id, task_id=task_id, shared=True, shared_at=datetime.utcnow()))

    if task.content_type == 'publicite' and task.publicite_id:
        task.publicite.partages = (task.publicite.partages or 0) + 1
    else:
        pub = Publicite.query.filter_by(produit_id=task.produit_id).first()
        if pub:
            pub.partages = (pub.partages or 0) + 1

    db.session.commit()
    sc, _ = _prog(user.id, today)
    return jsonify({'success': True, 'shared_count': sc, 'total': TASK_COUNT,
                    'completed': sc >= TASK_COUNT})


def api_claim_task_reward():
    """API pour réclamer la récompense après avoir partagé toutes les tâches."""
    import random
    from datetime import datetime, date
    from flask import request, jsonify
    from app import get_logged_in_user, db, TaskReward

    user = get_logged_in_user()
    if not user:
        return jsonify({'success': False}), 401

    today = datetime.now().date()
    if TaskReward.query.filter_by(user_id=user.id, date=today).first():
        return jsonify({'success': False}), 400

    sc, _ = _prog(user.id, today)
    if sc < TASK_COUNT:
        return jsonify({'success': False}), 400

    m = random.randint(TASK_REWARD_MIN, TASK_REWARD_MAX)
    user.solde_parrainage = (user.solde_parrainage or 0) + m
    db.session.add(TaskReward(user_id=user.id, date=today, montant=m))
    db.session.commit()
    return jsonify({'success': True, 'montant': int(m), 'message': f'+{int(m)} FCFA 🎉'})


def admin_taches():
    """Page admin pour gérer les tâches."""
    from datetime import date
    from flask import render_template, request, redirect, url_for, flash
    from sqlalchemy import func as f
    from app import get_logged_in_user, db, DailyTask, UserTask, Boutique, Produit

    user = get_logged_in_user()
    if not user or not user.is_admin:
        flash("Accès refusé.", "danger")
        return redirect(url_for('connexion_page'))

    today = date.today()

    if request.method == 'POST':
        a = request.form.get('action')
        if a == 'generate':
            _tasks(today)
            flash("OK", "success")
        elif a == 'toggle':
            t = DailyTask.query.get(request.form.get('task_id'))
            if t:
                t.actif = not t.actif
                db.session.commit()
        elif a == 'regenerate':
            DailyTask.query.filter_by(date=today).delete()
            db.session.commit()
            _tasks(today)
        return redirect(url_for('admin_taches_route'))

    tasks = DailyTask.query.filter_by(date=today).order_by(DailyTask.ordre).all()
    for t in tasks:
        t.share_count = UserTask.query.filter_by(task_id=t.id, shared=True).count()

    vs = db.session.query(
        Boutique.nom, f.count(UserTask.id).label('t')
    ).join(Produit, Produit.boutique_id == Boutique.id
    ).join(DailyTask, DailyTask.produit_id == Produit.id
    ).join(UserTask, UserTask.task_id == DailyTask.id
    ).filter(UserTask.shared == True
    ).group_by(Boutique.id
    ).order_by(f.count(UserTask.id).desc()
    ).limit(20).all()

    return render_template('admin_taches.html', user=user, tasks=tasks, today=today, vendeur_stats=vs)