-- Script SQL pour créer les tables du panier
-- Exécuter ce script sur la base de données PostgreSQL

-- Table paniers
CREATE TABLE IF NOT EXISTS paniers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    session_id VARCHAR(100),
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_paniers_user_id ON paniers(user_id);
CREATE INDEX IF NOT EXISTS idx_paniers_session_id ON paniers(session_id);

-- Table articles_panier
CREATE TABLE IF NOT EXISTS articles_panier (
    id SERIAL PRIMARY KEY,
    panier_id INTEGER NOT NULL REFERENCES paniers(id) ON DELETE CASCADE,
    produit_id INTEGER NOT NULL REFERENCES produits(id),
    quantite INTEGER NOT NULL DEFAULT 1,
    date_ajout TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_articles_panier_panier_id ON articles_panier(panier_id);
CREATE INDEX IF NOT EXISTS idx_articles_panier_produit_id ON articles_panier(produit_id);

-- Contrainte unique pour éviter les doublons (même produit dans même panier)
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_panier_produit ON articles_panier(panier_id, produit_id);