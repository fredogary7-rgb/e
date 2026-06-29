with open('c:/Users/user/Documents/d/e/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = """    # Cas spécial : Premier jeu après inscription
    if not user.last_play_date and not no_rounds_left and not is_blocked_500:
        can_play = True

    return render_template(
        \"dashboard.html\",
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
    )"""

new = """    # Cas spécial : Premier jeu après inscription
    if not user.last_play_date and not no_rounds_left and not is_blocked_500:
        can_play = True

    # --- PRODUITS DES VENDEURS (carousel dashboard) ---
    produits_recents = Produit.query.filter_by(est_actif=True).order_by(Produit.date_creation.desc()).limit(20).all()

    return render_template(
        \"dashboard.html\",
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
        produits_recents=produits_recents
    )"""

if old in content:
    content = content.replace(old, new)
    with open('c:/Users/user/Documents/d/e/app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - remplacement effectue avec succes')
else:
    print('ERREUR - texte non trouve')
    # Debug: chercher le texte approximativement
    idx = content.find("Cas spécial : Premier jeu")
    if idx >= 0:
        print(repr(content[idx:idx+600]))
