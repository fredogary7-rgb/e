-- Migration : ajout de la colonne retrait_bloque à la table "user"
-- Permet de bloquer/débloquer les retraits d'un compte donné.

ALTER TABLE "user"
ADD COLUMN IF NOT EXISTS retrait_bloque BOOLEAN DEFAULT FALSE;
