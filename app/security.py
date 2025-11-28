# security.py
import os
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash, VerificationError

# 1) Initialiseer Argon2 met veilige defaults
ph = PasswordHasher()  # gebruikt argon2id, met redelijke memory-/time-cost

# 2) Lees PEPPER uit environment
PEPPER = os.environ.get("PASSWORD_PEPPER", "")

def add_pepper(pw: str) -> str:
    # Pepper simpel concatenated; alternatief: HMAC (meer geavanceerd)
    return f"{pw}{PEPPER}"

# 3) Publieke helpers voor de rest van je app
def hash_password(plain: str) -> str:
    # Neemt een platte string, voegt pepper toe, geeft een Argon2 hash-string terug
    return ph.hash(add_pepper(plain))

def verify_password(stored_hash: str, plain: str) -> bool:
    # Vergelijkt de opgeslagen hash met het ingevoerde wachtwoord (plus pepper)
    try:
        return ph.verify(stored_hash, add_pepper(plain))
    except (VerifyMismatchError, InvalidHash, VerificationError):
        return False

def needs_rehash(stored_hash: str) -> bool:
    # Handig wanneer je later strengere Argon2 parameters instelt
    return ph.check_needs_rehash(stored_hash)