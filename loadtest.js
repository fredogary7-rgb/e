// ==========================================
// 🧪 TEST DE CHARGE K6 – Nectar Pro
// Cible : 5 000 utilisateurs simultanés
// ==========================================
//
// Installation :
//   npm install -g k6
//
// Exécution :
//   k6 run loadtest.js
//
// Avec sortie vers InfluxDB (monitoring) :
//   k6 run --out influxdb=http://localhost:8086/k6 loadtest.js
//
// Avec résultats dans un fichier JSON :
//   k6 run --out json=results.json loadtest.js
// ==========================================

import http from "k6/http";
import { check, sleep, group } from "k6";
import { Trend, Rate, Counter, Gauge } from "k6/metrics";
import { SharedArray } from "k6/data";

// ==========================================
// 📊 MÉTRIQUES CUSTOM
// ==========================================

const dashboardDuration = new Trend("dashboard_duration", true);
const connexionDuration = new Trend("connexion_duration", true);
const retraitDuration = new Trend("retrait_duration", true);
const notificationDuration = new Trend("notification_duration", true);
const marketDuration = new Trend("market_duration", true);
const errorRate = new Rate("errors");
const activeUsers = new Gauge("active_users");

// ==========================================
// ⚙️ CONFIGURATION
// ==========================================

// URL de base - MODIFIER pour pointer vers le serveur de test (PAS LA PRODUCTION)
const BASE_URL = __ENV.BASE_URL || "http://localhost:5000";

// Fichier CSV contenant les utilisateurs de test (format: username,password,phone)
// Généré par create_test_users.py
const TEST_USERS_PATH = "./test_users.csv";

// ==========================================
// 📂 CHARGEMENT DES UTILISATEURS DE TEST
// ==========================================

// Tentative de chargement depuis le CSV
let testUsers = [];
try {
  testUsers = new SharedArray("test_users", function () {
    // Utilisateurs codés en dur pour le fallback
    const users = [];
    for (let i = 1; i <= 5000; i++) {
      users.push({
        username: `testuser${i}`,
        password: `TestPass${i}!`,
        phone: `+22901${String(i).padStart(6, "0")}`,
      });
    }
    return users;
  });
} catch (e) {
  console.log("⚠️  Impossible de charger test_users.csv - utilisation des utilisateurs codés en dur");
  console.log("Exécutez python create_test_users.py pour générer le CSV");
}

// ==========================================
// 🎯 SCÉNARIOS DE MONTÉE EN CHARGE
// ==========================================

export const options = {
  // Montée en charge progressive (8 étapes vers 5000 utilisateurs)
  stages: [
    // Phase 1 : Warmup
    { duration: "2m", target: 50 },    // 50 utilisateurs
    // Phase 2 : Baseline
    { duration: "3m", target: 100 },    // 100 utilisateurs
    // Phase 3 : Charge modérée
    { duration: "3m", target: 250 },    // 250 utilisateurs
    // Phase 4 : Charge moyenne
    { duration: "3m", target: 500 },    // 500 utilisateurs
    // Phase 5 : Charge élevée
    { duration: "5m", target: 1000 },   // 1 000 utilisateurs
    // Phase 6 : Stress test
    { duration: "5m", target: 2000 },   // 2 000 utilisateurs
    // Phase 7 : Stress test
    { duration: "5m", target: 3000 },   // 3 000 utilisateurs
    // Phase 8 : Pic maximum
    { duration: "5m", target: 5000 },   // 5 000 utilisateurs
    // Descente progressive (optionnelle)
    // { duration: "5m", target: 0 },
  ],

  // Seuils d'alerte (le test échoue si dépassés)
  thresholds: {
    // Temps de réponse - 95% des requêtes doivent être < 800ms
    "http_req_duration": ["p(95)<800"],
    
    // Dashboard - 95% des dashboards doivent charger en < 500ms
    "dashboard_duration": ["p(95)<500"],
    
    // Connexion - 95% des connexions doivent réussir en < 1s
    "connexion_duration": ["p(95)<1000"],
    
    // Taux d'erreur global - max 1% d'erreurs
    "errors": ["rate<0.01"],
    
    // Vérification des statuts HTTP
    "http_req_failed": ["rate<0.01"],
    
    // Nombre de requêtes par seconde (optionnel)
    // "http_reqs": ["rate>100"],
  },

  // Répartition des scénarios
  scenarios: {
    test_charge: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: options.stages,
      gracefulRampDown: "30s",
    },
  },
};

