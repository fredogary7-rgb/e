#!/usr/bin/env python
"""
==========================================
📊 MONITORING PERFORMANCE – Nectar Pro
==========================================

Usage :
    python monitor.py                    # Surveiller localhost:5000
    python monitor.py --url https://nectar-pro.cc  # Surveiller la production
    python monitor.py --url http://localhost:5000 --duration 300  # Pendant 5 minutes

Ce script :
    1. Mesure le temps de réponse des routes critiques
    2. Vérifie les codes HTTP
    3. Détecte les erreurs 500/502/504
    4. Affiche les percentiles (p50, p95, p99)
    5. Exporte un rapport JSON
"""

import time
import requests
import statistics
import json
import argparse
import sys
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import os

# ==========================================
# Configuration
# ==========================================

ROUTES_TO_MONITOR = [
    {"name": "Index", "path": "/", "method": "GET"},
    {"name": "Connexion", "path": "/connexion", "method": "GET"},
    {"name": "Market", "path": "/market", "method": "GET"},
    {"name": "Publicite", "path": "/publicite", "method": "GET"},
    {"name": "APK", "path": "/apk", "method": "GET"},
    {"name": "Team", "path": "/team", "method": "GET"},
]

# Routes qui nécessitent une session (login)
AUTH_ROUTES = [
    {"name": "Dashboard", "path": "/dashboard", "method": "GET"},
    {"name": "Profile", "path": "/profile", "method": "GET"},
    {"name": "Retrait", "path": "/retrait", "method": "GET"},
    {"name": "Revenus", "path": "/revenus", "method": "GET"},
    {"name": "Channel", "path": "/chaine", "method": "GET"},
]

# ==========================================
# Mesure des performances
# ==========================================

