from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.staff.models import Staff, StaffRole
from app.modules.staff.security import TOKEN_TYPE, decode_access_token


def get_current_staff(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Staff:
    """Toute route staff/cuisine/manager en dépend — les routes client (scan
    QR, panier, suivi de commande) restent volontairement publiques."""
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

    # Défense en profondeur : `settings.jwt_secret` signe aussi les tokens
    # `platform_admin` (même secret, voir platform_admin/security.py) — sans
    # cette vérification, un token admin valide se déchiffrerait quand même
    # ici et ferait planter `int(payload["sub"])` sur un ID hors de l'espace
    # Staff (exception non rattrapée, 500 au lieu d'un 401 propre).
    if payload.get("type") != TOKEN_TYPE:
        raise HTTPException(
            status_code=401, detail={"code": "INVALID_TOKEN", "message": "invalid or expired token"}
        )

    staff = db.get(Staff, int(payload["sub"]))
    if not staff:
        raise HTTPException(status_code=401, detail={"code": "INVALID_TOKEN", "message": "staff not found"})

    # Contrôlé ici et pas seulement au login : un JWT vit 12h, donc un compte
    # désactivé (salarié parti) resterait sinon utilisable toute une journée.
    if not staff.is_active:
        raise HTTPException(
            status_code=401, detail={"code": "ACCOUNT_DISABLED", "message": "this account has been disabled"}
        )
    return staff


def require_role(*roles: StaffRole):
    """Ex: Depends(require_role(StaffRole.MANAGER)) — 403 si le rôle ne correspond pas."""

    def _dependency(staff: Staff = Depends(get_current_staff)) -> Staff:
        if staff.role not in roles:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "insufficient role"})
        return staff

    return _dependency
