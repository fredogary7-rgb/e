/**
 * NectarPro - PWA Service Worker Registration
 * Enregistre le service worker et gère le cache
 */
(function() {
  'use strict';

  if (!('serviceWorker' in navigator)) {
    console.log('⚠️ Service Worker non supporté');
    return;
  }

  window.addEventListener('load', function() {
    navigator.serviceWorker.register('/service-worker.js', {
      scope: '/'
    }).then(function(registration) {
      console.log('✅ Service Worker enregistré : scope =', registration.scope);
      
      // Gérer les mises à jour
      registration.addEventListener('updatefound', function() {
        var newWorker = registration.installing;
        console.log('📡 Nouveau Service Worker trouvé');
        
        newWorker.addEventListener('statechange', function() {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            console.log('🔄 Nouvelle version disponible - actualisez la page');
            if (confirm('Une nouvelle version de NectarPro est disponible. Actualiser ?')) {
              window.location.reload();
            }
          }
        });
      });
    }).catch(function(error) {
      console.error('❌ Erreur Service Worker :', error);
    });

    // Gérer les messages du Service Worker
    navigator.serviceWorker.addEventListener('message', function(event) {
      if (event.data && event.data.type === 'CACHE_UPDATED') {
        console.log('📦 Cache mis à jour :', event.data.cache);
      }
    });
  });

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
})();