from app import app, db, User

username = "test"

with app.app_context():

    user = User.query.filter_by(username=username).first()

    if not user:
        print("❌ Utilisateur introuvable")
    else:
        user.premier_depot = True
        db.session.commit()
        print(f"✅ premier_depot = True pour {user.username}")
