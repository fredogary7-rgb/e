// Cart Management System
class Cart {
    constructor() {
        this.items = this.loadCart();
    }

    // Load cart from localStorage
    loadCart() {
        const savedCart = localStorage.getItem('eshop_cart');
        return savedCart ? JSON.parse(savedCart) : [];
    }

    // Save cart to localStorage
    saveCart() {
        localStorage.setItem('eshop_cart', JSON.stringify(this.items));
        this.updateCartCount();
    }

    // Add item to cart
    addItem(productId, quantity = 1) {
        const product = getProductById(productId);
        if (!product) return false;

        const existingItem = this.items.find(item => item.id === productId);
        
        if (existingItem) {
            existingItem.quantity += quantity;
        } else {
            this.items.push({
                id: product.id,
                name: product.name,
                price: product.price,
                image: product.image,
                quantity: quantity
            });
        }

        this.saveCart();
        return true;
    }

    // Remove item from cart
    removeItem(productId) {
        this.items = this.items.filter(item => item.id !== productId);
        this.saveCart();
    }

    // Update item quantity
    updateQuantity(productId, quantity) {
        const item = this.items.find(item => item.id === productId);
        if (item) {
            if (quantity <= 0) {
                this.removeItem(productId);
            } else {
                item.quantity = quantity;
                this.saveCart();
            }
        }
    }

    // Get cart total
    getTotal() {
        return this.items.reduce((total, item) => total + (item.price * item.quantity), 0);
    }

    // Get cart items count
    getItemCount() {
        return this.items.reduce((count, item) => count + item.quantity, 0);
    }

    // Clear cart
    clear() {
        this.items = [];
        this.saveCart();
    }

    // Update cart count in navigation
    updateCartCount() {
        const cartCountElements = document.querySelectorAll('.cart-count');
        const count = this.getItemCount();
        cartCountElements.forEach(element => {
            element.textContent = count;
        });
    }

    // Get cart items with full product details
    getCartItems() {
        return this.items.map(item => {
            const product = getProductById(item.id);
            return {
                ...item,
                category: product ? product.category : '',
                stock: product ? product.stock : 0
            };
        });
    }
}

// Initialize cart instance
const cart = new Cart();

// Update cart count on page load
document.addEventListener('DOMContentLoaded', () => {
    cart.updateCartCount();
});

// Function to add to cart with animation
function addToCart(productId, buttonElement) {
    const success = cart.addItem(productId);
    
    if (success) {
        // Button animation
        if (buttonElement) {
            const originalText = buttonElement.innerHTML;
            buttonElement.innerHTML = '<i class="fas fa-check"></i> Ajouté!';
            buttonElement.style.backgroundColor = '#10b981';
            
            setTimeout(() => {
                buttonElement.innerHTML = originalText;
                buttonElement.style.backgroundColor = '';
            }, 1500);
        }
        
        // Show toast notification
        showToast('Produit ajouté au panier!');
    }
}

