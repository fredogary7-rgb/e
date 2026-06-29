"""Module Tâches Quotidiennes - NovaTrade"""
from datetime import datetime, date
from flask import render_template, request, redirect, url_for, flash, jsonify
from app import app, db

TASK_COUNT=10; TASK_REWARD_MIN=25; TASK_REWARD_MAX=100

class DailyTask(db.Model):
    __tablename__='daily_tasks'
    id=db.Column(db.Integer,primary_key=True)
    produit_id=db.Column(db.Integer,db.ForeignKey('produits.id'),nullable=True)
    publicite_id=db.Column(db.Integer,db.ForeignKey('publicites.id'),nullable=True)
    content_type=db.Column(db.String(20),default='produit')
    date=db.Column(db.Date,nullable=False,index=True)
    ordre=db.Column(db.Integer,default=0); actif=db.Column(db.Boolean,default=True)
    produit=db.relationship('Produit',backref='daily_tasks')
    publicite=db.relationship('Publicite',backref='daily_tasks')

class UserTask(db.Model):
    __tablename__='user_tasks'
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)
    task_id=db.Column(db.Integer,db.ForeignKey('daily_tasks.id'),nullable=False)
    shared=db.Column(db.Boolean,default=False); shared_at=db.Column(db.DateTime)

class TaskReward(db.Model):
    __tablename__='task_rewards'
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)
    date=db.Column(db.Date,nullable=False,index=True)
    montant=db.Column(db.Float,nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)

def _sel(date_obj):
    from app import Produit, Publicite
    prods=Produit.query.filter_by(est_actif=True).order_by((Produit.vues+Produit.ventes*10).desc()).limit(7).all()
    pubs=Publicite.query.filter_by(est_actif=True).order_by((Publicite.vues+Publicite.partages*5).desc()).limit(5).all()
    items=[('produit',p.id) for p in prods]+[('publicite',pub.id) for pub in pubs]
    import random; random.seed(str(date_obj)); random.shuffle(items)
    return items[:TASK_COUNT]

def _tasks(date_obj):
    tasks=DailyTask.query.filter_by(date=date_obj,actif=True).order_by(DailyTask.ordre).all()
    if not tasks:
        for i,(ctype,cid) in enumerate(_sel(date_obj)):
            t=DailyTask(produit_id=cid,content_type='produit',date=date_obj,ordre=i) if ctype=='produit' else DailyTask(publicite_id=cid,content_type='publicite',date=date_obj,ordre=i)
            db.session.add(t)
        db.session.commit()
        tasks=DailyTask.query.filter_by(date=date_obj,actif=True).order_by(DailyTask.ordre).all()
    return tasks

def _prog(user_id,date_obj):
    tasks=DailyTask.query.filter_by(date=date_obj,actif=True).all()
    ids=[t.id for t in tasks]
    uts=UserTask.query.filter(UserTask.user_id==user_id,UserTask.task_id.in_(ids)).all()
    return sum(1 for u in uts if u.shared),{u.task_id:u for u in uts}

@app.route('/taches')
def taches_page():
    from app import get_logged_in_user, user_is_activated
    user=get_logged_in_user()
    if not user: flash("Connectez-vous.","danger"); return redirect(url_for('connexion_page'))
    if not user_is_activated(user): flash("Compte non activé.","warning"); return redirect(url_for('dashboard_page'))
    now=datetime.now(); today=now.date()
    if now.weekday()>=5: return render_template('taches_clean.html',user=user,taches=[],shared_count=0,total=TASK_COUNT,can_start=False,message="⏸️ Lun-Ven uniquement.")
    if now.hour<8: return render_template('taches_clean.html',user=user,taches=[],shared_count=0,total=TASK_COUNT,can_start=False,message="⏰ Ouvre à 08h00.")
    if now.hour>=23: return render_template('taches_clean.html',user=user,taches=[],shared_count=0,total=TASK_COUNT,can_start=False,message="🌙 Terminé.")
    rw=TaskReward.query.filter_by(user_id=user.id,date=today).first()
    if rw: return render_template('taches_clean.html',user=user,taches=[],shared_count=TASK_COUNT,total=TASK_COUNT,can_start=False,reward_amount=rw.montant,message=f"✅ +{int(rw.montant)} FCFA aujourd'hui!")
    tasks=_tasks(today); sc,utm=_prog(user.id,today); td=[]
    for task in tasks:
        ut=utm.get(task.id)
        if task.content_type=='publicite' and task.publicite:
            p=task.publicite; td.append({'task_id':task.id,'type':'publicite','nom':p.titre,'image':p.video_url,'boutique_nom':p.boutique.nom if p.boutique else 'NovaTrade','shared':ut.shared if ut else False})
        else:
            p=task.produit; td.append({'task_id':task.id,'type':'produit','nom':p.nom if p else '?','image':(p.liste_images[0] if p and p.liste_images else None),'boutique_nom':p.boutique.nom if p and p.boutique else 'NovaTrade','shared':ut.shared if ut else False})
    import random; est=random.randint(TASK_REWARD_MIN,TASK_REWARD_MAX)
    return render_template('taches_clean.html',user=user,taches=td,shared_count=sc,total=TASK_COUNT,can_start=True,estimated_reward=est)

