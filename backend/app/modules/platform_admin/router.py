import hmac
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dates import as_utc
from app.core.logging import get_logger, log_event
from app.core.rate_limit import rate_limit
from app.core.subscription import get_launch_campaign, launch_promo_grants_used
from app.modules.platform_admin import schemas, security, service
from app.modules.platform_admin.dependencies import get_current_platform_admin
from app.modules.platform_admin.models import PlatformAdmin
from app.modules.staff.security import hash_password, verify_password
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


@router.post(
    "/admins", response_model=schemas.PlatformAdminOut, status_code=201, dependencies=[Depends(rate_limit(5))]
)
def create_admin(
    payload: schemas.AdminCreateIn,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """
    Seul chemin de création d'un compte `PlatformAdmin` (2026-08-21ter,
    remplace `scripts/create_platform_admin.py` — plus d'accès shell au
    serveur requis ; 2026-08-21quater, formulaire dans /admin) — deux
    autorisations possibles, jamais un compte staff/manager :

    1. Un JWT admin valide (`Authorization: Bearer ...`, même token que
       `/overview`) — le cas normal : une fois connecté sur /admin, ça
       suffit à en créer un autre, pas besoin de ressaisir un secret.
    2. `ADMIN_CREATION_SECRET` (variable d'environnement, jamais commitée) —
       le seul chemin quand aucun admin n'existe encore (premier compte) ou
       que Wassim est bloqué dehors sans session valide. `hmac.compare_digest` :
       comparaison en temps constant, même raison que pour un mot de passe.

    Un JWT présent mais invalide/expiré retombe sur la vérification du
    secret plutôt que de refuser tout de suite — sinon un token périmé
    couperait aussi l'accès de secours. Rate-limité à 5/min (`rate_limit()`
    vaut 20/min par défaut, pensé pour un brute-force de mot de passe — un
    secret à deviner mérite un plafond encore plus bas).

    Idempotent par e-mail comme l'ancien script : rejouer avec le même
    e-mail met à jour le mot de passe/nom/réactive le compte plutôt que d'en
    créer un second.
    """
    creator_email = "secret"
    if authorization:
        try:
            creator_email = get_current_platform_admin(authorization=authorization, db=db).email
        except HTTPException:
            if not hmac.compare_digest(payload.secret, settings.admin_creation_secret):
                raise HTTPException(status_code=401, detail={"code": "INVALID_SECRET", "message": "invalid secret"})
    elif not hmac.compare_digest(payload.secret, settings.admin_creation_secret):
        raise HTTPException(status_code=401, detail={"code": "INVALID_SECRET", "message": "invalid secret"})

    email = payload.email.strip().lower()
    admin = db.query(PlatformAdmin).filter(PlatformAdmin.email == email).first()
    if admin:
        admin.password_hash = hash_password(payload.password)
        admin.name = payload.name
        admin.is_active = True
    else:
        admin = PlatformAdmin(email=email, name=payload.name, password_hash=hash_password(payload.password))
        db.add(admin)
    db.commit()
    db.refresh(admin)
    # Jamais le secret ni le mot de passe dans les logs.
    log_event(logger, "platform_admin.admin_created_or_updated", admin_email=email, created_by=creator_email)
    return admin


@router.get("/overview", response_model=schemas.PlatformOverview)
async def overview(
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
):
    return await service.get_overview(db)


@router.get("/product-analytics", response_model=schemas.ProductAnalytics)
def product_analytics(_admin: PlatformAdmin = Depends(get_current_platform_admin)):
    return service.get_product_analytics()


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


@router.put("/restaurants/{restaurant_id}/promo", response_model=schemas.PromoUpdateOut)
def set_restaurant_promo(
    restaurant_id: int,
    payload: schemas.PromoUpdateIn,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(get_current_platform_admin),
):
    """
    Promo personnalisée au cas par cas (2026-08-21bis, remplace l'ancien
    `promo_gratuit` — booléen figé, sans échéance) — pour un restaurant
    précis, à la discrétion de Wassim, indépendamment de l'offre de
    lancement ci-dessus (campagne globale) ou du nombre de places déjà
    prises.

    `duration_days == 0` retire la promo en cours (remet les deux colonnes à
    `None`) — ne touche jamais `is_active`/`subscription_period_end` : un
    accès déjà accordé n'est jamais repris en cours de route, seule son
    expiration naturelle ou une nouvelle décision de Wassim y met fin.

    Sous 100 %, la réduction ne s'applique qu'au prochain paiement (voir
    `core/subscription.py::tier_price`) — n'active jamais le compte
    elle-même, même logique que l'offre de lancement globale. À 100 %,
    active le compte immédiatement pour `duration_days` en PROLONGEANT
    l'échéance existante plutôt qu'en l'écrasant : un restaurant qui a déjà
    payé un palier en cours ne doit jamais perdre des jours déjà réglés
    parce qu'on lui offre un cadeau par-dessus.
    """
    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=404, detail={"code": "RESTAURANT_NOT_FOUND", "message": "restaurant not found"}
        )

    if payload.duration_days == 0:
        restaurant.custom_promo_discount_percent = None
        restaurant.custom_promo_ends_at = None
    else:
        now = datetime.now(timezone.utc)
        ends_at = now + timedelta(days=payload.duration_days)
        restaurant.custom_promo_discount_percent = payload.discount_percent
        restaurant.custom_promo_ends_at = ends_at
        if payload.discount_percent >= 100:
            restaurant.is_active = True
            current_end = as_utc(restaurant.subscription_period_end) if restaurant.subscription_period_end else now
            restaurant.subscription_period_end = max(current_end, ends_at)

    db.commit()
    db.refresh(restaurant)
    log_event(
        logger, "platform_admin.restaurant_promo_set",
        admin_id=admin.id, restaurant_id=restaurant_id,
        discount_percent=restaurant.custom_promo_discount_percent,
        ends_at=restaurant.custom_promo_ends_at.isoformat() if restaurant.custom_promo_ends_at else None,
    )
    return schemas.PromoUpdateOut(
        custom_promo_discount_percent=restaurant.custom_promo_discount_percent,
        custom_promo_ends_at=restaurant.custom_promo_ends_at,
    )
