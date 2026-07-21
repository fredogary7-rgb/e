/**
 * NectarPro - PWA + VAPID Push Registration
 * Enregistre le Service Worker, gère le cache, les notifications push,
 * et la communication bidirectionnelle avec le SW.
 */
(function() {
  'use strict';

  if (!('serviceWorker' in navigator)) {
    console.log('⚠️ Service Worker non supporté');
    return;
  }

  // ── Variables globales ──
  let swRegistration = null;
  let vapidPublicKey = null;

  // ── Enregistrement du Service Worker ──
  window.addEventListener('load', function() {
    navigator.serviceWorker.register('/service-worker.js', {
      scope: '/'
    }).then(function(registration) {
      swRegistration = registration;
      console.log('✅ Service Worker enregistré : scope =', registration.scope);

      // Gérer les mises à jour du SW
      registration.addEventListener('updatefound', function() {
        var newWorker = registration.installing;
        console.log('📡 Nouveau Service Worker trouvé');

        newWorker.addEventListener('statechange', function() {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            console.log('🔄 Nouvelle version disponible');
            showUpdateBanner();
          }
        });
      });

      // Après enregistrement, récupérer la clé VAPID et s'abonner
      fetchVapidKeyAndSubscribe();

    }).catch(function(error) {
      console.error('❌ Erreur Service Worker :', error);
    });
  });

  // ── Récupération clé VAPID et abonnement ──
  function fetchVapidKeyAndSubscribe() {
    fetch('/api/push/vapid-public-key')
      .then(function(res) { return res.json(); })
      .then(function(data) {
        if (data.publicKey) {
          vapidPublicKey = data.publicKey;
          console.log('🔑 Clé VAPID reçue');

          // Transmettre la clé au Service Worker (pour re-subscribe)
          if (swRegistration && swRegistration.active) {
            swRegistration.active.postMessage({
              type: 'SET_VAPID_KEY',
              key: vapidPublicKey
            });
          }

          // Demander la permission et s'abonner
          checkPermissionAndSubscribe();
        } else {
          console.warn('⚠️ Clé VAPID non disponible');
        }
      })
      .catch(function(err) {
        console.error('❌ Erreur récupération clé VAPID:', err);
      });
  }

  // ── Vérification permission + abonnement ──
  function checkPermissionAndSubscribe() {
    if (!('Notification' in window)) {
      console.log('⚠️ Notifications non supportées');
      return;
    }

    if (Notification.permission === 'granted') {
      subscribeToPush();
    } else if (Notification.permission === 'default') {
      // Afficher un prompt élégant plutôt que le prompt natif
      showNotificationPrompt();
    } else {
      // denied – ne rien faire
      console.log('🚫 Notifications bloquées par l\'utilisateur');
    }
  }

  // ── Abonnement Push ──
  function subscribeToPush() {
    if (!swRegistration) {
      console.warn('⚠️ SW Registration non disponible');
      return;
    }
    if (!vapidPublicKey) {
      console.warn('⚠️ Clé VAPID non disponible');
      return;
    }

    swRegistration.pushManager.getSubscription()
      .then(function(subscription) {
        if (subscription) {
          console.log('📌 Déjà abonné aux push');
          // Synchroniser avec le serveur
          sendSubscriptionToServer(subscription);
          return;
        }

        // Nouvel abonnement
        var convertedKey = urlBase64ToUint8Array(vapidPublicKey);
        return swRegistration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: convertedKey
        }).then(function(newSubscription) {
          console.log('✅ Abonné aux push notifications');
          sendSubscriptionToServer(newSubscription);
        });
      })
      .catch(function(err) {
        console.error('❌ Erreur abonnement push:', err);
      });
  }

  // ── Envoi de l'abonnement au serveur ──
  function sendSubscriptionToServer(subscription) {
    var rawKey = subscription.getKey ? subscription.getKey('p256dh') : null;
    var rawAuthSecret = subscription.getKey ? subscription.getKey('auth') : null;

    var payload = {
      endpoint: subscription.endpoint,
      keys: {
        p256dh: rawKey ? btoa(String.fromCharCode.apply(null, new Uint8Array(rawKey))) : '',
        auth: rawAuthSecret ? btoa(String.fromCharCode.apply(null, new Uint8Array(rawAuthSecret))) : ''
      },
      // Métadonnées du navigateur/appareil
      user_agent: navigator.userAgent,
      browser: getBrowserName(),
      platform: getPlatformName(),
      language: navigator.language,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
    };

    fetch('/api/push/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function(res) {
      if (res.ok) {
        console.log('📤 Abonnement envoyé au serveur');
      } else if (res.status === 401) {
        console.warn('🔒 Non authentifié – abonnement non sauvegardé');
      }
    }).catch(function(err) {
      console.error('❌ Erreur envoi abonnement:', err);
    });
  }

  // ── Désabonnement ──
  window.unsubscribeFromPush = function() {
    if (!swRegistration) return Promise.reject('No SW');

    return swRegistration.pushManager.getSubscription()
      .then(function(subscription) {
        if (subscription) {
          // Informer le serveur
          fetch('/api/push/unsubscribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ endpoint: subscription.endpoint })
          }).catch(function() {});

          return subscription.unsubscribe();
        }
      })
      .then(function() {
        console.log('🔕 Désabonné des notifications');
      });
  };

  // ── Prompt de notification personnalisé ──
  function showNotificationPrompt() {
    // Créer un petit bandeau élégant
    var banner = document.createElement('div');
    banner.id = 'push-prompt-banner';
    banner.style.cssText = [
      'position:fixed; bottom:20px; left:50%; transform:translateX(-50%);',
      'background:linear-gradient(135deg, #0b1220, #1a2940);',
      'color:#fff; padding:14px 20px; border-radius:12px;',
      'box-shadow:0 8px 32px rgba(0,0,0,0.3); z-index:99999;',
      'display:flex; align-items:center; gap:12px; font-family:Inter,sans-serif;',
      'font-size:14px; max-width:420px; width:90%; border:1px solid rgba(255,255,255,0.1);',
      'animation:pushSlideUp 0.4s ease-out;'
    ].join('');

    banner.innerHTML = [
      '<span style="font-size:24px;">🔔</span>',
      '<span style="flex:1;">Activez les notifications pour recevoir les confirmations de dépôts, retraits et offres exclusives.</span>',
      '<button id="push-accept" style="background:#3b82f6;color:#fff;border:none;padding:8px 16px;border-radius:8px;',
      'font-weight:600;cursor:pointer;font-family:Inter,sans-serif;font-size:13px;white-space:nowrap;">Activer</button>',
      '<button id="push-deny" style="background:transparent;color:#94a3b8;border:none;padding:8px;',
      'cursor:pointer;font-size:16px;">✕</button>'
    ].join('');

    document.body.appendChild(banner);

    // Style d'animation
    if (!document.getElementById('push-anim-style')) {
      var style = document.createElement('style');
      style.id = 'push-anim-style';
      style.textContent = '@keyframes pushSlideUp { from{opacity:0;transform:translateX(-50%) translateY(30px);} to{opacity:1;transform:translateX(-50%) translateY(0);} }';
      document.head.appendChild(style);
    }

    document.getElementById('push-accept').addEventListener('click', function() {
      Notification.requestPermission().then(function(permission) {
        if (permission === 'granted') {
          subscribeToPush();
        }
        banner.remove();
      });
    });

    document.getElementById('push-deny').addEventListener('click', function() {
      banner.remove();
    });

    // Auto-fermeture après 15 secondes
    setTimeout(function() {
      if (document.getElementById('push-prompt-banner')) {
        banner.remove();
      }
    }, 15000);
  }

  // ── Bandeau de mise à jour ──
  function showUpdateBanner() {
    if (document.getElementById('update-banner')) return;

    var banner = document.createElement('div');
    banner.id = 'update-banner';
    banner.style.cssText = [
      'position:fixed; top:0; left:0; right:0; background:#3b82f6; color:#fff;',
      'text-align:center; padding:12px; z-index:99999; font-family:Inter,sans-serif;',
      'font-size:14px; font-weight:600; display:flex; align-items:center;',
      'justify-content:center; gap:12px; box-shadow:0 2px 8px rgba(59,130,246,0.4);'
    ].join('');

    banner.innerHTML = [
      '🔄 Une nouvelle version est disponible.',
      '<button onclick="window.location.reload()" style="background:#fff;color:#3b82f6;border:none;',
      'padding:6px 16px;border-radius:6px;font-weight:700;cursor:pointer;font-family:Inter,sans-serif;">',
      'Actualiser</button>'
    ].join('');

    document.body.prepend(banner);
  }

  // ── Écoute des messages du SW ──
  navigator.serviceWorker.addEventListener('message', function(event) {
    if (!event.data) return;

    switch (event.data.type) {
      case 'NOTIFICATION_DISPLAYED':
        console.log('📲 Notification affichée:', event.data.notificationId);
        // Marquer comme lue côté serveur
        if (event.data.notificationId) {
          fetch('/api/notifications/read/' + event.data.notificationId, {
            method: 'POST'
          }).catch(function() {});
        }
        break;

      case 'NOTIFICATION_CLICKED':
        console.log('👆 Notification cliquée:', event.data.notificationId);
        if (event.data.notificationId) {
          fetch('/api/notifications/read/' + event.data.notificationId, {
            method: 'POST'
          }).catch(function() {});
        }
        break;

      case 'NOTIFICATION_CLOSED':
        console.log('✕ Notification fermée:', event.data.notificationId);
        break;

      case 'UPDATE_AVAILABLE':
        console.log('🔄 Mise à jour disponible:', event.data.version);
        showUpdateBanner();
        break;

      case 'CACHE_UPDATED':
        console.log('📦 Cache mis à jour :', event.data.cache);
        break;
    }
  });

  // ── Utilitaires ──

  /** Convertit une clé base64 URL-safe en Uint8Array */
  function urlBase64ToUint8Array(base64String) {
    var padding = '='.repeat((4 - base64String.length % 4) % 4);
    var base64 = (base64String + padding)
      .replace(/\-/g, '+')
      .replace(/_/g, '/');
    var rawData = window.atob(base64);
    var outputArray = new Uint8Array(rawData.length);
    for (var i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  /** Détecte le nom du navigateur */
  function getBrowserName() {
    var ua = navigator.userAgent;
    if (ua.indexOf('Edg') > -1) return 'Edge';
    if (ua.indexOf('OPR') > -1 || ua.indexOf('Opera') > -1) return 'Opera';
    if (ua.indexOf('Brave') > -1) return 'Brave';
    if (ua.indexOf('Chrome') > -1) return 'Chrome';
    if (ua.indexOf('SamsungBrowser') > -1) return 'Samsung Internet';
    if (ua.indexOf('Firefox') > -1) return 'Firefox';
    if (ua.indexOf('Safari') > -1) return 'Safari';
    return 'Inconnu';
  }

  /** Détecte la plateforme */
  function getPlatformName() {
    var ua = navigator.userAgent;
    if (ua.indexOf('Android') > -1) return 'Android';
    if (ua.indexOf('Linux') > -1) return 'Linux';
    if (ua.indexOf('Windows') > -1) return 'Windows';
    if (ua.indexOf('Mac') > -1) return 'macOS';
    if (ua.indexOf('iPhone') > -1 || ua.indexOf('iPad') > -1) return 'iOS';
    return 'Inconnu';
  }

  // ─── Gérer la connectivité réseau ──────
  window.addEventListener('online', function() {
    console.log('🌐 En ligne');
    document.body.classList.remove('offline');
    var banner = document.getElementById('offline-banner');
    if (banner) banner.style.display = 'none';
  });

  window.addEventListener('offline', function() {
    console.log('📴 Hors ligne');
    document.body.classList.add('offline');
  });

  // ── Expose l'API globale ──
  window.NectarPush = {
    subscribe: subscribeToPush,
    unsubscribe: window.unsubscribeFromPush,
    isSubscribed: function() {
      if (!swRegistration) return Promise.resolve(false);
      return swRegistration.pushManager.getSubscription()
        .then(function(sub) { return !!sub; });
    },
    getRegistration: function() { return swRegistration; }
  };

})();