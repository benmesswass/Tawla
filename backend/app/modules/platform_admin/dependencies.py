from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.platform_admin.models import PlatformAdmin
from app.modules.platform_admin.security import TOKEN_TYPE, decode_access_token


def get_current_platform_admin(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> PlatformAdmin:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail={"code": "NOT_AUTHENTICATED", "message": "missing bearer token"}
        )

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_access_token(token)
    except Exception as exc:
        raise HTTPException(
            status_code=401, detail={"code": "INVALID_TOKEN", "message": "invalid or expired token"}
        ) from exc

    # Même secret que les tokens staff : sans ce claim, un token staff valide
    # se déchiffrerait quand même ici et ferait planter `db.get` sur un ID
    # hors de l'espace PlatformAdmin, ou pire, coïnciderait avec un vrai admin.
    if payload.get("type") != TOKEN_TYPE:
        raise HTTPException(
            status_code=401, detail={"code": "INVALID_TOKEN", "message": "invalid or expired token"}
        )

    admin = db.get(PlatformAdmin, int(payload["sub"]))
    # Contrôlé ici et pas seulement au login, même motif que Staff.is_active :
    # un JWT vit 12h, un accès désactivé pendant ce délai doit cesser tout de
    # suite — c'est l'écran qui expose le plus de données à la fois.
    if not admin or not admin.is_active:
        raise HTTPException(
            status_code=401, detail={"code": "INVALID_TOKEN", "message": "invalid or expired token"}
        )
    return admin
