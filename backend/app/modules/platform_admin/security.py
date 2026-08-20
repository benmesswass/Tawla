from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings
from app.modules.staff.security import JWT_ALGORITHM

# Session plus longue que celle du staff (12h, pensée pour « couvrir un
# service ») : un check-in d'opérateur est occasionnel, pas lié à un service
# précis.
ADMIN_TOKEN_EXPIRES_MINUTES = 60 * 12

# Même `settings.jwt_secret` que les tokens staff (`staff/security.py`) — ce
# claim est ce qui empêche la confusion entre les deux principaux, vérifié
# explicitement des deux côtés (`get_current_staff` et
# `get_current_platform_admin`).
TOKEN_TYPE = "platform_admin"


def create_access_token(admin_id: int) -> str:
    payload = {
        "sub": str(admin_id),
        "type": TOKEN_TYPE,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ADMIN_TOKEN_EXPIRES_MINUTES),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
