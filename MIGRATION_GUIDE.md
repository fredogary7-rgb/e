# Guide de Migration - Séparation Vue Vendeur / Vue Client

## 📋 Résumé des modifications

Cette mise à jour sépare complètement la vue vendeur et la vue client pour une architecture de marketplace professionnelle.

### 🆕 Nouvelles fonctionnalités

1. **Page Produit Publique** (`/product/<slug>`)
   - URL unique avec slug pour chaque produit
   - Exemple: `https://flowtoken.uk/product/iphone-15-pro-max`
   - Visible par tous les clients (même sans compte)
   - Le vendeur voit des options supplémentaires (copier le lien, modifier)

2. **Page Boutique Publique** (`/shop/<username>`)
   - URL unique pour chaque boutique
   - Exemple: `https://flowtoken.uk/shop/john-doe`
   - Affiche tous les produits du vendeur
   - Informations de la boutique (logo, description, note)

3. **Système de Slugs**
   - Génération automatique de slugs URL-safe
   - Slugs uniques basés sur le nom du produit
   - Régénération automatique si le nom change

4. **Statistiques Vendeur**
   - Nombre de vues par produit
   - Nombre d'ajouts au panier
   - Bouton "Copier le lien" pour partager

5. **Sécurité Renforcée**
   - Seul le propriétaire peut modifier/supprimer
   - Vérification côté serveur des permissions

---

## 🚀 Étapes de Migration

### Étape 1: Mettre à jour la base de données

Exécutez Flask-Migrate pour ajouter les nouvelles colonnes:

```bash
cd e
flask db migrate -m "Add slug and ajouts_panier to produits"
flask db upgrade
```

### Étape 2: Générer les slugs pour les produits existants

Exécutez le script de migration:

```bash
python migrate_slug.py
```

Ce script va:
- Parcourir tous les produits sans slug
- Générer un slug unique basé sur le nom
- Sauvegarder dans la base de données

### Étape 3: Redémarrer l'application

```bash
# En développement
python app.py

# Ou avec gunicorn
gunicorn app:app
```

---

## 📱 URLs Disponibles

### Pour les Clients

| URL | Description |
|-----|-------------|
| `/product/<slug>` | Page produit publique (ex: `/product/iphone-15`) |
| `/shop/<username>` | Page boutique publique (ex: `/shop/john`) |
| `/produits` | Liste de tous les produits |
| `/boutiques` | Liste de toutes les boutiques |

### Pour les Vendeurs

| URL | Description |
|-----|-------------|
| `/boutique/creer` | Créer une nouvelle boutique |
| `/boutique/<id>` | Gérer sa boutique |
| `/boutique/<id>/configurer` | Modifier les infos de la boutique |
| `/boutique/<id>/produit/ajouter` | Ajouter un produit |
| `/boutique/<id>/produit/<id>/modifier` | Modifier un produit |

---

## 🔒 Sécurité

### Qui peut modifier un produit?
- ✅ Le propriétaire de la boutique
- ❌ Les autres utilisateurs
- ❌ Les visiteurs non connectés

### Qui peut voir la page vendeur?
- La page `/produit/<id>` (ancienne URL) montre les options vendeur
- La page `/product/<slug>` (nouvelle URL) est publique
- Si le vendeur visite `/product/<slug>`, il voit un badge "Votre produit"

---

## 📊 Nouvelles Colonnes en Base de Données

### Table `produits`

| Colonne | Type | Description |
|---------|------|-------------|
| `slug` | VARCHAR(100) | Slug unique pour l'URL publique |
| `ajouts_panier` | INTEGER | Nombre d'ajouts au panier |

---

## 🧪 Tests

Après la migration, testez:

1. **Créer un nouveau produit**
   - Le slug doit être généré automatiquement
   - L'URL publique doit fonctionner

2. **Modifier le nom d'un produit**
   - Le slug doit être régénéré
   - L'ancienne URL ne doit plus fonctionner

3. **Visiter une page produit publique**
   - Les clients voient: image, description, prix, boutons
   - Le vendeur voit en plus: badge "Votre produit", bouton "Copier le lien"

4. **Visiter une page boutique publique**
   - Tous les produits du vendeur doivent s'afficher
   - Les informations de la boutique doivent être visibles

---

## 🐛 Dépannage

### Le slug n'est pas généré
Vérifiez que la méthode `generate_slug()` est appelée lors de la création:
```python
nouveau_produit.slug = nouveau_produit.generate_slug()
```

### Erreur de slug dupliqué
Le système gère automatiquement les doublons en ajoutant un suffixe numérique.

### Anciens produits sans slug
Exécutez le script de migration: `python migrate_slug.py`

---

## 📝 Notes

- Les slugs sont en minuscules, sans accents, avec des tirets
- Longueur maximale: 80 caractères
- Exemple: "iPhone 15 Pro Max" → "iphone-15-pro-max"