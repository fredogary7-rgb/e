// Main JavaScript file

// Mobile Navigation Toggle
document.addEventListener('DOMContentLoaded', () => {
    const burger = document.querySelector('.burger');
    const nav = document.querySelector('.nav-links');
    const navLinks = document.querySelectorAll('.nav-links li');

    if (burger && nav) {
        burger.addEventListener('click', () => {
            // Toggle Nav
            nav.classList.toggle('active');
            
            // Burger Animation
            burger.classList.toggle('active');
        });

        // Close menu when clicking on a link
        navLinks.forEach(link => {
            link.addEventListener('click', () => {
                nav.classList.remove('active');
                burger.classList.remove('active');
            });
        });
    }

    // Initialize page-specific functionality
    initHomePage();
    initProductsPage();
    initCartPage();
    initContactPage();
    initProductDetailPage();
});

// Home Page Functions
function initHomePage() {
    const featuredProductsContainer = document.getElementById('featured-products');
    
    if (featuredProductsContainer) {
        const featuredProducts = getFeaturedProducts();
        renderProducts(featuredProducts, featuredProductsContainer);
    }
}

// Products Page Functions
function initProductsPage() {
    const productsContainer = document.getElementById('products-container');
    const categoryFilter = document.getElementById('category-filter');
    const sortFilter = document.getElementById('sort-filter');
    const searchInput = document.getElementById('search-input');

    if (productsContainer) {
        // Initial render
        renderProducts(products, productsContainer);

        // Category filter
        if (categoryFilter) {
            categoryFilter.addEventListener('change', () => {
                filterAndSortProducts();
            });
        }

        // Sort filter
        if (sortFilter) {
            sortFilter.addEventListener('change', () => {
                filterAndSortProducts();
            });
        }

        // Search
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                filterAndSortProducts();
            });
        }
    }
}

function filterAndSortProducts() {
    const categoryFilter = document.getElementById('category-filter');
    const sortFilter = document.getElementById('sort-filter');
    const searchInput = document.getElementById('search-input');
    const productsContainer = document.getElementById('products-container');

    if (!productsContainer) return;

    let filteredProducts = [...products];

    // Apply category filter
    if (categoryFilter && categoryFilter.value !== 'Tous') {
        filteredProducts = filteredProducts.filter(p => p.category === categoryFilter.value);
    }

    // Apply search
    if (searchInput && searchInput.value.trim()) {
        const query = searchInput.value.trim().toLowerCase();
        filteredProducts = filteredProducts.filter(p => 
            p.name.toLowerCase().includes(query) ||
            p.category.toLowerCase().includes(query) ||
            p.description.toLowerCase().includes(query)
        );
    }

    // Apply sort
    if (sortFilter) {
        switch(sortFilter.value) {
            case 'price-low':
                filteredProducts.sort((a, b) => a.price - b.price);
                break;
            case 'price-high':
                filteredProducts.sort((a, b) => b.price - a.price);
                break;
            case 'name':
                filteredProducts.sort((a, b) => a.name.localeCompare(b.name));
                break;
            case 'rating':
                filteredProducts.sort((a, b) => b.rating - a.rating);
                break;
        }
    }

    renderProducts(filteredProducts, productsContainer);
}

// Render Products
function renderProducts(productsArray, container) {
    if (productsArray.length === 0) {
        container.innerHTML = `
            <div class="empty-products" style="grid-column: 1 / -1; text-align: center; padding: 60px 20px;">
                <i class="fas fa-search" style="font-size: 3rem; color: #6b7280; margin-bottom: 20px;"></i>
                <h3 style="margin-bottom: 10px;">Aucun produit trouvé</h3>
                <p style="color: #6b7280;">Essayez de modifier vos filtres ou votre recherche</p>
            </div>
        `;
        return;
    }

    container.innerHTML = productsArray.map(product => `
        <div class="product-card" data-id="${product.id}">
            <a href="product.html?id=${product.id}">
                <img src="${product.image}" alt="${product.name}" class="product-image">
            </a>
            <div class="product-info">
                <span class="product-category">${product.category}</span>
                <h3 class="product-name">
                    <a href="product.html?id=${product.id}">${product.name}</a>
                </h3>
                <div class="product-rating">
                    ${generateStars(product.rating)}
                    <span style="color: #6b7280; font-size: 0.9rem;">(${product.rating})</span>
                </div>
                <p class="product-price">${product.price.toFixed(2)}€</p>
                <button class="btn btn-primary" onclick="addToCart(${product.id}, this)">
                    <i class="fas fa-shopping-cart"></i> Ajouter au panier
                </button>
            </div>
        </div>
    `).join('');
}

// Generate Star Rating
function generateStars(rating) {
    let stars = '';
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;

    for (let i = 0; i < fullStars; i++) {
        stars += '<i class="fas fa-star"></i>';
    }
    if (hasHalfStar) {
        stars += '<i class="fas fa-star-half-alt"></i>';
    }
    const emptyStars = 5 - Math.ceil(rating);
    for (let i = 0; i < emptyStars; i++) {
        stars += '<i class="far fa-star"></i>';
    }

    return stars;
}

