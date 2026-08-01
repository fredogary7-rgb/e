-- ===============================================
-- NECTAR PRO - Index Database Optimization
-- Pour PostgreSQL (Neon)
-- Cible : 5 000 utilisateurs simultanés
-- ===============================================

-- Exécuter avec :
-- psql "postgresql://neondb_owner:npg_YaC69HIAGyZn@ep-muddy-darkness-ai9gl7w1-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require" -f optimize_db.sql

-- Pour exécuter via un outil en ligne (comme pgAdmin, DBeaver, ou le SQL Editor de Neon)

-- ===============================================
-- 🔴 INDEX CRITIQUES (USER TABLE)
-- ===============================================

-- 1. Parrain - Utilisé pour les filleuls, commissions, parrainage (N+1 détecté)
CREATE INDEX IF NOT EXISTS idx_user_parrain ON "user" (parrain);

-- 2. Admin/Banned - Filtrages back-office
CREATE INDEX IF NOT EXISTS idx_user_is_admin ON "user" (is_admin);
CREATE INDEX IF NOT EXISTS idx_user_is_banned ON "user" (is_banned);

-- 3. Pays - Filtres et segmentation
CREATE INDEX IF NOT EXISTS idx_user_country ON "user" (country);

-- 4. Dates - Tris, classements, KPIs
CREATE INDEX IF NOT EXISTS idx_user_date_creation ON "user" (date_creation DESC);
CREATE INDEX IF NOT EXISTS idx_user_last_login ON "user" (last_login DESC);

-- 5. Wallet - Filtres pays/opérateur pour les retraits
CREATE INDEX IF NOT EXISTS idx_user_wallet_country ON "user" (wallet_country);
CREATE INDEX IF NOT EXISTS idx_user_wallet_operator ON "user" (wallet_operator);

-- 6. Index composite pour le classement des soldes
CREATE INDEX IF NOT EXISTS idx_user_solde_revenu_admin ON "user" (is_admin, is_banned, solde_revenu DESC);

-- ===============================================
-- 🟡 INDEX IMPORTANTS (DEPOT TABLE)
-- ===============================================

-- 7. Dépôts par utilisateur - Historique, dashboard
CREATE INDEX IF NOT EXISTS idx_depot_user_id ON depot (user_id);

-- 8. Dépôts par statut - Filtres admin
CREATE INDEX IF NOT EXISTS idx_depot_statut ON depot (statut);

-- 9. Dépôts par date - Tris, exports
CREATE INDEX IF NOT EXISTS idx_depot_date ON depot (date DESC);

-- 10. Index composite pour le dashboard admin
CREATE INDEX IF NOT EXISTS idx_depot_user_statut ON depot (user_id, statut);

-- ===============================================
-- 🟡 INDEX IMPORTANTS (RETRAIT TABLE)
-- ===============================================

-- 11. Retraits par utilisateur
CREATE INDEX IF NOT EXISTS idx_retrait_user_id ON retrait (user_id);

-- 12. Retraits par statut
CREATE INDEX IF NOT EXISTS idx_retrait_statut ON retrait (statut);

-- 13. Retraits par date
CREATE INDEX IF NOT EXISTS idx_retrait_date ON retrait (date DESC);

-- 14. Synchro SoleasPay - Recherche par référence
CREATE INDEX IF NOT EXISTS idx_retrait_reference_soleaspay ON retrait (reference_soleaspay);

-- ===============================================
-- 🟡 INDEX IMPORTANTS (COMMISSION TABLE)
-- ===============================================

-- 15. Commissions par parrain
CREATE INDEX IF NOT EXISTS idx_commission_parrain_uid ON commission (parrain_uid);

-- 16. Commissions par date
CREATE INDEX IF NOT EXISTS idx_commission_date ON commission (date DESC);

-- 17. Index composite - Parrain + Date
CREATE INDEX IF NOT EXISTS idx_commission_parrain_date ON commission (parrain_uid, date DESC);

-- ===============================================
-- 🟡 INDEX IMPORTANTS (COMMANDES TABLE)
-- ===============================================

-- 18. Commandes par acheteur
CREATE INDEX IF NOT EXISTS idx_commandes_user_id ON commandes (user_id);

-- 19. Commandes par boutique
CREATE INDEX IF NOT EXISTS idx_commandes_boutique_id ON commandes (boutique_id);

-- 20. Commandes par statut
CREATE INDEX IF NOT EXISTS idx_commandes_statut ON commandes (statut);

-- 21. Commandes par date
CREATE INDEX IF NOT EXISTS idx_commandes_date ON commandes (date_creation DESC);

-- 22. Commandes par référence (recherche)
CREATE INDEX IF NOT EXISTS idx_commandes_reference ON commandes (reference);

