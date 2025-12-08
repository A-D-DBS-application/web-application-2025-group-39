# security.py
import os
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash, VerificationError

# ============================================================
# 1) Initialiseer Argon2 met veilige defaults
#    - Maakt een PasswordHasher object (beste keuze voor password hashing)
#    - Standaard parameters zijn veilig, maar kunnen later aangescherpt worden
#      (memory_cost, time_cost, parallelism)
# ============================================================
ph = PasswordHasher()

# ============================================================
# 2) Lees PEPPER uit environment
#    - Pepper is een extra geheim dat niet in de database staat
#      Het wordt toegevoegd aan elk wachtwoord voordat je het hasht
#      Maakt het moeilijker voor aanvallers, zelfs als ze je database stelen
#    - Zorg dat PASSWORD_PEPPER in je serveromgeving is gezet. (environment variable)
# ============================================================
PEPPER = os.environ.get("PASSWORD_PEPPER", "")


def add_pepper(pw: str) -> str:
    # Combineer het wachtwoord met de PEPPER
    # Simpelweg aaneenplakking; alternatief is HMAC voor extra veiligheid
    return f"{pw}{PEPPER}"


# ============================================================
# 3) Publieke helpers voor de rest van je applicatie
# ============================================================

def hash_password(plain: str) -> str:
    #Neemt een plaintext wachtwoord
    #Voegt de pepper toe
    #Maakt er een Argon2 hash van
    #Resultaat is een lange string die je veilig in de database kan opslaan.
    return ph.hash(add_pepper(plain))


def verify_password(stored_hash: str, plain: str) -> bool:
    # Vergelijkt een ingevoerd wachtwoord met de opgeslagen hash:
    # - Voeg pepper toe aan het ingevoerde wachtwoord
    # - Gebruik Argon2 verify() om te checken of dit overeenkomt met de hash
    # - Foutafhandeling: mismatch, invalid hash, of andere verificatieproblemen
    try:
        return ph.verify(stored_hash, add_pepper(plain))
    except (VerifyMismatchError, InvalidHash, VerificationError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    # Check of een hash opnieuw berekend moet worden:
    # - True  = hash is geldig maar niet meer volgens huidige Argon2 instellingen -> rehash bij login
    # - False = hash voldoet nog → geen actie nodig
    # Handig wanneer je later strengere Argon2 parameters instelt
    # Bijvoorbeeld: hogere memory_cost of time_cost
    return ph.check_needs_rehash(stored_hash)