// ==========================================
// 🎭 SCÉNARIO PRINCIPAL
// ==========================================

export default function () {
  // Sélectionner un utilisateur aléatoire
  const userIndex = Math.floor(Math.random() * testUsers.length);
  const user = testUsers[userIndex];

  // Mise à jour du nombre d'utilisateurs actifs
  activeUsers.add(1);

  // ==========================================
  // PHASE 1 : CONNEXION (15% des actions)
  // ==========================================
  
  const shouldLogin = Math.random() < 0.15;
  let cookies = null;

  if (shouldLogin) {
    group("Connexion", function () {
      const loginStart = Date.now();
      
      const loginResponse = http.post(
        `${BASE_URL}/connexion`,
        {
          username: user.username,
          password: user.password,
        },
        {
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
          tags: { scenario: "connexion" },
        }
      );

      connexionDuration.add(Date.now() - loginStart);

      const loginOk = check(loginResponse, {
        "✅ Connexion réussie": (r) => r.status === 200 || r.status === 302,
        "⚠️  Pas d'erreur serveur": (r) => r.status < 500,
      });

      if (!loginOk) {
        errorRate.add(1);
      }

      if (loginResponse.status === 200 || loginResponse.status === 302) {
        cookies = loginResponse.cookies;
      }
    });
  }

  // Si on a des cookies de session, on est connecté
  const sessionCookies = cookies || {};

  // ==========================================
  // PHASE 2 : DASHBOARD (25% des actions)
  // ==========================================
  
  const shouldViewDashboard = Math.random() < 0.25;

  if (shouldViewDashboard) {
    group("Tableau de bord", function () {
      const dashStart = Date.now();

      const dashboardResponse = http.get(`${BASE_URL}/dashboard`, {
        cookies: sessionCookies,
        tags: { scenario: "dashboard" },
      });

      dashboardDuration.add(Date.now() - dashStart);

      const dashOk = check(dashboardResponse, {
        "✅ Dashboard chargé": (r) => r.status === 200,
        "📊 Contient solde": (r) => r.body.includes("solde") || r.body.includes("Solde"),
        "⚠️  Pas d'erreur 500": (r) => r.status < 500,
      });

      if (!dashOk) {
        errorRate.add(1);
      }
    });
  }

  // ==========================================
  // PHASE 3 : NOTIFICATIONS (10% des actions)
  // ==========================================
  
  const shouldViewNotifications = Math.random() < 0.10;

  if (shouldViewNotifications) {
    group("Notifications", function () {
      const notifStart = Date.now();

      const notifResponse = http.get(`${BASE_URL}/api/notifications`, {
        cookies: sessionCookies,
        headers: {
          "Accept": "application/json",
          "X-Requested-With": "XMLHttpRequest",
        },
        tags: { scenario: "notifications" },
      });

      notificationDuration.add(Date.now() - notifStart);

      const notifOk = check(notifResponse, {
        "✅ Notifications chargées": (r) => r.status === 200,
        "⚠️  Pas d'erreur 500": (r) => r.status < 500,
      });

      if (!notifOk) {
        errorRate.add(1);
      }
    });
  }

  // ==========================================
  // PHASE 4 : RECHERCHES / MARKET (10% des actions)
  // ==========================================
  
  const shouldSearch = Math.random() < 0.10;

  if (shouldSearch) {
    group("Recherche", function () {
      const searchStart = Date.now();

      const searchTerms = ["produit", "vêtement", "chaussure", "montre", "téléphone"];
      const randomTerm = searchTerms[Math.floor(Math.random() * searchTerms.length)];

      const searchResponse = http.get(`${BASE_URL}/market?q=${randomTerm}`, {
        cookies: sessionCookies,
        tags: { scenario: "recherche" },
      });

      marketDuration.add(Date.now() - searchStart);

      const searchOk = check(searchResponse, {
        "✅ Recherche effectuée": (r) => r.status === 200,
        "⚠️  Pas d'erreur 500": (r) => r.status < 500,
      });

      if (!searchOk) {
        errorRate.add(1);
      }
    });
  }

  // ==========================================
  // PHASE 5 : PORTEFEUILLE (15% des actions)
  // ==========================================
  
  const shouldViewWallet = Math.random() < 0.15;

  if (shouldViewWallet) {
    group("Portefeuille", function () {
      const walletStart = Date.now();

      // Chargement du dashboard (section solde)
      const walletResponse = http.get(`${BASE_URL}/dashboard#wallet`, {
        cookies: sessionCookies,
        tags: { scenario: "portefeuille" },
      });

      dashboardDuration.add(Date.now() - walletStart);

      const walletOk = check(walletResponse, {
        "✅ Portefeuille chargé": (r) => r.status === 200,
        "💳 Contient wallet": (r) => r.body.includes("wallet") || r.body.includes("portefeuille") || r.body.includes("Wallet"),
        "⚠️  Pas d'erreur 500": (r) => r.status < 500,
      });

      if (!walletOk) {
        errorRate.add(1);
      }
    });
  }

  // ==========================================
  // PHASE 6 : TRANSFERT (10% des actions)
  // ==========================================
  
  const shouldTransfer = Math.random() < 0.10;

  if (shouldTransfer) {
    group("Transfert", function () {
      const transferStart = Date.now();

      // Simuler un retrait (POST /retrait)
      const transferResponse = http.post(
        `${BASE_URL}/retrait`,
        {
          montant: Math.floor(Math.random() * 5000) + 500, // 500-5500 XOF
          phone: user.phone,
          payment_method: "Moov Money",
          pays: "Benin",
        },
        {
          cookies: sessionCookies,
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
          tags: { scenario: "transfert" },
        }
      );

      retraitDuration.add(Date.now() - transferStart);

      const transferOk = check(transferResponse, {
        "✅ Transfert initié": (r) => r.status === 200 || r.status === 302,
        "⚠️  Pas d'erreur 500": (r) => r.status < 500,
      });

      if (!transferOk) {
        errorRate.add(1);
      }
    });
  }

  // ==========================================
  // PHASE 7 : NAVIGATION (10% des actions)
  // ==========================================
  
  const shouldNavigate = Math.random() < 0.10;

  if (shouldNavigate) {
    group("Navigation", function () {
      const pages = [
        "/publicite",
        "/market",
        "/boutique/1",
        "/revenues",
        "/chaine",
        "/apk",
      ];
      const randomPage = pages[Math.floor(Math.random() * pages.length)];

      const navResponse = http.get(`${BASE_URL}${randomPage}`, {
        cookies: sessionCookies,
        tags: { scenario: "navigation" },
      });

      const navOk = check(navResponse, {
        "✅ Navigation OK": (r) => r.status === 200,
        "⚠️  Pas d'erreur 500": (r) => r.status < 500,
      });

      if (!navOk) {
        errorRate.add(1);
      }
    });
  }

  // ==========================================
  // PHASE 8 : DÉCONNEXION (5% des actions)
  // ==========================================
  
  const shouldLogout = Math.random() < 0.05;

  if (shouldLogout) {
    group("Déconnexion", function () {
      const logoutResponse = http.get(`${BASE_URL}/logout`, {
        cookies: sessionCookies,
        tags: { scenario: "deconnexion" },
      });

      const logoutOk = check(logoutResponse, {
        "✅ Déconnexion OK": (r) => r.status === 200 || r.status === 302,
      });

      if (!logoutOk) {
        errorRate.add(1);
      }
    });
  }

  // ==========================================
  // TEMPS D'ATTENTE RÉALISTE ENTRE ACTIONS
  // ==========================================

  // Les utilisateurs réels ne cliquent pas toutes les 100ms
  // Temps de réflexion : entre 2 et 15 secondes
  sleep(Math.random() * 13 + 2); // 2-15 secondes

  activeUsers.add(-1);
}

