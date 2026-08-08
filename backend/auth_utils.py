"""Real password hashing for the `users` table (decisions-log.md: real-auth decision supersedes
the original "no real authentication" PRD call). PBKDF2-HMAC-SHA256 via stdlib `hashlib` — chosen
over bcrypt/passlib specifically to avoid a new pip dependency in an environment where package
installs have repeatedly hit corporate-proxy SSL friction (env-network.md).
"""
import hashlib
import hmac
import secrets

_ITERATIONS = 260_000  # OWASP-recommended floor for PBKDF2-HMAC-SHA256 as of this build


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS)
    return f"{_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        iterations_str, salt, hex_digest = stored.split("$")
        iterations = int(iterations_str)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations)
    return hmac.compare_digest(candidate.hex(), hex_digest)