@app.route('/api/share-task',methods=['POST'])
def api_share_task():
    from app import get_logged_in_user, user_is_activated, Publicite
    user=get_logged_in_user()
    if not user or not user_is_activated(user): return jsonify({'success':False}),403
    data=request.get_json(); task_id=data.get('task_id')
    if not task_id: return jsonify({'success':False}),400
    now=datetime.now(); today=now.date()
    if now.weekday()>=5 or now.hour<8 or now.hour>=23: return jsonify({'success':False}),400
    task=DailyTask.query.get(task_id)
    if not task or not task.actif or task.date!=today: return jsonify({'success':False}),400
    ut=UserTask.query.filter_by(user_id=user.id,task_id=task_id).first()
    if ut and ut.shared: return jsonify({'success':False}),400
    if ut: ut.shared=True; ut.shared_at=datetime.utcnow()
    else: db.session.add(UserTask(user_id=user.id,task_id=task_id,shared=True,shared_at=datetime.utcnow()))
    pub=Publicite.query.filter_by(produit_id=task.produit_id).first()
    if pub: pub.partages=(pub.partages or 0)+1
    db.session.commit(); sc,_=_prog(user.id,today)
    return jsonify({'success':True,'shared_count':sc,'total':TASK_COUNT,'completed':sc>=TASK_COUNT})

@app.route('/api/claim-task-reward',methods=['POST'])
def api_claim_task_reward():
    from app import get_logged_in_user
    user=get_logged_in_user()
    if not user: return jsonify({'success':False}),401
    today=datetime.now().date()
    if TaskReward.query.filter_by(user_id=user.id,date=today).first(): return jsonify({'success':False}),400
    sc,_=_prog(user.id,today)
    if sc<TASK_COUNT: return jsonify({'success':False}),400
    import random; m=random.randint(TASK_REWARD_MIN,TASK_REWARD_MAX)
    user.solde_parrainage=(user.solde_parrainage or 0)+m
    db.session.add(TaskReward(user_id=user.id,date=today,montant=m))
    db.session.commit()
    return jsonify({'success':True,'montant':int(m),'message':f'+{int(m)} FCFA 🎉'})

@app.route('/admin/taches',methods=['GET','POST'])
def admin_taches():
    from app import get_logged_in_user, Boutique, Produit
    user=get_logged_in_user()
    if not user or not user.is_admin: flash("Accès refusé.","danger"); return redirect(url_for('connexion_page'))
    today=date.today()
    if request.method=='POST':
        a=request.form.get('action')
        if a=='generate': _tasks(today); flash("OK","success")
        elif a=='toggle':
            t=DailyTask.query.get(request.form.get('task_id'))
            if t: t.actif=not t.actif; db.session.commit()
        elif a=='regenerate': DailyTask.query.filter_by(date=today).delete(); db.session.commit(); _tasks(today)
        return redirect(url_for('admin_taches'))
    tasks=DailyTask.query.filter_by(date=today).order_by(DailyTask.ordre).all()
    for t in tasks: t.share_count=UserTask.query.filter_by(task_id=t.id,shared=True).count()
    from sqlalchemy import func as f
    vs=db.session.query(Boutique.nom,f.count(UserTask.id).label('t')).join(Produit,Produit.boutique_id==Boutique.id).join(DailyTask,DailyTask.produit_id==Produit.id).join(UserTask,UserTask.task_id==DailyTask.id).filter(UserTask.shared==True).group_by(Boutique.id).order_by(f.count(UserTask.id).desc()).limit(20).all()
    return render_template('admin_taches.html',user=user,tasks=tasks,today=today,vendeur_stats=vs)

