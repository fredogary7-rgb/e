/**
 * NectarPro Service Worker
 * PWA avancée avec :
 *   - Cache intelligent (CSS, JS, images, polices, pages)
 *   - Mode offline
 *   - Mise à jour automatique
 *   - Compatibilité Web Push API (VAPID) - préparée
 *
 * Version: 1.0.0
 */

const CACHE_NAME = 'nectarpro-v1';
const RUNTIME_CACHE = 'nectarpro-runtime-v1';

// Ressources à mettre en cache immédiatement à l'installation
const PRECACHE_ASSETS = [
    '/',
    '/offline',
    '/static/manifest.json',
    '/static/images/net.jpg',
    '/static/images/pwa/icon-192.png',
    '/static/images/pwa/icon-512.png',
    '/static/css/global_modern.css',
    '/static/css/style.css',
    '/static/js/data.js',
    '/static/js/cart.js',
    '/static/js/main.js',
    '/js/cart.js',
    '/js/data.js',
    '/js/main.js',
    '/css/global_modern.css',
    '/css/style.css',
    // Polices Google (fallback hors ligne sur la page offline)
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css',
];

// Pages à mettre en cache réseau d'abord (Network First)
const NETWORK_FIRST_PATTERNS = [
    '/dashboard',
    '/market',
    '/retrait',
    '/revenus',
    '/profile',
    '/boutique',
    '/products',
    '/publicites',
    '/videos',
    '/taches',
    '/mes-retraits',
    '/team',
    '/shop',
    '/checkout',
    '/cart',
    '/settings',
];

// Extensions à mettre en cache (Stale While Revalidate)
const SWR_EXTENSIONS = [
    '.css',
    '.js',
    '.png',
    '.jpg',
    '.jpeg',
    '.gif',
    '.svg',
    '.webp',
    '.woff',
    '.woff2',
    '.mp4',
    '.webm',
];

// ============================================================
// INSTALLATION
// ============================================================
self.addEventListener('install', (event) => {
    console.log('[SW NectarPro] Installation...');

    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[SW NectarPro] Mise en cache des ressources');
                return cache.addAll(PRECACHE_ASSETS);
            })
            .then(() => {
                console.log('[SW NectarPro] Skip waiting');
                return self.skipWaiting();
            })
            .catch((err) => {
                console.error('[SW NectarPro] Erreur installation:', err);
            })
    );
});

// ============================================================
// ACTIVATION - Nettoyage des anciens caches
// ============================================================
self.addEventListener('activate', (event) => {
    console.log('[SW NectarPro] Activation...');

    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => {
                        return name !== CACHE_NAME && name !== RUNTIME_CACHE;
                    })
                    .map((name) => {
                        console.log('[SW NectarPro] Suppression ancien cache:', name);
                        return caches.delete(name);
                    })
            );
        }).then(() => {
            console.log('[SW NectarPro] Prêt - prend le contrôle');
            return self.clients.claim();
        })
    );
});

// ============================================================
// STRATÉGIES DE CACHE
// ============================================================

/**
 * Cache First - Pour les assets statiques
 * Sert du cache, sinon va chercher le réseau et met en cache
 */
async function cacheFirst(request) {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
        return cachedResponse;
    }
    try {
        const networkResponse = await fetch(request);
        if (networkResponse && networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        // Si c'est une page HTML, retourne la page offline
        if (request.headers.get('Accept') && request.headers.get('Accept').includes('text/html')) {
            const offlineCache = await caches.match('/offline');
            if (offlineCache) return offlineCache;
        }
        throw error;
    }
}

/**
 * Network First - Pour les pages dynamiques (dashboard, etc.)
 * Essaie le réseau d'abord, fallback sur le cache, puis page offline
 */