// Function to show toast notification
function showToast(message, type = 'success') {
    // Remove existing toast
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }

    // Create new toast
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
        ${message}
    `;
    document.body.appendChild(toast);

    // Show toast
    setTimeout(() => toast.classList.add('show'), 10);

    // Hide toast after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Function to render cart items
function renderCartItems() {
    const cartItemsContainer = document.getElementById('cart-items-container');
    const cartSummaryContainer = document.getElementById('cart-summary-container');
    
    if (!cartItemsContainer) return;

    const cartItems = cart.getCartItems();

    if (cartItems.length === 0) {
        cartItemsContainer.innerHTML = `
            <div class="empty-cart">
                <i class="fas fa-shopping-cart"></i>
                <h2>Votre panier est vide</h2>
                <p>Découvrez nos produits et ajoutez-les à votre panier</p>
                <a href="products.html" class="btn btn-primary">Voir les produits</a>
            </div>
        `;
        if (cartSummaryContainer) {
            cartSummaryContainer.style.display = 'none';
        }
        return;
    }

    // Render cart header
    let cartHTML = `
        <div class="cart-header">
            <span>Produit</span>
            <span>Prix</span>
            <span>Quantité</span>
            <span>Sous-total</span>
            <span></span>
        </div>
    `;

    // Render cart items
    cartItems.forEach(item => {
        const subtotal = (item.price * item.quantity).toFixed(2);
        cartHTML += `
            <div class="cart-item" data-id="${item.id}">
                <div class="cart-item-info">
                    <img src="${item.image}" alt="${item.name}" class="cart-item-image">
                    <span class="cart-item-name">${item.name}</span>
                </div>
                <span class="cart-item-price">${item.price.toFixed(2)}€</span>
                <div class="quantity-control">
                    <button class="quantity-btn" onclick="updateCartQuantity(${item.id}, ${item.quantity - 1})">-</button>
                    <span class="quantity-value">${item.quantity}</span>
                    <button class="quantity-btn" onclick="updateCartQuantity(${item.id}, ${item.quantity + 1})">+</button>
                </div>
                <span class="cart-item-subtotal">${subtotal}€</span>
                <button class="remove-btn" onclick="removeFromCart(${item.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
    });

    cartItemsContainer.innerHTML = cartHTML;

    // Render cart summary
    if (cartSummaryContainer) {
        const total = cart.getTotal().toFixed(2);
        const shipping = total > 50 ? 0 : 5.99;
        const grandTotal = (parseFloat(total) + shipping).toFixed(2);

        cartSummaryContainer.innerHTML = `
            <h3>Récapitulatif</h3>
            <div class="summary-row">
                <span>Sous-total</span>
                <span>${total}€</span>
            </div>
            <div class="summary-row">
                <span>Livraison</span>
                <span>${shipping === 0 ? 'Gratuite' : shipping + '€'}</span>
            </div>
            ${total > 50 ? '<p style="color: #10b981; font-size: 0.9rem;">✓ Livraison gratuite!</p>' : '<p style="color: #6b7280; font-size: 0.9rem;">Livraison gratuite à partir de 50€</p>'}
            <div class="summary-row total">
                <span>Total</span>
                <span>${grandTotal}€</span>
            </div>
            <button class="btn btn-primary" onclick="checkout()">
                <i class="fas fa-lock"></i> Passer à la caisse
            </button>
            <button class="btn btn-outline" onclick="clearCart()">
                Vider le panier
            </button>
        `;
    }
}

// Function to update cart quantity
function updateCartQuantity(productId, quantity) {
    cart.updateQuantity(productId, quantity);
    renderCartItems();
}

// Function to remove item from cart
function removeFromCart(productId) {
    cart.removeItem(productId);
    renderCartItems();
    showToast('Produit retiré du panier');
}

// Function to clear cart
function clearCart() {
    if (confirm('Êtes-vous sûr de vouloir vider votre panier?')) {
        cart.clear();
        renderCartItems();
        showToast('Panier vidé');
    }
}

// Function to proceed to checkout
function checkout() {
    const cartItems = cart.getCartItems();
    if (cartItems.length === 0) {
        showToast('Votre panier est vide', 'error');
        return;
    }

    // Simulate checkout process
    const orderSummary = cartItems.map(item => 
        `${item.name} x${item.quantity} - ${(item.price * item.quantity).toFixed(2)}€`
    ).join('\n');

    const total = cart.getTotal().toFixed(2);
    const shipping = total > 50 ? 0 : 5.99;
    const grandTotal = (parseFloat(total) + shipping).toFixed(2);

    alert(`
        COMMANDE SIMULÉE
        
        Détails de la commande:
        ${orderSummary}
        
        Sous-total: ${total}€
        Livraison: ${shipping === 0 ? 'Gratuite' : shipping + '€'}
        Total: ${grandTotal}€
        
        Merci pour votre achat!
    `);

    cart.clear();
    renderCartItems();
    showToast('Commande validée avec succès!');
}