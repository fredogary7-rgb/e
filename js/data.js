// Products data
const products = [
    {
        id: 1,
        name: "Smartphone Pro X",
        category: "Électronique",
        price: 799.99,
        image: "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400&h=300&fit=crop",
        rating: 4.5,
        description: "Le dernier smartphone de haute technologie avec un écran AMOLED 6.7 pouces, un processeur octa-core, 256GB de stockage et un appareil photo triple 48MP. Profitez d'une autonomie de batterie exceptionnelle et d'une charge rapide.",
        stock: 15
    },
    {
        id: 2,
        name: "Montre Connectée Elite",
        category: "Électronique",
        price: 299.99,
        image: "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400&h=300&fit=crop",
        rating: 4.8,
        description: "Montre connectée avec suivi de santé avancé, GPS intégré, résistance à l'eau 50m, et autonomie de 7 jours. Compatible iOS et Android.",
        stock: 23
    },
    {
        id: 3,
        name: "Casque Audio Premium",
        category: "Électronique",
        price: 199.99,
        image: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=300&fit=crop",
        rating: 4.6,
        description: "Casque sans fil avec réduction de bruit active, son haute fidélité, et confort exceptionnel pour une écoute prolongée. Autonomie de 30 heures.",
        stock: 18
    },
    {
        id: 4,
        name: "Sac à Dos Urbain",
        category: "Mode",
        price: 89.99,
        image: "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&h=300&fit=crop",
        rating: 4.3,
        description: "Sac à dos moderne avec compartiment pour ordinateur portable 15 pouces, poche anti-vol, et matériau imperméable. Parfait pour le travail ou les voyages.",
        stock: 32
    },
    {
        id: 5,
        name: "Lunettes de Soleil Polarized",
        category: "Mode",
        price: 129.99,
        image: "https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=400&h=300&fit=crop",
        rating: 4.4,
        description: "Lunettes de soleil avec verres polarisés, protection UV400, et monture en titane léger. Design élégant et confortable.",
        stock: 27
    },
    {
        id: 6,
        name: "Machine à Café Automatique",
        category: "Maison",
        price: 449.99,
        image: "https://images.unsplash.com/photo-1517668808822-9ebb02f2a0e6?w=400&h=300&fit=crop",
        rating: 4.7,
        description: "Machine à café entièrement automatique avec broyeur intégré, 15 programmes de boissons, et écran tactile. Préparation d'espresso, cappuccino, et plus.",
        stock: 9
    },
    {
        id: 7,
        name: "Lampe de Bureau LED",
        category: "Maison",
        price: 59.99,
        image: "https://images.unsplash.com/photo-1507473888900-52e1adad54cd?w=400&h=300&fit=crop",
        rating: 4.2,
        description: "Lampe de bureau LED avec intensité réglable, température de couleur ajustable, et port USB de charge. Design minimaliste et économique en énergie.",
        stock: 45
    },
    {
        id: 8,
        name: "Enceinte Bluetooth Portable",
        category: "Électronique",
        price: 79.99,
        image: "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400&h=300&fit=crop",
        rating: 4.5,
        description: "Enceinte Bluetooth compacte avec son 360°, résistance à l'eau IPX7, et autonomie de 12 heures. Parfaite pour les activités en plein air.",
        stock: 38
    },
    {
        id: 9,
        name: "Veste en Cuir Premium",
        category: "Mode",
        price: 249.99,
        image: "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=400&h=300&fit=crop",
        rating: 4.6,
        description: "Veste en cuir véritable avec coupe moderne, doublure en satin, et multiples poches. Disponible en plusieurs tailles et couleurs.",
        stock: 14
    },
    {
        id: 10,
        name: "Tablette Graphique Pro",
        category: "Électronique",
        price: 349.99,
        image: "https://images.unsplash.com/photo-1542751371-adc38448a05e?w=400&h=300&fit=crop",
        rating: 4.8,
        description: "Tablette graphique professionnelle avec stylet sans batterie, 8192 niveaux de pression, et surface active de 10x6 pouces. Idéale pour les artistes numériques.",
        stock: 11
    },
    {
        id: 11,
        name: "Plante Décorative Intérieure",
        category: "Maison",
        price: 34.99,
        image: "https://images.unsplash.com/photo-1485955900006-10f4d324d411?w=400&h=300&fit=crop",
        rating: 4.3,
        description: "Plante artificielle de haute qualité dans un pot en céramique moderne. Aucun entretien requis, parfait pour décorer intérieur.",
        stock: 52
    },
    {
        id: 12,
        name: "Chaussures de Sport Running",
        category: "Mode",
        price: 119.99,
        image: "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=300&fit=crop",
        rating: 4.7,
        description: "Chaussures de running légères avec amorti responsive, tige respirante, et semelle en caoutchouc durable. Confort optimal pour toutes vos courses.",
        stock: 29
    }
];

// Categories
const categories = [
    "Tous",
    "Électronique",
    "Mode",
    "Maison"
];

// Function to get products by category
function getProductsByCategory(category) {
    if (category === "Tous") {
        return products;
    }
    return products.filter(product => product.category === category);
}

// Function to get product by ID
function getProductById(id) {
    return products.find(product => product.id === parseInt(id));
}

// Function to get featured products (first 4)
function getFeaturedProducts() {
    return products.slice(0, 4);
}

// Function to search products
function searchProducts(query) {
    const lowerQuery = query.toLowerCase();
    return products.filter(product => 
        product.name.toLowerCase().includes(lowerQuery) ||
        product.category.toLowerCase().includes(lowerQuery) ||
        product.description.toLowerCase().includes(lowerQuery)
    );
}

// Function to sort products
function sortProducts(productsArray, sortBy) {
    const sorted = [...productsArray];
    switch(sortBy) {
        case 'price-low':
            return sorted.sort((a, b) => a.price - b.price);
        case 'price-high':
            return sorted.sort((a, b) => b.price - a.price);
        case 'name':
            return sorted.sort((a, b) => a.name.localeCompare(b.name));
        case 'rating':
            return sorted.sort((a, b) => b.rating - a.rating);
        default:
            return sorted;
    }
}