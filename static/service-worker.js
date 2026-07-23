/**
 * NectarPro Service Worker
 * PWA avancée avec :
 *   - Cache intelligent (CSS, JS, images, polices, pages)
 *   - Mode offline
 *   - Mise à jour automatique
 *   - Web Push API (VAPID) – notifications, click, close, subscription change
 *
 * Version: 2.0.0
 */

// ── Clé publique VAPID (remplacée au déploiement par le serveur) ──
const VAPID_PUBLIC_KEY = '{{VAPID_PUBLIC_KEY}}';

const CACHE_NAME = 'nectarpro-v2';
const RUNTIME_CACHE = 'nectarpro-runtime-v2';

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
    console.log('[SW NectarPro] Installation v2...');

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
        if (request.headers.get('Accept') && request.headers.get('Accept').includes('text/html')) {
            const offlineCache = await caches.match('/offline');
            if (offlineCache) return offlineCache;
        }
        throw error;
    }
}

/**
 * Network First - Pour les pages dynamiques (dashboard, etc.)
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
        const offlineCache = await caches.match('/offline');
        if (offlineCache) return offlineCache;
        throw error;
    }
}

/**
 * Stale While Revalidate - Pour les assets (CSS, JS, images)
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

    // Ignorer les requêtes vers l'API
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

    // Stratégie : Network First pour les images de produits uploadées
    // Évite les incohérences de cache (200 sur fichier inexistant, 404 sur fichier existant)
    if (url.pathname.startsWith('/static/uploads/') || url.pathname.startsWith('/static/vlogs/')) {
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

    // Reçoit la clé VAPID publique du client
    if (event.data && event.data.type === 'SET_VAPID_KEY') {
        // Stocke en variable (sera utilisée pour re-subscribe)
        self._vapidPublicKey = event.data.key;
        console.log('[SW NectarPro] Clé VAPID reçue');
    }
});

// ============================================================
// WEB PUSH API (VAPID) – COMPLET
// ============================================================

/**
 * Réception d'une notification push
 */
self.addEventListener('push', (event) => {
    console.log('[SW NectarPro] Push reçu');

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
        vibrate: data.vibrate || [200, 100, 200],
        actions: data.actions || [],
        requireInteraction: data.requireInteraction || false,
        image: data.image || undefined,
        silent: data.silent || false,
        timestamp: data.timestamp || Date.now(),
        renotify: data.renotify || false,
    };

    event.waitUntil(
        self.registration.showNotification(data.title, options)
            .then(() => {
                // Notifier le client que la notif a été affichée (pour analytics)
                self.clients.matchAll({ type: 'window', includeUncontrolled: true })
                    .then((clients) => {
                        clients.forEach((client) => {
                            client.postMessage({
                                type: 'NOTIFICATION_DISPLAYED',
                                notificationId: data.data && data.data.notification_id,
                                timestamp: Date.now()
                            });
                        });
                    });
            })
    );
});

/**
 * Clic sur une notification
 */
self.addEventListener('notificationclick', (event) => {
    console.log('[SW NectarPro] Notification cliquée');

    event.notification.close();

    let targetUrl = event.notification.data && event.notification.data.url
        ? event.notification.data.url
        : '/';
    const notificationId = event.notification.data && event.notification.data.notification_id;

    // Construire une URL absolue (openWindow nécessite une URL absolue)
    const absoluteUrl = targetUrl.startsWith('/')
        ? self.location.origin + targetUrl
        : targetUrl;

    event.waitUntil(
        self.clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((windowClients) => {
                // Chercher un onglet déjà ouvert avec exactement cette URL
                for (const client of windowClients) {
                    if (client.url === absoluteUrl && 'focus' in client) {
                        // Notifier le client du clic (pour marquer comme lu)
                        client.postMessage({
                            type: 'NOTIFICATION_CLICKED',
                            notificationId: notificationId,
                            url: absoluteUrl
                        });
                        return client.focus();
                    }
                }
                // Ouvrir un nouvel onglet avec l'URL absolue
                if (self.clients.openWindow) {
                    return self.clients.openWindow(absoluteUrl);
                }
            })
    );
});

/**
 * Fermeture d'une notification (l'utilisateur la swipe)
 */
self.addEventListener('notificationclose', (event) => {
    console.log('[SW NectarPro] Notification fermée');

    const notificationId = event.notification.data && event.notification.data.notification_id;

    if (notificationId) {
        event.waitUntil(
            self.clients.matchAll({ type: 'window', includeUncontrolled: true })
                .then((windowClients) => {
                    windowClients.forEach((client) => {
                        client.postMessage({
                            type: 'NOTIFICATION_CLOSED',
                            notificationId: notificationId
                        });
                    });
                })
        );
    }
});

/**
 * Changement du PushSubscription (expiration, révocation, etc.)
 */
self.addEventListener('pushsubscriptionchange', (event) => {
    console.log('[SW NectarPro] PushSubscription a changé – re-subscription...');

    const vapidKey = self._vapidPublicKey || VAPID_PUBLIC_KEY;

    event.waitUntil(
        self.registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(vapidKey)
        })
        .then((newSubscription) => {
            console.log('[SW NectarPro] Nouvelle subscription');
            // Envoyer la nouvelle subscription au serveur
            return fetch('/api/push/subscribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    endpoint: newSubscription.endpoint,
                    keys: {
                        p256dh: btoa(String.fromCharCode.apply(null, new Uint8Array(newSubscription.getKey('p256dh')))),
                        auth: btoa(String.fromCharCode.apply(null, new Uint8Array(newSubscription.getKey('auth'))))
                    }
                })
            });
        })
        .then(() => {
            console.log('[SW NectarPro] Re-subscription envoyée au serveur');
        })
        .catch((err) => {
            console.error('[SW NectarPro] Erreur re-subscription:', err);
        })
    );
});

// ── Utilitaire : conversion base64 URL-safe → Uint8Array ──
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/\-/g, '+')
        .replace(/_/g, '/');
    const rawData = atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

// ============================================================
// BACKGROUND SYNC
// ============================================================
self.addEventListener('sync', (event) => {
    console.log('[SW NectarPro] Background Sync:', event.tag);

    if (event.tag === 'nectarpro-resubscribe') {
        event.waitUntil(
            self.registration.pushManager.getSubscription()
                .then((subscription) => {
                    if (subscription) {
                        return fetch('/api/push/sync-subscription', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                endpoint: subscription.endpoint
                            })
                        });
                    }
                })
        );
    }
});

// ============================================================
// PÉRIODIC SYNC (si supporté par le navigateur)
// ============================================================
self.addEventListener('periodicsync', (event) => {
    console.log('[SW NectarPro] Periodic Sync:', event.tag);

    if (event.tag === 'nectarpro-check-updates') {
        event.waitUntil(
            fetch('/api/push/check-updates')
                .then((res) => res.json())
                .then((data) => {
                    if (data.hasUpdate) {
                        // Notifier le client
                        self.clients.matchAll().then((clients) => {
                            clients.forEach((client) => {
                                client.postMessage({
                                    type: 'UPDATE_AVAILABLE',
                                    version: data.version
                                });
                            });
                        });
                    }
                })
                .catch(() => { /* silencieux */ })
        );
    }
});

console.log('[SW NectarPro v2] Service Worker chargé et prêt.');