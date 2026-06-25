-- Migration: Ajout de la colonne motif_refus à la table retrait
-- Date: 2026-06-26
-- Description: Ajoute une colonne pour stocker le motif de refus d'un retrait

-- Ajouter la colonne motif_refus si elle n'existe pas
ALTER TABLE retrait 
ADD COLUMN IF NOT EXISTS motif_refus TEXT;

-- Vérification de la structure de la table retrait
-- Cette requête permet de voir toutes les colonnes de la table
-- SELECT column_name, data_type, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_name = 'retrait' 
-- ORDER BY ordinal_position;

-- Instructions pour Railway :
-- 1. Exécuter cette migration via le dashboard Railway (Data > Database > Run SQL)
-- 2. Ou exécuter via psql : psql -d neondb -f add_motif_refus_column.sql
-- 3. Redémarrer l'application après la migration

-- Note : Cette migration est idempotente (peut être exécutée plusieurs fois sans effet secondaire)