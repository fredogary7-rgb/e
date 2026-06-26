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

-- Ajouter la colonne transaction_reference si elle n'existe pas
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'retrait' AND column_name = 'transaction_reference'
    ) THEN
        ALTER TABLE retrait ADD COLUMN transaction_reference VARCHAR(100);
        RAISE NOTICE 'Colonne transaction_reference ajoutée à la table retrait';
    ELSE
        RAISE NOTICE 'Colonne transaction_reference existe déjà';
    END IF;
END $$;

-- Ajouter la colonne external_reference si elle n'existe pas
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'retrait' AND column_name = 'external_reference'
    ) THEN
        ALTER TABLE retrait ADD COLUMN external_reference VARCHAR(100);
        RAISE NOTICE 'Colonne external_reference ajoutée à la table retrait';
    ELSE
        RAISE NOTICE 'Colonne external_reference existe déjà';
    END IF;
END $$;

-- Ajouter la colonne soleaspay_status si elle n'existe pas
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'retrait' AND column_name = 'soleaspay_status'
    ) THEN
        ALTER TABLE retrait ADD COLUMN soleaspay_status VARCHAR(50);
        RAISE NOTICE 'Colonne soleaspay_status ajoutée à la table retrait';
    ELSE
        RAISE NOTICE 'Colonne soleaspay_status existe déjà';
    END IF;
END $$;

-- Ajouter la colonne soleaspay_created_at si elle n'existe pas
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'retrait' AND column_name = 'soleaspay_created_at'
    ) THEN
        ALTER TABLE retrait ADD COLUMN soleaspay_created_at TIMESTAMP;
        RAISE NOTICE 'Colonne soleaspay_created_at ajoutée à la table retrait';
    ELSE
        RAISE NOTICE 'Colonne soleaspay_created_at existe déjà';
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

-- Créer un index sur external_reference pour les recherches rapides (utilisé par le webhook)
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'retrait' AND column_name = 'external_reference'
    ) THEN
        CREATE INDEX idx_retrait_external_reference ON retrait(external_reference);
        RAISE NOTICE 'Index idx_retrait_external_reference créé';
    END IF;
END $$;

-- Afficher les colonnes de la table retrait
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'retrait' 
ORDER BY ordinal_position;
