-- Tables pour le système de publicités vidéo (style TikTok)

-- Table des publicités
CREATE TABLE IF NOT EXISTS publicites (
    id SERIAL PRIMARY KEY,
    boutique_id INTEGER NOT NULL REFERENCES boutiques(id),
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    produit_id INTEGER REFERENCES produits(id),
    video_url VARCHAR(500) NOT NULL,
    titre VARCHAR(200) NOT NULL,
    description TEXT,
    prix FLOAT,
    devise VARCHAR(10) DEFAULT 'XOF',
    duree FLOAT,
    vues INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    commentaires_count INTEGER DEFAULT 0,
    partages INTEGER DEFAULT 0,
    est_actif BOOLEAN DEFAULT true,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des commentaires sur les publicités
CREATE TABLE IF NOT EXISTS commentaires_publicites (
    id SERIAL PRIMARY KEY,
    publicite_id INTEGER NOT NULL REFERENCES publicites(id),
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    texte TEXT NOT NULL,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des likes sur les publicités
CREATE TABLE IF NOT EXISTS likes_publicites (
    id SERIAL PRIMARY KEY,
    publicite_id INTEGER NOT NULL REFERENCES publicites(id),
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des follows/abonnements
CREATE TABLE IF NOT EXISTS follows (
    id SERIAL PRIMARY KEY,
    follower_id INTEGER NOT NULL REFERENCES "user"(id),
    following_id INTEGER NOT NULL REFERENCES "user"(id),
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_publicites_boutique_id ON publicites(boutique_id);
CREATE INDEX IF NOT EXISTS idx_publicites_user_id ON publicites(user_id);
CREATE INDEX IF NOT EXISTS idx_publicites_est_actif ON publicites(est_actif);
CREATE INDEX IF NOT EXISTS idx_commentaires_publicite_id ON commentaires_publicites(publicite_id);
CREATE INDEX IF NOT EXISTS idx_likes_publicite_id ON likes_publicites(publicite_id);
CREATE INDEX IF NOT EXISTS idx_follows_follower_id ON follows(follower_id);
CREATE INDEX IF NOT EXISTS idx_follows_following_id ON follows(following_id);