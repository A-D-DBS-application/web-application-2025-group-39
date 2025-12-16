import os
from dotenv import load_dotenv

# Laadt de variabelen uit je .env bestand
load_dotenv()

class Config:
    # Haal de waarden op via de namen die je in .env hebt gekozen
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False