class PerformanceMonitor:
    def __init__(self, base_url, duration=120, concurrency=10, verbose=False):
        self.base_url = base_url.rstrip("/")
        self.duration = duration
        self.concurrency = concurrency
        self.verbose = verbose
        self.results = defaultdict(lambda: {"times": [], "errors": 0, "statuses": defaultdict(int)})
        self.start_time = None
        self.end_time = None
        self.total_requests = 0
        self.total_errors = 0

    def measure_route(self, route_info, cookies=None, headers=None):
        """Mesure le temps de réponse d'une route."""
        method = route_info["method"]
        path = route_info["path"]
        name = route_info["name"]
        url = f"{self.base_url}{path}"

        try:
            start = time.time()
            
            if method == "GET":
                resp = requests.get(url, cookies=cookies, headers=headers, timeout=15)
            elif method == "POST":
                resp = requests.post(url, cookies=cookies, headers=headers, timeout=15)
            
            elapsed = (time.time() - start) * 1000  # ms

            self.results[name]["times"].append(elapsed)
            self.results[name]["statuses"][resp.status_code] += 1
            self.total_requests += 1

            if resp.status_code >= 500:
                self.results[name]["errors"] += 1
                self.total_errors += 1

            if self.verbose:
                symbol = "✅" if resp.status_code < 400 else "❌"
                print(f"  {symbol} {name:20s} {elapsed:8.1f}ms  HTTP {resp.status_code}")

            return {"name": name, "time": elapsed, "status": resp.status_code}

        except requests.exceptions.Timeout:
            self.results[name]["errors"] += 1
            self.total_errors += 1
            self.results[name]["statuses"]["timeout"] += 1
            if self.verbose:
                print(f"  ⏱️  {name:20s} TIMEOUT (>15s)")
            return {"name": name, "time": 15000, "status": "timeout"}

        except Exception as e:
            self.results[name]["errors"] += 1
            self.total_errors += 1
            self.results[name]["statuses"]["error"] += 1
            if self.verbose:
                print(f"  ❌ {name:20s} ERROR: {str(e)[:50]}")
            return {"name": name, "time": 0, "status": "error"}

    def run(self):
        """Exécute le monitoring pendant la durée spécifiée."""
        print(f"""
╔══════════════════════════════════════════════╗
║     📊 MONITORING PERFORMANCE               ║
║     Nectar Pro                              ║
╚══════════════════════════════════════════════╝

🌐 URL        : {self.base_url}
⏱️  Durée      : {self.duration}s
🔀 Concurrence : {self.concurrency}
📋 Routes      : {len(ROUTES_TO_MONITOR) + len(AUTH_ROUTES)}
""")

        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(seconds=self.duration)
        iteration = 0

        while datetime.now() < self.end_time:
            iteration += 1
            elapsed = (datetime.now() - self.start_time).seconds
            remaining = self.duration - elapsed
            
            print(f"\n🔄 Itération {iteration} ({elapsed}s écoulées, {remaining}s restantes)")
            print("-" * 50)

            # Routes publiques (parallèles)
            with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
                futures = []
                for route in ROUTES_TO_MONITOR:
                    future = executor.submit(self.measure_route, route)
                    futures.append(future)

                # Attendre que toutes les requêtes soient terminées
                for future in as_completed(futures):
                    try:
                        result = future.result(timeout=20)
                    except Exception:
                        pass

            # Routes authentifiées (séquentielles pour éviter les conflits de session)
            if iteration % 3 == 0:  # Toutes les 3 itérations
                print("  -- Routes authentifiées --")
                for route in AUTH_ROUTES:
                    self.measure_route(route)

            # Pause entre les itérations
            time.sleep(2)

        # Rapport final
        self.generate_report()

    def generate_report(self):
        """Génère le rapport final."""
        actual_duration = (datetime.now() - self.start_time).seconds

        report = {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "duration_seconds": actual_duration,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "error_rate": f"{(self.total_errors / max(self.total_requests, 1) * 100):.2f}%",
            "routes": {}
        }

        print(f"""
╔══════════════════════════════════════════════╗
║     📊 RAPPORT DE PERFORMANCE               ║
║     Nectar Pro                              ║
╚══════════════════════════════════════════════╝

🕒 Durée du test   : {actual_duration}s
🌐 Requêtes totales : {self.total_requests}
❌ Erreurs          : {self.total_errors} ({report['error_rate']})
""")

        # Détail par route
        print("=" * 70)
        print(f"{'Route':<25s} {'Min':>8s} {'Avg':>8s} {'p95':>8s} {'p99':>8s} {'Max':>8s} {'Err%':>6s}")
        print("-" * 70)

        overall_times = []

        for route_name, data in sorted(self.results.items()):
            times = data["times"]
            if not times:
                print(f"{route_name:<25s} {'N/A':>8s} {'N/A':>8s} {'N/A':>8s} {'N/A':>8s} {'N/A':>8s} {'100%':>6s}")
                continue

            sorted_times = sorted(times)
            avg = statistics.mean(times)
            min_t = min(times)
            max_t = max(times)
            p95 = sorted_times[int(len(sorted_times) * 0.95)] if len(sorted_times) > 0 else 0
            p99 = sorted_times[int(len(sorted_times) * 0.99)] if len(sorted_times) > 0 else 0
            
            error_count = data["errors"]
            error_pct = f"{(error_count / len(times) * 100):.1f}%" if len(times) > 0 else "N/A"

            # Couleur basée sur la performance
            if avg < 300:
                symbol = "🟢"
            elif avg < 800:
                symbol = "🟡"
            else:
                symbol = "🔴"

            print(f"{symbol} {route_name:<23s} {min_t:7.1f}ms {avg:7.1f}ms {p95:7.1f}ms {p99:7.1f}ms {max_t:7.1f}ms {error_pct:>5s}")

            overall_times.extend(times)

            report["routes"][route_name] = {
                "requests": len(times),
                "min_ms": round(min_t, 2),
                "avg_ms": round(avg, 2),
                "p95_ms": round(p95, 2),
                "p99_ms": round(p99, 2),
                "max_ms": round(max_t, 2),
                "errors": error_count,
                "error_rate": error_pct,
                "status_codes": dict(data["statuses"]),
            }

        # Global
        if overall_times:
            sorted_overall = sorted(overall_times)
            print("-" * 70)
            print(f"{'GLOBAL':<25s} {min(overall_times):7.1f}ms {statistics.mean(overall_times):7.1f}ms {sorted_overall[int(len(sorted_overall)*0.95)]:7.1f}ms {sorted_overall[int(len(sorted_overall)*0.99)]:7.1f}ms {max(overall_times):7.1f}ms")

            report["global"] = {
                "min_ms": round(min(overall_times), 2),
                "avg_ms": round(statistics.mean(overall_times), 2),
                "p50_ms": round(statistics.median(overall_times), 2),
                "p95_ms": round(sorted_overall[int(len(sorted_overall) * 0.95)], 2),
                "p99_ms": round(sorted_overall[int(len(sorted_overall) * 0.99)], 2),
                "max_ms": round(max(overall_times), 2),
            }

        # Recommandations
        print(f"""
{'='*70}
📋 RECOMMANDATIONS
{'='*70}""")

        if overall_times:
            avg_global = statistics.mean(overall_times)
            p95_global = sorted_overall[int(len(sorted_overall) * 0.95)] if len(sorted_overall) > 0 else 0

            if avg_global < 300:
                print("✅ PERFORMANCE EXCELLENTE")
                print("   Temps de réponse moyen < 300ms")
            elif avg_global < 800:
                print("⚠️  PERFORMANCE ACCEPTABLE")
                print("   Temps de réponse moyen entre 300-800ms")
                print("   Actions recommandées :")
                print("   1. Vérifier les index de base de données")
                print("   2. Activer le cache Flask-Caching")
                print("   3. Optimiser les requêtes N+1")
            else:
                print("🔴 PERFORMANCE INSUFFISANTE")
                print("   Temps de réponse moyen > 800ms")
                print("   Actions urgentes :")
                print("   1. Exécuter optimize_db.sql pour les index")
                print("   2. Activer le cache Flask-Caching")
                print("   3. Augmenter le pool de connexions PostgreSQL")
                print("   4. Utiliser Gunicorn avec Gevent")
                print("   5. Profiler les routes lentes")
            
            if p95_global > 800:
                print(f"\n   ⚠️  p95 = {p95_global:.0f}ms (dépasse la cible de 800ms)")
        
        # Sauvegarde JSON
        report_file = f"monitor_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Rapport sauvegardé : {report_file}")
        print(f"═" * 70)


