import hmac

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger, log_event
from app.core.rate_limit import rate_limit
from app.modules.admin import schemas
from app.modules.tenants.models import Restaurant

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
logger = get_logger("admin")


def require_admin(x_admin_secret: str | None = Header(default=None)) -> None:
    """
    Secret unique partagé (Settings.admin_secret) — pas de compte ni de rôle,
    Wassim est seul utilisateur de cet écran (YAGNI, 2026-08-20). Fail-closed :
    tant qu'`ADMIN_SECRET` n'est pas posé en production, cette route reste
    fermée à tout le monde plutôt que de comparer "" à "" avec succès.
    `hmac.compare_digest` : comparaison à temps constant, comme les webhooks
    Konnect (app/core/konnect.py) — un secret comparé caractère par caractère
    fuit sa longueur/son préfixe par le temps de réponse.
    """
    if (
        not settings.admin_secret
        or not x_admin_secret
        or not hmac.compare_digest(x_admin_secret, settings.admin_secret)
    ):
        raise HTTPException(
            status_code=401, detail={"code": "INVALID_ADMIN_SECRET", "message": "invalid admin secret"}
        )


@router.get(
    "/restaurants",
    response_model=list[schemas.AdminRestaurantOut],
    dependencies=[Depends(require_admin), Depends(rate_limit())],
)
def list_restaurants(db: Session = Depends(get_db)):
    """Tous les restaurants, tous statuts confondus — c'est un écran admin,
    pas une vue restaurant scoping comme le reste de l'app."""
    return db.query(Restaurant).order_by(Restaurant.created_at.desc()).all()


@router.patch(
    "/restaurants/{restaurant_id}/promo",
    response_model=schemas.AdminRestaurantOut,
    dependencies=[Depends(require_admin), Depends(rate_limit())],
)
def set_promo(restaurant_id: int, payload: schemas.PromoUpdateIn, db: Session = Depends(get_db)):
    """
    Dérogation posée à la main par Wassim (« chaque client doit payer 50 DT
    pour l'Essentiel, jamais gratuit, sauf promo activée par l'admin »,
    2026-08-20) — indépendante de `is_active`, voir Restaurant.is_usable.
    """
    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=404, detail={"code": "RESTAURANT_NOT_FOUND", "message": "restaurant not found"}
        )
    restaurant.promo_gratuit = payload.promo_gratuit
    db.commit()
    db.refresh(restaurant)
    log_event(logger, "admin.promo_set", restaurant_id=restaurant_id, promo_gratuit=payload.promo_gratuit)
    return restaurant
