from app import app, db, User

# Utilisateurs à conserver
KEEP_USERS = [
    "thom14",
    "nina14",
    "thom",
    "youssoufa118",
    "test",
]

with app.app_context():
    users_to_delete = User.query.filter(~User.username.in_(KEEP_USERS)).all()

    print(f"{len(users_to_delete)} utilisateur(s) seront supprimés.")

    for user in users_to_delete:
        print(f"Suppression : {user.username}")
        db.session.delete(user)

    db.session.commit()

    print("✅ Suppression terminée.")
