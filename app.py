import time
import requests
import os
import re
import sys
import uuid
import unicodedata
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

os.makedirs(UPLOAD_FOLDER_PROFILE, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_APPS, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_VLOGS, exist_ok=True)

app.config['UPLOAD_FOLDER_PROFILE'] = UPLOAD_FOLDER_PROFILE
app.config['UPLOAD_FOLDER_VLOGS'] = UPLOAD_FOLDER_VLOGS
app.config['UPLOAD_FOLDER_APPS'] = UPLOAD_FOLDER_APPS
app.config['UPLOAD_FOLDER'] = 'static/uploads'

def allowed_file(filename):
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

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ─── FLASK-LOGIN CONFIG ─────────────────────────────────
from flask_login import LoginManager, UserMixin, current_user

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "connexion_page"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_request
def load_logged_in_user():
    from flask import g
    user_id = session.get("user_id")
    if user_id:
        try:
            g.logged = User.query.get(user_id)
        except:
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
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30), unique=True, nullable=False, index=True)
    password = db.Column(db.String(300), nullable=False)
    last_play_date = db.Column(db.DateTime, nullable=True)
    parrain = db.Column(db.String(50), nullable=True)
    has_played_slot = db.Column(db.Boolean, default=False)
    downlines = db.relationship('User', primaryjoin="User.username == foreign(User.parrain)", remote_side="User.parrain", lazy='dynamic')
    commission_total = db.Column(db.Float, default=0.0)
    has_seen_pay_ok = db.Column(db.Boolean, default=False)
    ip_address = db.Column(db.String(45))
    wallet_country = db.Column(db.String(50))
    wallet_operator = db.Column(db.String(50))
    wallet_number = db.Column(db.String(30))
    bonus = db.Column(db.Float, default=0.0)
    chances_bridge = db.Column(db.Integer, default=3)
    derniere_maj_chances = db.Column(db.Date)
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
    has_free_attempt = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    pin_code = db.Column(db.String(255), nullable=True)
    has_frog_attempt = db.Column(db.Boolean, default=True)
    frog_game_done = db.Column(db.Boolean, default=False)
    country = db.Column(db.String(50), default='')
    has_played_this_round = db.Column(db.Boolean, default=False)
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
    game_played_count = db.Column(db.Integer, default=0)
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


class Depot(db.Model):
    __tablename__ = "depot"
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(50), db.ForeignKey("user.username", ondelete="CASCADE"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=True)
    user = db.relationship("User", backref="depots", foreign_keys=[user_id])
    phone = db.Column(db.String(30), nullable=False)
    operator = db.Column(db.String(50), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    montant = db.Column(db.Float, nullable=False)
    reference = db.Column(db.String(200), nullable=True)
    statut = db.Column(db.String(20), default="pending")
    email = db.Column(db.String(120), nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)


class Retrait(db.Model):
    __tablename__ = "retrait"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    phone = db.Column(db.String(30), nullable=False)
    montant = db.Column(db.Float, nullable=False)
    statut = db.Column(db.String(20), default="en_attente")
    date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_method = db.Column(db.String(50))
    pays = db.Column(db.String(50), nullable=True)
    frais = db.Column(db.Float, default=0.0)


class ChannelMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=True)
    media_url = db.Column(db.String(255), nullable=True)
    media_type = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    reactions = db.Column(db.JSON, default=lambda: {"🔥": 0, "🚀": 0, "❤️": 0})


class ChannelSub(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


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