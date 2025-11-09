from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config

# Initialiseer database object (nog niet gekoppeld aan app)
db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Koppel db aan app
    db.init_app(app)
    migrate.init_app(app, db)

    # Reflecteer bestaande tabellen in Supabase
    with app.app_context():
        db.reflect()

    # Importeren van routes en models HIERNA
    from app import routes, models
    app.register_blueprint(routes.main)

    return app
