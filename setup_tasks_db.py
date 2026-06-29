"""Script pour créer les tables du module Tâches Quotidiennes."""
import sys
sys.path.insert(0, '.')

from app import app, db

with app.app_context():
    # Créer toutes les tables manquantes (inclut DailyTask, UserTask, TaskReward)
    db.create_all()
    print("✅ Tables DailyTask, UserTask, TaskReward créées avec succès !")
