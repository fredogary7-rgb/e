"""
Script pour ajouter les routes du système de panier à app.py
"""

routes_panier = '''

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

'''

# Lire le fichier app.py existant
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Ajouter les routes à la fin du fichier
if "def cart_page():" not in content:
    content += routes_panier
    
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Routes du panier ajoutées avec succès !")
else:
    print("ℹ️ Les routes du panier existent déjà.")