import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from .config import settings

_ITER = 200_000


def hash_secret(value: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", value.encode(), salt.encode(), _ITER).hex()
    return f"{salt}${digest}"


def verify_secret(value: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", value.encode(), salt.encode(), _ITER).hex()
    return hmac.compare_digest(check, digest)


def create_token(user_id: int, role: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({"sub": str(user_id), "role": role, "exp": exp}, settings.secret_key, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])


def chain_hash(prev: str, user_id, action: str, entity: str, entity_id, detail: str, ts: str) -> str:
    payload = "|".join([prev, str(user_id), action, entity, str(entity_id), detail or "", ts])
    return hashlib.sha256(payload.encode()).hexdigest()