// Cart Page Functions
function initCartPage() {
    const cartPage = document.getElementById('cart-page');
    
    if (cartPage) {
        renderCartItems();
    }
}

// Contact Page Functions
function initContactPage() {
    const contactForm = document.getElementById('contact-form');
    
    if (contactForm) {
        contactForm.addEventListener('submit', (e) => {
            e.preventDefault();
            
            const name = document.getElementById('name').value;
            const email = document.getElementById('email').value;
            const subject = document.getElementById('subject').value;
            const message = document.getElementById('message').value;

            // Simulate form submission
            setTimeout(() => {
                showToast('Message envoyé avec succès! Nous vous répondrons bientôt.');
                contactForm.reset();
            }, 1000);
        });
    }
}

// Product Detail Page Functions
function initProductDetailPage() {
    const productDetailContainer = document.getElementById('product-detail-container');
    
    if (productDetailContainer) {
        // Get product ID from URL
        const urlParams = new URLSearchParams(window.location.search);
        const productId = urlParams.get('id');

        if (productId) {
            const product = getProductById(productId);
            
            if (product) {
                renderProductDetail(product, productDetailContainer);
            } else {
                productDetailContainer.innerHTML = `
                    <div class="empty-products" style="grid-column: 1 / -1; text-align: center; padding: 60px 20px;">
                        <i class="fas fa-exclamation-circle" style="font-size: 3rem; color: #6b7280; margin-bottom: 20px;"></i>
                        <h3 style="margin-bottom: 10px;">Produit non trouvé</h3>
                        <p style="color: #6b7280; margin-bottom: 20px;">Le produit que vous recherchez n'existe pas</p>
                        <a href="products.html" class="btn btn-primary">Voir les produits</a>
                    </div>
                `;
            }
        }
    }
}

function renderProductDetail(product, container) {
    document.title = `${product.name} - E-Shop`;

    container.innerHTML = `
        <div class="product-detail-image">
            <img src="${product.image}" alt="${product.name}">
        </div>
        <div class="product-detail-info">
            <span class="product-category">${product.category}</span>
            <h1>${product.name}</h1>
            <div class="product-rating">
                ${generateStars(product.rating)}
                <span style="color: #6b7280;">(${product.rating})</span>
            </div>
            <p class="product-detail-price">${product.price.toFixed(2)}€</p>
            <p class="product-description">${product.description}</p>
            <div class="product-quantity">
                <label>Quantité:</label>
                <div class="quantity-control" style="display: inline-flex; align-items: center; gap: 10px;">
                    <button class="quantity-btn" onclick="decreaseDetailQuantity()">-</button>
                    <span class="quantity-value" id="detail-quantity">1</span>
                    <button class="quantity-btn" onclick="increaseDetailQuantity()">+</button>
                </div>
            </div>
            <div style="display: flex; gap: 15px;">
                <button class="btn btn-primary" onclick="addToCartFromDetail(${product.id})" style="flex: 1;">
                    <i class="fas fa-shopping-cart"></i> Ajouter au panier
                </button>
                <button class="btn btn-secondary" onclick="buyNow(${product.id})" style="flex: 1;">
                    <i class="fas fa-bolt"></i> Acheter maintenant
                </button>
            </div>
            <div style="margin-top: 30px; padding: 20px; background-color: #f3f4f6; border-radius: 8px;">
                <p><i class="fas fa-truck" style="color: #2563eb; margin-right: 10px;"></i> Livraison gratuite à partir de 50€</p>
                <p style="margin-top: 10px;"><i class="fas fa-undo" style="color: #2563eb; margin-right: 10px;"></i> Retours gratuits sous 30 jours</p>
                <p style="margin-top: 10px;"><i class="fas fa-shield-alt" style="color: #2563eb; margin-right: 10px;"></i> Garantie 2 ans</p>
            </div>
        </div>
    `;
}

function decreaseDetailQuantity() {
    const quantityElement = document.getElementById('detail-quantity');
    let quantity = parseInt(quantityElement.textContent);
    if (quantity > 1) {
        quantityElement.textContent = quantity - 1;
    }
}

function increaseDetailQuantity() {
    const quantityElement = document.getElementById('detail-quantity');
    let quantity = parseInt(quantityElement.textContent);
    quantityElement.textContent = quantity + 1;
}

function addToCartFromDetail(productId) {
    const quantity = parseInt(document.getElementById('detail-quantity').textContent);
    for (let i = 0; i < quantity; i++) {
        cart.addItem(productId);
    }
    showToast(`${quantity} produit(s) ajouté(s) au panier!`);
}

function buyNow(productId) {
    const quantity = parseInt(document.getElementById('detail-quantity').textContent);
    cart.addItem(productId, quantity);
    window.location.href = 'cart.html';
}

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});