-- Migration: ajout publicite_id et content_type à daily_tasks
ALTER TABLE daily_tasks ADD COLUMN publicite_id INTEGER REFERENCES publicites(id) ON DELETE CASCADE;
ALTER TABLE daily_tasks ADD COLUMN content_type VARCHAR(20) DEFAULT 'produit';
