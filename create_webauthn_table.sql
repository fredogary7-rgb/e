-- Migration pour créer la table webauthn_credentials
-- Exécuter cette migration pour ajouter le support WebAuthn/Passkeys

-- Créer la table webauthn_credentials si elle n'existe pas
CREATE TABLE IF NOT EXISTS webauthn_credentials (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    credential_id VARCHAR(500) UNIQUE NOT NULL,
    credential_public_key BYTEA NOT NULL,
    sign_count INTEGER DEFAULT 0,
    device_type VARCHAR(50),
    aaguid VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE
);

-- Ajouter la contrainte de clé étrangère
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'webauthn_credentials_user_id_fkey'
        AND table_name = 'webauthn_credentials'
    ) THEN
        ALTER TABLE webauthn_credentials
        ADD CONSTRAINT webauthn_credentials_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Créer les index pour les performances
CREATE INDEX IF NOT EXISTS idx_webauthn_credentials_user_id ON webauthn_credentials(user_id);
CREATE INDEX IF NOT EXISTS idx_webauthn_credentials_credential_id ON webauthn_credentials(credential_id);
CREATE INDEX IF NOT EXISTS idx_webauthn_credentials_is_active ON webauthn_credentials(is_active);

-- Afficher un message de confirmation
SELECT 'Table webauthn_credentials créée avec succès !' as result;