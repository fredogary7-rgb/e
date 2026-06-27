"""Script pour créer l'utilisateur admin"""
import sys
sys.path.insert(0, '.')

from app import app, db, User
from werkzeug.security import generate_password_hash

def create_admin():
    with app.app_context():
        # Vérifier si l'admin existe déjà
        admin = User.query.filter_by(username="admin").first()
        
        if admin:
            print("⚠️ L'utilisateur admin existe déjà !")
            print(f"   Username: admin")
            print(f"   Email: {admin.email}")
            print(f"   Phone: {admin.phone}")
            return
        
        # Créer l'admin
        admin = User(
            username="admin",
            email="admin@novatrade.cc",
            phone="0000000000",
            password=generate_password_hash("admin123nova"),
            is_admin=True,
            premier_depot=True
        )
        
        db.session.add(admin)
        db.session.commit()
        
        print("=" * 50)
        print("✅ UTILISATEUR ADMIN CRÉÉ AVEC SUCCÈS !")
        print("=" * 50)
        print()
        print("📋 IDENTIFIANTS DE CONNEXION :")
        print("   Username: admin")
        print("   Mot de passe: admin123")
        print()
        print("🔗 LIENS ADMIN :")
        print("   Page de connexion admin: /admin/finance")
        print("   Page dépôts: /admin/deposits")
        print()
        print("⚠️ IMPORTANT : Changez le mot de passe après la première connexion !")
        print("=" * 50)

if __name__ == "__main__":
    create_admin()