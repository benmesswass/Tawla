from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.staff.models import Staff, StaffRole
from app.modules.staff.security import TOKEN_TYPE, decode_access_token
from app.modules.tenants.models import Restaurant


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


def require_active_restaurant(
    staff: Staff = Depends(get_current_staff),
    db: Session = Depends(get_db),
) -> Staff:
    """
    Toute route qui représente un USAGE réel de Tawla (gérer la carte, les
    tables, prendre des commandes, voir les stats...) en dépend — jamais
    `get_current_staff` seul pour ça. Volontairement PAS fusionné dans
    `get_current_staff` : le manager d'un restaurant pas encore activé doit
    quand même pouvoir se connecter, lire sa fiche restaurant et payer —
    seules ces routes-là (tenants `GET /{id}`, `/subscription/*`, `/auth/me`)
    restent sur `get_current_staff` nu, une allowlist volontaire (voir
    CLAUDE.md, 2026-08-20).
    """
    restaurant = db.get(Restaurant, staff.restaurant_id)
    if not restaurant or not restaurant.is_usable:
        raise HTTPException(
            status_code=402,
            detail={"code": "PAYMENT_REQUIRED", "message": "restaurant subscription is not active"},
        )
    return staff


def require_role(*roles: StaffRole):
    """Ex: Depends(require_role(StaffRole.MANAGER)) — 403 si le rôle ne correspond pas.
    Passe par `require_active_restaurant` (pas `get_current_staff` nu) : un
    restaurant non activé n'a accès à aucune route protégée par rôle."""

    def _dependency(staff: Staff = Depends(require_active_restaurant)) -> Staff:
        if staff.role not in roles:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "insufficient role"})
        return staff

    return _dependency


def require_role_regardless_of_activation(*roles: StaffRole):
    """
    Comme `require_role`, mais SANS passer par `require_active_restaurant` —
    exclusivement pour `tenants/router.py::start_subscription_checkout` et
    `check_subscription_payment` : un manager doit pouvoir payer/vérifier son
    paiement précisément PARCE QUE son restaurant n'est pas encore actif. Ne
    jamais réutiliser ailleurs — toute autre route « manager » doit passer
    par `require_role` (voir CLAUDE.md, 2026-08-20).
    """

    def _dependency(staff: Staff = Depends(get_current_staff)) -> Staff:
        if staff.role not in roles:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "insufficient role"})
        return staff

    return _dependency
