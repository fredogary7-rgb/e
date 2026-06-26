-- Script SQL pour ajouter les colonnes de synchronisation SoleasPay à la table retrait
-- Exécuter sur la base de données PostgreSQL

-- Ajouter la colonne reference_soleaspay si elle n'existe pas
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'retrait' AND column_name = 'reference_soleaspay'
    ) THEN
        ALTER TABLE retrait ADD COLUMN reference_soleaspay VARCHAR(100);
        RAISE NOTICE 'Colonne reference_soleaspay ajoutée à la table retrait';
    ELSE
        RAISE NOTICE 'Colonne reference_soleaspay existe déjà';
    END IF;
END $$;

-- Ajouter la colonne last_sync si elle n'existe pas
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'retrait' AND column_name = 'last_sync'
    ) THEN
        ALTER TABLE retrait ADD COLUMN last_sync TIMESTAMP;
        RAISE NOTICE 'Colonne last_sync ajoutée à la table retrait';
    ELSE
        RAISE NOTICE 'Colonne last_sync existe déjà';
    END IF;
END $$;

-- Créer un index sur reference_soleaspay pour les recherches rapides
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'retrait' AND column_name = 'reference_soleaspay'
    ) THEN
        CREATE INDEX idx_retrait_reference_soleaspay ON retrait(reference_soleaspay);
        RAISE NOTICE 'Index idx_retrait_reference_soleaspay créé';
    END IF;
END $$;

-- Afficher les colonnes de la table retrait
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'retrait' 
ORDER BY ordinal_position;