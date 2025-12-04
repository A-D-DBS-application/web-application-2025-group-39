# __init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import timedelta
from config import Config

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__)

    # Config laden uit config.py
    app.config.from_object(Config)

    # Secret key uit environment (niet hardcoded!)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # Sessie instellingen
    app.config["SESSION_PERMANENT"] = False
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=60)

    # Extra beveiliging voor cookies
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=False,  # zet True zodra je via HTTPS draait
    )

    # DB en migratie koppelen
    db.init_app(app)
    migrate.init_app(app, db)

    # Reflecteer bestaande tabellen (Supabase)
    with app.app_context():
        db.reflect()

    # Blueprints registreren
    from app import routes, models

    app.register_blueprint(routes.main)

    return app