# ==========================================
# Routes lentes (mode profiling)
# ==========================================

def profile_routes(base_url, threshold_ms=500):
    """Détecte les routes lentes (dépassant threshold_ms)."""
    print(f"""
╔══════════════════════════════════════════════╗
║     🔍 DÉTECTION ROUTES LENTES              ║
║     Seuil : > {threshold_ms}ms                    ║
╚══════════════════════════════════════════════╝
""")

    all_routes = ROUTES_TO_MONITOR + AUTH_ROUTES
    slow_routes = []

    for route in all_routes:
        times = []
        for _ in range(5):  # 5 mesures
            try:
                start = time.time()
                resp = requests.get(
                    f"{base_url}{route['path']}",
                    timeout=15
                )
                elapsed = (time.time() - start) * 1000
                times.append(elapsed)
            except:
                times.append(15000)  # Timeout

        avg = statistics.mean(times)
        p95 = sorted(times)[int(len(times) * 0.95)] if len(times) > 0 else 0

        symbol = "🟢" if avg < 300 else ("🟡" if avg < 800 else "🔴")
        print(f"{symbol} {route['name']:<25s} Avg: {avg:7.1f}ms  p95: {p95:7.1f}ms")

        if avg > threshold_ms:
            slow_routes.append({
                "name": route["name"],
                "path": route["path"],
                "avg_ms": round(avg, 2),
                "p95_ms": round(p95, 2),
            })

    if slow_routes:
        print(f"\n🔴 {len(slow_routes)} route(s) lente(s) détectée(s) :")
        for r in slow_routes:
            print(f"   • {r['name']} ({r['path']}) - {r['avg_ms']}ms avg, {r['p95_ms']}ms p95")
    else:
        print(f"\n✅ Aucune route lente détectée")

    return slow_routes


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitorer les performances de Nectar Pro")
    parser.add_argument("--url", type=str, default="http://localhost:5000", help="URL de base (défaut: http://localhost:5000)")
    parser.add_argument("--duration", type=int, default=120, help="Durée du test en secondes (défaut: 120)")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrence (défaut: 10)")
    parser.add_argument("--profile", action="store_true", help="Mode profiling : détecter les routes lentes")
    parser.add_argument("--threshold", type=int, default=500, help="Seuil route lente en ms (défaut: 500)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbeux")

    args = parser.parse_args()

    if args.profile:
        profile_routes(args.url, args.threshold)
    else:
        monitor = PerformanceMonitor(
            base_url=args.url,
            duration=args.duration,
            concurrency=args.concurrency,
            verbose=args.verbose,
        )
        monitor.run()