from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config

# Initialiseer database objecten (nog niet gekoppeld aan app)
db = SQLAlchemy()
migrate = Migrate()

def create_app():
    # Flask-app aanmaken
    app = Flask(__name__)

    # Configuratie laden uit config.py
    app.config.from_object(Config)

    # Secret key instellen voor sessiebeveiliging
    app.secret_key = 'iets_heel_random_en_veilig'  # Bijvoorbeeld: 's3cr3t_K3y_2025!'

    # Sessie eindigt bij sluiten van de browser
    app.config['SESSION_PERMANENT'] = False

    # (Optioneel) Sessie verloopt automatisch na 60 minuten
    from datetime import timedelta
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=60)

    # Koppel database en migratie aan app
    db.init_app(app)
    migrate.init_app(app, db)

    # Reflecteer bestaande tabellen in Supabase
    with app.app_context():
        db.reflect()

    # Routes en modellen importeren en blueprint registreren
    from app import routes, models
    app.register_blueprint(routes.main)

    return app
