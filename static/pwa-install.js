/**
 * NectarPro - PWA Installation Banner & Button
 * Détecte si l'app est installable et affiche une bannière/bouton natif
 */
(function() {
  'use strict';

  let deferredPrompt = null;
  let installBanner = null;
  let installButtons = null;
  let bannerShown = false;

  // ─── Vérifier si l'app est déjà installée (mode standalone) ──────
  var isStandalone = window.matchMedia('(display-mode: standalone)').matches
    || navigator.standalone
    || document.referrer.includes('android-app://');

  // ─── Vérifier si bannière dismissée récemment (< 7 jours) ──────
  var dismissed = localStorage.getItem('pwa-banner-dismissed');
  var isRecentlyDismissed = dismissed && (Date.now() - parseInt(dismissed)) < 7 * 24 * 60 * 60 * 1000;

  // ─── Écouter l'événement beforeinstallprompt (affichage immédiat) ──────
  window.addEventListener('beforeinstallprompt', function(e) {
    e.preventDefault();
    deferredPrompt = e;
    showInstallUI();
    console.log('📲 PWA : beforeinstallprompt capturé');
  });

  // ─── FALLBACK : afficher la bannière après 3s même sans beforeinstallprompt ──────
  // (indispensable pour iOS et les premières visites où le flag PWA
  //  n'est pas encore activé par Chrome)
  if (!isStandalone && !isRecentlyDismissed) {
    setTimeout(function() {
      if (!bannerShown) {
        console.log('📲 PWA : fallback banner (beforeinstallprompt non reçu)');
        showInstallUI();
      }
    }, 3000);
  }

  // ─── Afficher l'UI d'installation ──────
  function showInstallUI() {
    if (bannerShown || isStandalone) return;
    bannerShown = true;
    // Boutons pwa-install dans le DOM
    installButtons = document.querySelectorAll('.pwa-install-btn, #pwa-install');
    if (installButtons.length > 0) {
      installButtons.forEach(function(btn) {
        btn.style.display = 'inline-flex';
        btn.addEventListener('click', installPWA);
      });
    }

    // Créer la bannière flottante en bas
    if (!installBanner) {
      installBanner = document.createElement('div');
      installBanner.id = 'pwa-install-banner';
      installBanner.innerHTML = `
        <div style="
          position: fixed; bottom: 0; left: 0; right: 0;
          background: linear-gradient(135deg, #db2777, #ec4899);
          color: white; padding: 14px 20px; z-index: 99999;
          display: flex; align-items: center; justify-content: space-between;
          gap: 12px; box-shadow: 0 -4px 20px rgba(219,39,119,0.4);
          font-family: 'Poppins', sans-serif; font-size: 14px;
          animation: pwaSlideUp 0.4s ease-out;
        ">
          <div style="display:flex;align-items:center;gap:10px;flex:1;">
            <span style="font-size:28px;">📲</span>
            <div>
              <strong style="display:block;">Installer NectarPro</strong>
              <span style="opacity:0.85;font-size:12px;">Accès rapide depuis l'écran d'accueil</span>
            </div>
          </div>
          <button id="pwa-banner-install" style="
            background: white; color: #db2777; border: none;
            padding: 10px 18px; border-radius: 25px;
            font-weight: 600; font-size: 13px; cursor: pointer;
            white-space: nowrap; font-family: 'Poppins', sans-serif;
          ">Installer</button>
          <button id="pwa-banner-close" style="
            background: transparent; color: white; border: none;
            font-size: 20px; cursor: pointer; padding: 4px 8px;
            line-height: 1;
          ">✕</button>
        </div>
        <style>
          @keyframes pwaSlideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
        </style>
      `;
      document.body.appendChild(installBanner);

      document.getElementById('pwa-banner-install').addEventListener('click', installPWA);
      document.getElementById('pwa-banner-close').addEventListener('click', function() {
        installBanner.style.display = 'none';
        localStorage.setItem('pwa-banner-dismissed', Date.now());
      });
    }
  }

  // ─── Installer la PWA ──────
  function installPWA() {
    if (!deferredPrompt) {
      // Fallback: afficher les instructions manuelles
      showManualInstallHelp();
      return;
    }
    deferredPrompt.prompt();
    deferredPrompt.userChoice.then(function(result) {
      console.log('📲 PWA choix utilisateur:', result.outcome);
      deferredPrompt = null;
      hideInstallUI();
      if (result.outcome === 'accepted') {
        console.log('✅ PWA installée avec succès');
      }
    });
  }

  function hideInstallUI() {
    if (installBanner) {
      installBanner.style.display = 'none';
    }
    if (installButtons) {
      installButtons.forEach(function(btn) { btn.style.display = 'none'; });
    }
  }

  // ─── Instructions manuelles pour iOS ──────
  function showManualInstallHelp() {
    var isIOS = /iphone|ipad|ipod/.test(navigator.userAgent.toLowerCase());
    if (isIOS) {
      alert('📲 Pour installer l\'application :\n\n1. Appuyez sur le bouton Partager (📤) en bas de Safari\n2. Faites défiler et sélectionnez "Sur l\'écran d\'accueil"\n3. Appuyez sur "Ajouter"');
    } else {
      alert('📲 Pour installer l\'application :\n\n1. Ouvrez le menu du navigateur (⋮)\n2. Sélectionnez "Installer l\'application" ou "Ajouter à l\'écran d\'accueil"');
    }
  }

  // ─── Écouter l'événement appinstalled ──────
  window.addEventListener('appinstalled', function() {
    console.log('✅ PWA : application installée avec succès');
    deferredPrompt = null;
    hideInstallUI();
  });

  // ─── Cacher la bannière si déjà dismissée récemment (< 7 jours) ──────
  var dismissed = localStorage.getItem('pwa-banner-dismissed');
  if (dismissed && (Date.now() - parseInt(dismissed)) < 7 * 24 * 60 * 60 * 1000) {
    // Ne pas réafficher trop tôt (on écoute quand même beforeinstallprompt pour les boutons)
    console.log('📲 PWA bannière ignorée (dismiss récent)');
  }

  // ─── Exposer la fonction installPWA globalement ──────
  window.installPWA = installPWA;

  console.log('📲 PWA Install : module chargé');
})();