-- ===============================================
-- 🟡 INDEX IMPORTANTS (PUBLICITES TABLE)
-- ===============================================

-- 23. Publicités par créateur
CREATE INDEX IF NOT EXISTS idx_publicites_user_id ON publicites (user_id);

-- 24. Publicités actives (le plus utilisé)
CREATE INDEX IF NOT EXISTS idx_publicites_actif ON publicites (est_actif);

-- 25. Publicités par date
CREATE INDEX IF NOT EXISTS idx_publicites_date ON publicites (date_creation DESC);

-- 26. Index composite pour le feed
CREATE INDEX IF NOT EXISTS idx_publicites_feed ON publicites (est_actif, date_creation DESC);

-- ===============================================
-- 🟢 INDEX UTILES (NOTIFICATIONS TABLE)
-- ===============================================

-- 27. Notifications non lues par utilisateur (requête la + fréquente)
CREATE INDEX IF NOT EXISTS idx_notifications_user_lu ON notifications (user_id, lu);

-- 28. Notifications par date
CREATE INDEX IF NOT EXISTS idx_notifications_date ON notifications (date_creation DESC);

-- ===============================================
-- 🟢 INDEX UTILES (USER_TASKS TABLE)
-- ===============================================

-- 29. Tâches par utilisateur
CREATE INDEX IF NOT EXISTS idx_user_tasks_user_id ON user_tasks (user_id);

-- 30. Tâches par tâche
CREATE INDEX IF NOT EXISTS idx_user_tasks_task_id ON user_tasks (task_id);

-- 31. Éviter les doublons user+tâche (améliore les INSERT ON CONFLICT)
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_tasks_unique ON user_tasks (user_id, task_id);

-- ===============================================
-- 🟢 INDEX UTILES (FOLLOWS TABLE)
-- ===============================================

-- 32. Followers
CREATE INDEX IF NOT EXISTS idx_follows_follower ON follows (follower_id);

-- 33. Following
CREATE INDEX IF NOT EXISTS idx_follows_following ON follows (following_id);

-- 34. Éviter les doublons follower+following
CREATE UNIQUE INDEX IF NOT EXISTS idx_follows_unique ON follows (follower_id, following_id);

-- ===============================================
-- 🟢 INDEX UTILES (PANIER TABLE)
-- ===============================================

-- 35. Panier par utilisateur
CREATE INDEX IF NOT EXISTS idx_paniers_user_id ON paniers (user_id);

-- 36. Panier par session (utilisateurs non connectés)
CREATE INDEX IF NOT EXISTS idx_paniers_session_id ON paniers (session_id);

-- ===============================================
-- 🟢 INDEX UTILES (ARTICLES PANIER)
-- ===============================================

-- 37. Articles par panier
CREATE INDEX IF NOT EXISTS idx_articles_panier_panier_id ON articles_panier (panier_id);

-- 38. Articles par produit
CREATE INDEX IF NOT EXISTS idx_articles_panier_produit_id ON articles_panier (produit_id);

-- ===============================================
-- 🟢 INDEX UTILES (LIKES, SAUVEGARDES, SIGNALEMENTS)
-- ===============================================

-- 39. Likes par publicité
CREATE INDEX IF NOT EXISTS idx_likes_publicite ON likes_publicites (publicite_id, user_id);

-- 40. Sauvegardes par utilisateur
CREATE INDEX IF NOT EXISTS idx_sauvegardes_user ON sauvegardes_publicites (user_id, publicite_id);

-- 41. Signalements par publicité
CREATE INDEX IF NOT EXISTS idx_signalements_publicite ON signalements_publicites (publicite_id);

-- ===============================================
-- 🟢 INDEX UTILES (STAKING, QUESTIONS, GAMES)
-- ===============================================

-- 42. Staking actif
CREATE INDEX IF NOT EXISTS idx_staking_phone ON staking (phone);
CREATE INDEX IF NOT EXISTS idx_staking_actif ON staking (actif);

-- 43. GameSession par utilisateur
CREATE INDEX IF NOT EXISTS idx_game_session_user ON game_session (user_id, status);

-- ===============================================
-- 📊 ANALYSE DES STATISTIQUES POST-INDEX
-- ===============================================

-- Après avoir créé les index, mettre à jour les statistiques PostgreSQL :
ANALYZE "user";
ANALYZE depot;
ANALYZE retrait;
ANALYZE commission;
ANALYZE commandes;
ANALYZE publicites;
ANALYZE notifications;
ANALYZE user_tasks;
ANALYZE follows;
ANALYZE paniers;
ANALYZE articles_panier;

-- Vérifier la taille des index créés :
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;

-- Voir les index qui ne sont jamais utilisés (après quelques jours de production) :
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY tablename;