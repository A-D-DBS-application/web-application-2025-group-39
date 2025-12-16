import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect  # NIEUW: Importeer CSRF bescherming
from datetime import timedelta
from config import Config

# Objecten buiten de factory aanmaken
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect() # NIEUW: Maak het CSRF object aan

def create_app():
    app = Flask(__name__)

    # 1. CONFIGURATIE
    # Hier laden we alles uit config.py (inclusief SECRET_KEY en DATABASE_URL)
    app.config.from_object(Config)

    # OPMERKING: Omdat je in config.py al os.getenv("SECRET_KEY") gebruikt, 
    # hoef je app.config["SECRET_KEY"] hier niet nog eens apart te overschrijven.
    
    # Sessie instellingen
    app.config["SESSION_PERMANENT"] = False
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=60)

    # 2. EXTRA BEVEILIGING
    # Deze instellingen staan nu centraal. 
    # SLIMME CHECK: We kijken of de app in 'development' modus staat via je .env.
    # Indien development: Secure=False (nodig voor localhost).
    # Indien iets anders (zoals bij de prof of op Render): Secure=True (veilig voor HTTPS).
    is_dev = os.getenv('FLASK_ENV') == 'development'

    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,       # Voorkomt dat JavaScript bij je cookies kan (beschermt tegen XSS-aanvallen)
        SESSION_COOKIE_SAMESITE="Lax",      # Zorgt dat cookies niet worden meegestuurd bij verzoeken van andere websites
        SESSION_COOKIE_SECURE=not is_dev    # Staat op False bij jou lokaal, maar op True voor de prof/productie
    )

    # 3. INITIALISATIE
    db.init_app(app)
    migrate.init_app(app, db)
    
    # CSRF BEVEILIGING (Anti-Hacking):
    # Deze uitsmijter verplicht dat elk HTML-formulier een unieke 'csrf_token' meestuurt.
    # Dit voorkomt dat andere websites (hackers) ongevraagd acties kunnen uitvoeren 
    # in naam van jouw ingelogde gebruikers (Cross-Site Request Forgery).
    csrf.init_app(app)

    # Reflecteer bestaande tabellen
    with app.app_context():
        db.reflect()

    # Blueprints registreren
    from app import routes, models
    app.register_blueprint(routes.main)

    return app