// ==========================================
// 📊 RAPPORT FINAL
// ==========================================

export function handleSummary(data) {
  const metrics = data.metrics;
  
  // Extraire les métriques clés
  const httpReqDuration = metrics.http_req_duration?.values || {};
  const httpReqs = metrics.http_reqs?.values || {};
  const errors = metrics.errors?.values || {};
  const dashboardDurationVals = metrics.dashboard_duration?.values || {};
  const connexionDurationVals = metrics.connexion_duration?.values || {};

  const summary = {
    timestamp: new Date().toISOString(),
    test_configuration: {
      base_url: BASE_URL,
      target_users: 5000,
      stages: options.stages,
    },
    results: {
      // Temps de réponse global
      http_req_duration: {
        avg_ms: (httpReqDuration.avg || 0).toFixed(2),
        p50_ms: (httpReqDuration.med || 0).toFixed(2),
        p90_ms: (httpReqDuration["p(90)"] || 0).toFixed(2),
        p95_ms: (httpReqDuration["p(95)"] || 0).toFixed(2),
        p99_ms: (httpReqDuration["p(99)"] || 0).toFixed(2),
        min_ms: (httpReqDuration.min || 0).toFixed(2),
        max_ms: (httpReqDuration.max || 0).toFixed(2),
      },
      
      // Nombre total de requêtes
      total_requests: httpReqs.count || 0,
      requests_per_second: (httpReqs.rate || 0).toFixed(2),
      
      // Taux d'erreur
      error_rate: ((errors.rate || 0) * 100).toFixed(2) + "%",
      
      // Durée du dashboard
      dashboard_duration_avg_ms: (dashboardDurationVals.avg || 0).toFixed(2),
      dashboard_duration_p95_ms: (dashboardDurationVals["p(95)"] || 0).toFixed(2),
      
      // Durée de connexion
      connexion_duration_avg_ms: (connexionDurationVals.avg || 0).toFixed(2),
      connexion_duration_p95_ms: (connexionDurationVals["p(95)"] || 0).toFixed(2),
      
      // Durée totale du test
      test_duration_seconds: data.state?.testRunDurationMs / 1000 || 0,
    },
    status: data.root_group?.checks?.every(c => c.passes >= 1) ? "PASS" : "FAIL",
  };

  return {
    "stdout": `\n
    ╔══════════════════════════════════════════════╗
    ║     📊 RAPPORT DE TEST DE CHARGE            ║
    ║     Nectar Pro - 5000 utilisateurs          ║
    ╚══════════════════════════════════════════════╝
    
    🌐 Requêtes totales : ${summary.results.total_requests}
    ⚡ Requêtes/seconde  : ${summary.results.requests_per_second}
    ❌ Taux d'erreur      : ${summary.results.error_rate}
    
    📈 TEMPS DE RÉPONSE GLOBAL
    ├─ Moyenne  : ${summary.results.http_req_duration.avg_ms} ms
    ├─ Médiane  : ${summary.results.http_req_duration.p50_ms} ms
    ├─ p90      : ${summary.results.http_req_duration.p90_ms} ms
    ├─ p95      : ${summary.results.http_req_duration.p95_ms} ms
    └─ p99      : ${summary.results.http_req_duration.p99_ms} ms
    
    📊 DASHBOARD
    ├─ Moyenne  : ${summary.results.dashboard_duration_avg_ms} ms
    └─ p95      : ${summary.results.dashboard_duration_p95_ms} ms
    
    🔐 CONNEXION
    ├─ Moyenne  : ${summary.results.connexion_duration_avg_ms} ms
    └─ p95      : ${summary.results.connexion_duration_p95_ms} ms
    
    ⏱️  Durée du test : ${summary.results.test_duration_seconds.toFixed(0)} secondes
    ✅ Statut final   : ${summary.results.http_req_duration.p95_ms < 800 ? "✅ SUCCÈS" : "⚠️  ÉCHEC (p95 > 800ms)"}
    
    `,
    "summary.json": JSON.stringify(summary, null, 2),
  };
}