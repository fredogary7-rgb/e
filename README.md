# E-Shop - Application E-commerce

Une application e-commerce moderne et responsive développée en HTML, CSS et JavaScript pur.

## 🚀 Fonctionnalités

- **Catalogue de produits** - Présentation des produits avec images, descriptions et prix
- **Filtrage et recherche** - Filtrer par catégorie, trier par prix/nom/note, et recherche textuelle
- **Panier d'achat** - Ajout/suppression de produits, gestion des quantités
- **Persistance des données** - Le panier est sauvegardé dans le localStorage
- **Design responsive** - Adapté à tous les écrans (mobile, tablette, desktop)
- **Page produit détaillée** - Description complète, sélection de quantité
- **Formulaire de contact** - Page de contact fonctionnelle

## 📁 Structure du projet

```
e/
├── index.html          # Page d'accueil
├── products.html       # Page catalogue produits
├── product.html        # Page détail produit
├── cart.html           # Page panier
├── contact.html        # Page contact
├── css/
│   └── style.css       # Feuille de style principale
├── js/
│   ├── data.js         # Données des produits
│   ├── cart.js         # Gestion du panier
│   └── main.js         # Scripts principaux
└── README.md           # Documentation
```

## 🛠️ Installation et utilisation

1. **Cloner ou télécharger le projet**
   ```bash
   git clone https://github.com/fredogary7-rgb/e.git
   cd e
   ```

2. **Ouvrir l'application**
   - Ouvrez simplement `index.html` dans votre navigateur
   - Ou utilisez un serveur local (recommandé):
     ```bash
     # Avec Python
     python -m http.server 8000
     
     # Avec Node.js
     npx serve
     ```

3. **Accéder à l'application**
   - Ouvrez votre navigateur à `http://localhost:8000`

## 🎨 Personnalisation

### Modifier les produits
Éditez le fichier `js/data.js` pour ajouter, modifier ou supprimer des produits:

```javascript
const products = [
    {
        id: 1,
        name: "Nom du produit",
        category: "Catégorie",
        price: 99.99,
        image: "url_de_l_image",
        rating: 4.5,
        description: "Description du produit",
        stock: 10
    },
    // ... autres produits
];
```

### Modifier les couleurs
Les variables CSS sont définies dans `css/style.css`:

```css
:root {
    --primary-color: #2563eb;
    --secondary-color: #1e40af;
    --accent-color: #f59e0b;
    /* ... autres variables */
}
```

## 🌟 Fonctionnalités détaillées

### Page d'accueil
- Bannière hero avec appel à l'action
- Produits en vedette
- Section des avantages (livraison, paiement sécurisé, etc.)

### Page Produits
- Grille de produits responsive
- Filtres par catégorie
- Tri par prix, nom, note
- Recherche textuelle en temps réel

### Page Panier
- Gestion des quantités
- Calcul automatique du total
- Livraison gratuite à partir de 50€
- Simulation de commande

### Page Contact
- Formulaire de contact
- Informations de contact
- Horaires d'ouverture

## 📱 Responsive Design

L'application est entièrement responsive et s'adapte à:
- 📱 Mobiles (< 480px)
- 📱 Tablettes (480px - 768px)
- 💻 Desktops (> 768px)

## 🔧 Technologies utilisées

- **HTML5** - Structure sémantique
- **CSS3** - Styles modernes avec variables CSS, Flexbox, Grid
- **JavaScript (ES6+)** - Fonctionnalités interactives
- **Font Awesome** - Icônes
- **Unsplash** - Images de produits (via URL)

## 📝 Notes

- Les images des produits proviennent d'Unsplash (URL externes)
- Le panier est stocké dans le localStorage du navigateur
- Le paiement est simulé (pas de véritable traitement de paiement)

## 🤝 Contribution

Les contributions sont les bienvenues! N'hésitez pas à:
1. Fork le projet
2. Créer une branche de fonctionnalité
3. Soumettre une pull request

## 📄 Licence

Ce projet est open source et disponible sous licence MIT.

---

Développé avec ❤️ par E-Shop Team