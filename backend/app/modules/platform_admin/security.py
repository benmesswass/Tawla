from datetime import datetime, timedelta, timezone
from hashlib import sha256

import jwt

from app.core.config import settings

JWT_ALGORITHM = "HS256"
ADMIN_TOKEN_EXPIRES_MINUTES = 60 * 12
ADMIN_SCOPE = "platform_admin"


def _admin_jwt_secret() -> str:
    """
    Secret dérivé de `jwt_secret` avec séparation de domaine (même principe
    que `crypto.py::_fernet`) — jamais le même secret que les tokens staff.

    Un token staff porte `sub` = un id numérique (`get_current_staff` fait
    `int(payload["sub"])`) ; un token admin n'a pas de compte à retrouver en
    base. Avec un secret partagé, un token admin déchiffrerait quand même
    correctement sous `decode_access_token` et ferait planter `get_current_staff`
    sur `int("platform-admin")` (exception non rattrapée, hors du try/except qui
    entoure seulement le décodage) — un secret distinct fait échouer ce
    décodage-là proprement (signature invalide, 401 déjà géré), sans jamais
    atteindre cette ligne.
    """
    return sha256(f"{settings.jwt_secret}:platform-admin".encode("utf-8")).hexdigest()


def create_admin_token() -> str:
    payload = {
        "scope": ADMIN_SCOPE,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ADMIN_TOKEN_EXPIRES_MINUTES),
    }
    return jwt.encode(payload, _admin_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_admin_token(token: str) -> dict:
    payload = jwt.decode(token, _admin_jwt_secret(), algorithms=[JWT_ALGORITHM])
    if payload.get("scope") != ADMIN_SCOPE:
        raise jwt.InvalidTokenError("not a platform-admin token")
    return payload
