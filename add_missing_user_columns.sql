-- Migration pour ajouter les colonnes manquantes dans la table "user"
-- Exécuter cette migration pour corriger l'erreur AttributeError: 'User' object has no attribute 'points'

-- Ajouter les colonnes de points manquantes
ALTER TABLE "user" 
ADD COLUMN IF NOT EXISTS points INTEGER DEFAULT 0;

ALTER TABLE "user" 
ADD COLUMN IF NOT EXISTS points_video INTEGER DEFAULT 0;

ALTER TABLE "user" 
ADD COLUMN IF NOT EXISTS points_youtube INTEGER DEFAULT 0;

ALTER TABLE "user" 
ADD COLUMN IF NOT EXISTS points_tiktok INTEGER DEFAULT 0;

ALTER TABLE "user" 
ADD COLUMN IF NOT EXISTS points_instagram INTEGER DEFAULT 0;

ALTER TABLE "user" 
ADD COLUMN IF NOT EXISTS points_ads INTEGER DEFAULT 0;

ALTER TABLE "user" 
ADD COLUMN IF NOT EXISTS points_spin INTEGER DEFAULT 0;

ALTER TABLE "user" 
ADD COLUMN IF NOT EXISTS points_games INTEGER DEFAULT 0;

-- Afficher un message de confirmation
SELECT 'Migration colonnes points ajoutées avec succès !' as result;