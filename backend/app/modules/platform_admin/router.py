from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger, log_event
from app.core.rate_limit import rate_limit
from app.core.subscription import get_launch_campaign, launch_promo_grants_used
from app.modules.platform_admin import schemas, security, service
from app.modules.platform_admin.dependencies import get_current_platform_admin
from app.modules.platform_admin.models import PlatformAdmin
from app.modules.staff.security import verify_password
from app.modules.tenants.models import Restaurant

logger = get_logger("platform_admin")

router = APIRouter(prefix="/api/v1/platform-admin", tags=["platform-admin"])

# Hash bcrypt valide comparé même quand l'e-mail n'existe pas — même
# stratégie anti-timing que /auth/login (staff/router.py::_DUMMY_HASH).
_DUMMY_HASH = "$2b$12$f/0oq4Vt.wjtcqw76TM1DONwSQqoVa/lcI0H/3sTvjhBSBTJBjYHG"  # nosemgrep: generic.secrets.security.detected-bcrypt-hash.detected-bcrypt-hash


@router.post("/login", response_model=schemas.AdminLoginResponse, dependencies=[Depends(rate_limit())])
def login(payload: schemas.AdminLoginRequest, db: Session = Depends(get_db)):
    admin = db.query(PlatformAdmin).filter(PlatformAdmin.email == payload.email.lower()).first()

    if not admin:
        verify_password(payload.password, _DUMMY_HASH)
        raise HTTPException(
            status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "invalid email or password"}
        )

    if not verify_password(payload.password, admin.password_hash):
        raise HTTPException(
            status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "invalid email or password"}
        )

    # Mot de passe vérifié d'abord, même ordre que /auth/login : un accès
    # désactivé apprend qu'il est désactivé, pas qu'un e-mail donné existe.
    if not admin.is_active:
        raise HTTPException(
            status_code=401, detail={"code": "ACCOUNT_DISABLED", "message": "this account has been disabled"}
        )

    token = security.create_access_token(admin.id)
    return schemas.AdminLoginResponse(access_token=token, admin=admin)


@router.get("/overview", response_model=schemas.PlatformOverview)
async def overview(
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
):
    return await service.get_overview(db)


@router.get("/launch-campaign", response_model=schemas.LaunchCampaignOut)
def get_launch_campaign_settings(
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
):
    campaign = get_launch_campaign(db)
    return schemas.LaunchCampaignOut(
        discount_percent=campaign.discount_percent,
        max_grants=campaign.max_grants,
        grants_used=launch_promo_grants_used(db),
    )


@router.put("/launch-campaign", response_model=schemas.LaunchCampaignOut)
def set_launch_campaign_settings(
    payload: schemas.LaunchCampaignUpdate,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(get_current_platform_admin),
):
    """
    Réglages de l'offre de lancement (2026-08-21) — « une seule manip
    simple » demandée par Wassim : deux nombres, un bouton. S'applique aux
    inscriptions FUTURES uniquement — voir Restaurant.launch_promo_discount_percent,
    figé à l'inscription et jamais recalculé rétroactivement pour un
    restaurant déjà inscrit.
    """
    campaign = get_launch_campaign(db)
    campaign.discount_percent = payload.discount_percent
    campaign.max_grants = payload.max_grants
    db.commit()
    db.refresh(campaign)
    log_event(
        logger, "platform_admin.launch_campaign_updated",
        admin_id=admin.id, discount_percent=campaign.discount_percent, max_grants=campaign.max_grants,
    )
    return schemas.LaunchCampaignOut(
        discount_percent=campaign.discount_percent,
        max_grants=campaign.max_grants,
        grants_used=launch_promo_grants_used(db),
    )


@router.put("/restaurants/{restaurant_id}/promo", response_model=schemas.PromoUpdateIn)
def set_restaurant_promo(
    restaurant_id: int,
    payload: schemas.PromoUpdateIn,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(get_current_platform_admin),
):
    """
    Dérogation gratuite au cas par cas (2026-08-20, voir
    Restaurant.promo_gratuit) — distincte de l'offre de lancement ci-dessus :
    pour un restaurant précis, à la discrétion de Wassim, indépendamment de
    la campagne en cours ou du nombre de places déjà prises. Ne renvoie que
    la confirmation ; le frontend recharge `/overview` pour refléter le
    changement dans le tableau — pas la peine de dupliquer la construction
    d'un `RestaurantSummary` isolé pour ça.
    """
    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=404, detail={"code": "RESTAURANT_NOT_FOUND", "message": "restaurant not found"}
        )
    restaurant.promo_gratuit = payload.promo_gratuit
    db.commit()
    log_event(
        logger, "platform_admin.restaurant_promo_set",
        admin_id=admin.id, restaurant_id=restaurant_id, promo_gratuit=payload.promo_gratuit,
    )
    return payload
