from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings

JWT_ALGORITHM = "HS256"
JWT_EXPIRES_MINUTES = 60 * 12  # 12h : couvre un service complet

# Claim discriminant entre les deux principaux qui partagent `settings.jwt_secret`
# (staff et `platform_admin`, voir `platform_admin/security.py`) — vérifié
# explicitement dans `get_current_staff` avant de relire `sub` comme un ID
# de Staff : sans lui, un token admin valide déchiffrerait quand même ici
# (même secret) et ferait planter `int(payload["sub"])` sur un ID qui n'a
# aucune raison d'exister dans le bon espace.
TOKEN_TYPE = "staff"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(staff_id: int, restaurant_id: int, role: str) -> str:
    payload = {
        "sub": str(staff_id),
        "restaurant_id": restaurant_id,
        "role": role,
        "type": TOKEN_TYPE,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRES_MINUTES),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