async function networkFirst(request) {
    try {
        const networkResponse = await fetch(request);
        if (networkResponse && networkResponse.ok) {
            const cache = await caches.open(RUNTIME_CACHE);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        // Fallback offline
        const offlineCache = await caches.match('/offline');
        if (offlineCache) return offlineCache;
        throw error;
    }
}

/**
 * Stale While Revalidate - Pour les assets (CSS, JS, images)
 * Sert du cache immédiatement, puis met à jour en arrière-plan
 */
async function staleWhileRevalidate(request) {
    const cache = await caches.open(RUNTIME_CACHE);
    const cachedResponse = await cache.match(request);

    const fetchPromise = fetch(request)
        .then((networkResponse) => {
            if (networkResponse && networkResponse.ok) {
                cache.put(request, networkResponse.clone());
            }
            return networkResponse;
        })
        .catch(() => {
            return cachedResponse;
        });

    return cachedResponse || fetchPromise;
}

// ============================================================
// ROUTAGE DES REQUÊTES
// ============================================================
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Ignorer les requêtes non-GET
    if (request.method !== 'GET') return;

    // Ignorer les requêtes vers l'API (SoleasPay, etc.)
    if (url.pathname.startsWith('/api/')) return;
    if (url.pathname.startsWith('/admin/')) return;
    if (url.pathname.startsWith('/webhook')) return;

    // Ignorer les requêtes externes (sauf CDN connus)
    if (url.origin !== self.location.origin) {
        const knownCDNs = [
            'cdnjs.cloudflare.com',
            'fonts.googleapis.com',
            'fonts.gstatic.com',
            'cdn.jsdelivr.net',
        ];
        if (!knownCDNs.some(cdn => url.hostname.includes(cdn))) {
            return;
        }
    }

    // Stratégie : Network First pour les pages HTML
    const isHTML = request.headers.get('Accept') && request.headers.get('Accept').includes('text/html');
    const isPage = NETWORK_FIRST_PATTERNS.some(pattern => url.pathname.startsWith(pattern));

    if (isHTML || isPage) {
        event.respondWith(networkFirst(request));
        return;
    }

    // Stratégie : Stale While Revalidate pour les assets statiques
    const isAsset = SWR_EXTENSIONS.some(ext => url.pathname.endsWith(ext));
    if (isAsset || url.pathname.startsWith('/static/')) {
        event.respondWith(staleWhileRevalidate(request));
        return;
    }

    // Stratégie par défaut : Cache First
    event.respondWith(cacheFirst(request));
});

// ============================================================
// MISE À JOUR AUTOMATIQUE - NOTIFICATION
// ============================================================
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

// Notifie les clients qu'une mise à jour est disponible
self.addEventListener('controllerchange', () => {
    // Le nouveau SW a pris le contrôle
});

// ============================================================
// WEB PUSH API - PRÉPARATION (VAPID)
// ============================================================
// Architecture prête pour les notifications Web Push avec VAPID
// À activer lorsque les clés VAPID seront générées

self.addEventListener('push', (event) => {
    console.log('[SW NectarPro] Push reçu:', event);

    let data = {
        title: 'NectarPro',
        body: 'Nouvelle notification',
        icon: '/static/images/pwa/icon-192.png',
        badge: '/static/images/pwa/icon-96.png',
        tag: 'nectarpro-notification',
        data: {
            url: '/'
        }
    };

    if (event.data) {
        try {
            const payload = event.data.json();
            data = { ...data, ...payload };
        } catch (e) {
            data.body = event.data.text();
        }
    }

    const options = {
        body: data.body,
        icon: data.icon,
        badge: data.badge,
        tag: data.tag,
        data: data.data,
        vibrate: [200, 100, 200],
        actions: data.actions || [],
        requireInteraction: data.requireInteraction || false,
    };

    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

self.addEventListener('notificationclick', (event) => {
    console.log('[SW NectarPro] Notification cliquée:', event);

    event.notification.close();

    const url = event.notification.data && event.notification.data.url
        ? event.notification.data.url
        : '/';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((windowClients) => {
                // Chercher un onglet déjà ouvert
                for (const client of windowClients) {
                    if (client.url.includes(url) && 'focus' in client) {
                        return client.focus();
                    }
                }
                // Ouvrir un nouvel onglet
                if (clients.openWindow) {
                    return clients.openWindow(url);
                }
            })
    );
});

self.addEventListener('pushsubscriptionchange', (event) => {
    console.log('[SW NectarPro] Le push subscription a changé');
    // TODO: Envoyer la nouvelle subscription au serveur
    event.waitUntil(
        self.registration.pushManager.subscribe({
            userVisibleOnly: true,
            // Les clés VAPID seront ajoutées ici
            applicationServerKey: null // À remplacer par la clé publique VAPID
        })
        .then((newSubscription) => {
            console.log('[SW NectarPro] Nouvelle subscription:', newSubscription);
            // TODO: POST /api/push/subscribe avec la nouvelle subscription
        })
    );
});

console.log('[SW NectarPro] Service Worker chargé et prêt.');