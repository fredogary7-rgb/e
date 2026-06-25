-- Migration pour ajouter les colonnes de sécurité PIN
-- Exécuter cette migration pour ajouter le support anti-bruteforce

-- Ajouter les colonnes si elles n'existent pas déjà
ALTER TABLE "user" 
ADD COLUMN IF NOT EXISTS pin_failed_attempts INTEGER DEFAULT 0;

ALTER TABLE "user" 
ADD COLUMN IF NOT EXISTS pin_locked_until TIMESTAMP;

-- Afficher un message de confirmation
SELECT 'Migration PIN security columns ajoutée avec succès !' as result;