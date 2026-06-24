-- ============================================
-- CRÉER LES TABLES MANQUANTES POUR PUBLICITÉS
-- ============================================

-- Table pour les sauvegardes de publicités
CREATE TABLE IF NOT EXISTS sauvegardes_publicites (
    id SERIAL PRIMARY KEY,
    publicite_id INTEGER NOT NULL REFERENCES publicites(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(publicite_id, user_id)
);

-- Table pour les signalements de publicités
CREATE TABLE IF NOT EXISTS signalements_publicites (
    id SERIAL PRIMARY KEY,
    publicite_id INTEGER NOT NULL REFERENCES publicites(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    raison VARCHAR(50),
    description TEXT,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(publicite_id, user_id)
);

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_sauvegardes_publicite ON sauvegardes_publicites(publicite_id);
CREATE INDEX IF NOT EXISTS idx_sauvegardes_user ON sauvegardes_publicites(user_id);
CREATE INDEX IF NOT EXISTS idx_signalements_publicite ON signalements_publicites(publicite_id);
CREATE INDEX IF NOT EXISTS idx_signalements_user ON signalements_publicites(user_id);

-- Vérification
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name IN ('sauvegardes_publicites', 'signalements_publicites');