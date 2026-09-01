from datetime import datetime, timedelta, timezone
from hashlib import sha256

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import encrypt_field
from app.core.database import get_db
from app.core.dates import as_utc
from app.core.konnect import (
    KonnectError,
    init_konnect_payment,
    is_konnect_enabled,
    is_subscription_konnect_enabled,
    sign_konnect_webhook,
    verify_konnect_webhook,
)
from app.core.logging import get_logger, log_event
from app.core.markets import current_market
from app.core.rate_limit import rate_limit
from app.core.subscription import (
    SUBSCRIPTION_DURATION_DAYS,
    effective_tier,
    tier_price,
    require_tier,
    tier_includes,
)
from app.core.subscription_payments import settle_subscription_payment
from app.modules.staff.dependencies import get_current_staff, require_role, require_role_regardless_of_activation
from app.modules.staff.models import Staff, StaffRole
from app.modules.tables import service as tables_service
from app.modules.tenants import schemas
from app.modules.tenants.models import Restaurant, SubscriptionTier

router = APIRouter(prefix="/api/v1/restaurants", tags=["restaurants"])

_MANAGER = require_role(StaffRole.MANAGER)
# Uniquement pour le checkout/vérification d'abonnement, voir la docstring de
# require_role_regardless_of_activation — jamais pour une autre route.
_MANAGER_EVEN_IF_INACTIVE = require_role_regardless_of_activation(StaffRole.MANAGER)
logger = get_logger("tenants")


# `POST /api/v1/restaurants` a été supprimé en Phase 12.2 : il créait un
# établissement sans aucune authentification (n'importe qui pouvait polluer la
# base), n'était appelé par aucun frontend, et faisait doublon avec
# `POST /api/v1/auth/register` qui crée le restaurant ET son premier manager.
# Les tests s'en servaient comme fixture : ils passent désormais par
# `tests/conftest.py::create_restaurant`, qui écrit directement en base.


# Déclarée AVANT `/{restaurant_id}` : sinon FastAPI tente de lire « by-token »
# comme un entier et répond 422 au lieu de router ici.
@router.get("/by-token/{qr_token}", response_model=schemas.RestaurantPublicOut)
def get_restaurant_by_qr_token(qr_token: str, db: Session = Depends(get_db)):
    """
    Route client : publique, mais liée à une table précise par son `qr_token`
    opaque, comme toutes les routes du parcours de commande.

    Elle remplace la lecture par identifiant, qui était publique et
    incrémentale : parcourir 1, 2, 3… donnait la liste des établissements
    clients de Tawla et leur formule d'abonnement.
    """
    table = tables_service.get_table_by_qr_token(db, qr_token)
    return db.get(Restaurant, table.restaurant_id)


@router.get("/{restaurant_id}", response_model=schemas.RestaurantOut)
def get_restaurant(
    restaurant_id: int,
    db: Session = Depends(get_db),
    staff: Staff = Depends(get_current_staff),
):
    """
    Fiche complète — écran cuisine et dashboard, tous deux authentifiés.
    404 et non 403 sur un autre établissement : un 403 confirmerait qu'il
    existe.
    """
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(
            status_code=404, detail={"code": "RESTAURANT_NOT_FOUND", "message": "restaurant not found"}
        )
    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=404, detail={"code": "RESTAURANT_NOT_FOUND", "message": "restaurant not found"}
        )
    return schemas.serialize_restaurant(restaurant)


@router.patch("/{restaurant_id}/ramadan-mode", response_model=schemas.RestaurantOut)
def set_ramadan_mode(
    restaurant_id: int,
    payload: schemas.RamadanModeUpdate,
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER),
    _tier: Staff = Depends(require_tier(SubscriptionTier.PRO)),
):
    """Réservé à Pro et Business (offre à trois paliers, 2026-08-18)."""
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})

    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=404, detail={"code": "RESTAURANT_NOT_FOUND", "message": "restaurant not found"}
        )

    restaurant.ramadan_mode_enabled = payload.enabled
    restaurant.iftar_time = payload.iftar_time
    db.commit()
    db.refresh(restaurant)
    return schemas.serialize_restaurant(restaurant)


@router.patch("/{restaurant_id}/cafe-mode", response_model=schemas.RestaurantOut)
def set_cafe_mode(
    restaurant_id: int,
    payload: schemas.CafeModeUpdate,
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER),
):
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})

    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=404, detail={"code": "RESTAURANT_NOT_FOUND", "message": "restaurant not found"}
        )

    restaurant.cafe_mode_enabled = payload.enabled
    db.commit()
    db.refresh(restaurant)
    return schemas.serialize_restaurant(restaurant)


@router.patch("/{restaurant_id}/kitchen-sound", response_model=schemas.RestaurantOut)
def set_kitchen_sound(
    restaurant_id: int,
    payload: schemas.KitchenSoundUpdate,
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER),
):
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})

    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=404, detail={"code": "RESTAURANT_NOT_FOUND", "message": "restaurant not found"}
        )

    restaurant.kitchen_sound_enabled = payload.enabled
    db.commit()
    db.refresh(restaurant)
    return schemas.serialize_restaurant(restaurant)


@router.patch("/{restaurant_id}/social-links", response_model=schemas.RestaurantOut)
def set_social_links(
    restaurant_id: int,
    payload: schemas.SocialLinksUpdate,
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER),
):
    """
    Icônes réseaux sociaux du menu client (Phase D1 de ROADMAP_DESIGN.md,
    point 3). Les quatre liens sont posés ensemble (un seul formulaire côté
    Réglages) — envoyer None sur l'un d'eux le retire sans toucher aux
    autres, à la différence d'un PATCH partiel classique.
    """
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    restaurant = _restaurant_or_404(db, restaurant_id)

    restaurant.facebook_url = payload.facebook_url
    restaurant.instagram_url = payload.instagram_url
    restaurant.tiktok_url = payload.tiktok_url
    restaurant.whatsapp_url = payload.whatsapp_url
    db.commit()
    db.refresh(restaurant)
    return schemas.serialize_restaurant(restaurant)


# --- Bannière de couverture et logo (Phase D1 de ROADMAP_DESIGN.md) ---------
#
# Même trio de champs et mêmes contraintes que la photo des plats
# (menu/router.py) : bytea en base, jpeg/png/webp, 3 Mo max, empreinte du
# contenu dans l'URL pour l'invalidation de cache. Volontairement PAS
# derrière require_tier(PRO) contrairement à la photo des plats : ce sont
# deux images fixes par restaurant, pas une par plat, l'argument de coût de
# stockage qui justifie le verrou Pro ne tient pas ici — et le verrouiller
# laisserait un compte Essentiel sans la moindre image sur son menu (il ne
# peut déjà pas uploader de photo de plat), à l'opposé de l'objectif de toute
# cette roadmap.

FORMATS_PHOTO = {"image/jpeg", "image/png", "image/webp"}
TAILLE_PHOTO_MAX = 3 * 1024 * 1024


@router.put("/{restaurant_id}/cover-photo", response_model=schemas.RestaurantOut)
async def upload_restaurant_cover_photo(
    restaurant_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER),
):
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    restaurant = _restaurant_or_404(db, restaurant_id)

    if file.content_type not in FORMATS_PHOTO:
        raise HTTPException(
            status_code=415,
            detail={"code": "UNSUPPORTED_IMAGE", "message": "image must be jpeg, png or webp"},
        )
    contenu = await file.read()
    if len(contenu) > TAILLE_PHOTO_MAX:
        raise HTTPException(
            status_code=413,
            detail={"code": "IMAGE_TOO_LARGE", "message": "image exceeds 3 MB"},
        )

    restaurant.cover_photo_data = contenu
    restaurant.cover_photo_content_type = file.content_type
    restaurant.cover_photo_url = (
        f"/api/v1/restaurants/{restaurant.id}/cover-photo?v={sha256(contenu).hexdigest()[:12]}"
    )
    db.commit()
    db.refresh(restaurant)
    log_event(logger, "restaurant.cover_photo_uploaded", restaurant_id=restaurant.id)
    return schemas.serialize_restaurant(restaurant)


@router.get("/{restaurant_id}/cover-photo")
def get_restaurant_cover_photo(restaurant_id: int, db: Session = Depends(get_db)):
    """Publique, comme la carte elle-même : c'est le client attablé qui la regarde."""
    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant or not restaurant.cover_photo_data:
        raise HTTPException(status_code=404, detail={"code": "IMAGE_NOT_FOUND", "message": "no image"})
    return Response(
        content=restaurant.cover_photo_data,
        media_type=restaurant.cover_photo_content_type or "image/jpeg",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.delete("/{restaurant_id}/cover-photo", response_model=schemas.RestaurantOut)
def delete_restaurant_cover_photo(
    restaurant_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_MANAGER)
):
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    restaurant = _restaurant_or_404(db, restaurant_id)
    restaurant.cover_photo_data = None
    restaurant.cover_photo_content_type = None
    restaurant.cover_photo_url = None
    db.commit()
    db.refresh(restaurant)
    return schemas.serialize_restaurant(restaurant)


@router.put("/{restaurant_id}/logo", response_model=schemas.RestaurantOut)
async def upload_restaurant_logo(
    restaurant_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER),
):
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    restaurant = _restaurant_or_404(db, restaurant_id)

    if file.content_type not in FORMATS_PHOTO:
        raise HTTPException(
            status_code=415,
            detail={"code": "UNSUPPORTED_IMAGE", "message": "image must be jpeg, png or webp"},
        )
    contenu = await file.read()
    if len(contenu) > TAILLE_PHOTO_MAX:
        raise HTTPException(
            status_code=413,
            detail={"code": "IMAGE_TOO_LARGE", "message": "image exceeds 3 MB"},
        )

    restaurant.logo_data = contenu
    restaurant.logo_content_type = file.content_type
    restaurant.logo_url = f"/api/v1/restaurants/{restaurant.id}/logo?v={sha256(contenu).hexdigest()[:12]}"
    db.commit()
    db.refresh(restaurant)
    log_event(logger, "restaurant.logo_uploaded", restaurant_id=restaurant.id)
    return schemas.serialize_restaurant(restaurant)


@router.get("/{restaurant_id}/logo")
def get_restaurant_logo(restaurant_id: int, db: Session = Depends(get_db)):
    """Publique, comme la carte elle-même : c'est le client attablé qui la regarde."""
    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant or not restaurant.logo_data:
        raise HTTPException(status_code=404, detail={"code": "IMAGE_NOT_FOUND", "message": "no image"})
    return Response(
        content=restaurant.logo_data,
        media_type=restaurant.logo_content_type or "image/jpeg",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.delete("/{restaurant_id}/logo", response_model=schemas.RestaurantOut)
def delete_restaurant_logo(restaurant_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_MANAGER)):
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    restaurant = _restaurant_or_404(db, restaurant_id)
    restaurant.logo_data = None
    restaurant.logo_content_type = None
    restaurant.logo_url = None
    db.commit()
    db.refresh(restaurant)
    return schemas.serialize_restaurant(restaurant)


@router.put("/{restaurant_id}/konnect-credentials", response_model=schemas.RestaurantOut)
def set_konnect_credentials(
    restaurant_id: int,
    payload: schemas.KonnectCredentialsIn,
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER),
):
    """
    Connecte le wallet Konnect PROPRE au restaurant — modèle direct (paiement
    carte du client, 2026-08-19) : sans ça, le client n'a que le mode démo
    (voir orders/service.py::start_card_payment). La clé n'est jamais
    réaffichée après coup (voir RestaurantOut.konnect_configured), même
    logique que le mot de passe temporaire d'un compte staff — on peut la
    remplacer, jamais la relire.
    """
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    restaurant = _restaurant_or_404(db, restaurant_id)

    restaurant.konnect_api_key_encrypted = encrypt_field(payload.api_key)
    restaurant.konnect_wallet_id = payload.wallet_id
    db.commit()
    db.refresh(restaurant)
    log_event(logger, "restaurant.konnect_credentials_set", restaurant_id=restaurant_id)
    return schemas.serialize_restaurant(restaurant)


def _restaurant_or_404(db: Session, restaurant_id: int) -> Restaurant:
    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=404, detail={"code": "RESTAURANT_NOT_FOUND", "message": "restaurant not found"}
        )
    return restaurant


@router.post("/{restaurant_id}/subscription/checkout", response_model=schemas.SubscriptionCheckoutOut)
def start_subscription_checkout(
    restaurant_id: int,
    payload: schemas.SubscriptionCheckoutIn,
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER_EVEN_IF_INACTIVE),
):
    """
    Deux usages distincts derrière ce même endpoint (2026-08-20, revu le
    2026-08-21 pour l'offre de lancement) :

    - `tier=essentiel` : abonnement de 30 jours (49 DT, jamais gratuit — voir
      CLAUDE.md) — TOUJOURS payable, contrairement à Pro/Business ci-dessous.
      Pas de règle "déjà actif, refusé" : payer avant l'échéance ne fait que
      prolonger la période depuis le reste courant (voir le calcul plus bas),
      jamais un double paiement problématique. Nécessaire pour que le rappel
      de paiement affiché tant que `has_paid_for_subscription` est faux
      (offre de lancement, frontend) propose un bouton qui marche vraiment,
      y compris pendant que le mois gratuit court encore.
    - `tier=pro`/`business` : passage à un palier SUPÉRIEUR, payé en ligne
      (offre à trois paliers, 2026-08-18) — jamais un renouvellement à
      l'identique ni une rétrogradation. Fonctionne aussi directement depuis
      un compte pas encore activé : le régler active le compte au passage
      (voir settle_subscription_payment), pas besoin de payer Essentiel
      d'abord.
    """
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    restaurant = _restaurant_or_404(db, restaurant_id)

    target = payload.tier
    if target not in current_market.tier_prices:
        raise HTTPException(status_code=400, detail={"code": "INVALID_TIER", "message": "unknown tier"})
    if target != SubscriptionTier.ESSENTIEL:
        current = effective_tier(restaurant)
        if tier_includes(current, target):
            raise HTTPException(
                status_code=400,
                detail={"code": "NOT_AN_UPGRADE", "message": f"restaurant already has {current.value} or above"},
            )

    if not is_subscription_konnect_enabled():
        # Mode démonstration : aucune clé Konnect réelle pour Tawla elle-même
        # pour l'instant (voir app/core/konnect.py) — le palier est appliqué
        # immédiatement, comme pay_by_card_simulated pour le paiement d'une
        # commande. Même calcul de prolongation que le règlement réel
        # (settle_subscription_payment) : reproduire ce même comportement ici
        # en mode démo évite un abonnement qui se comporterait différemment
        # le jour où Konnect devient réel. `is_subscription_konnect_enabled`
        # (pas `is_konnect_enabled` seule) : PAYMENT_MODE=konnect peut être
        # posé pour le paiement carte du client sans que Tawla ait encore ses
        # propres clés Konnect — rester en démo tant qu'elles manquent.
        # Essentiel EST un abonnement de 30 jours comme Pro/Business
        # (2026-08-20, voir CLAUDE.md) — même calcul de période pour les
        # trois. `is_active=True` passe à `True` une bonne fois pour toutes
        # (voir Restaurant.is_active/is_usable) ; c'est `subscription_period_end`
        # qui porte le renouvellement, pas ce booléen.
        now = datetime.now(timezone.utc)
        base = (
            as_utc(restaurant.subscription_period_end)
            if restaurant.subscription_period_end and as_utc(restaurant.subscription_period_end) > now
            else now
        )
        restaurant.subscription_tier = target
        restaurant.subscription_period_end = base + timedelta(days=SUBSCRIPTION_DURATION_DAYS)
        restaurant.is_active = True
        restaurant.has_paid_for_subscription = True
        db.commit()
        db.refresh(restaurant)
        log_event(
            logger, "subscription.checkout_demo",
            restaurant_id=restaurant_id, tier=target.value, provider="demo",
        )
        return schemas.SubscriptionCheckoutOut(mode="demo", restaurant=schemas.serialize_restaurant(restaurant))

    price = tier_price(restaurant, target)
    try:
        pay_url, payment_ref = init_konnect_payment(
            amount_tnd=price,
            order_id=str(restaurant.id),
            description=f"Tawla — abonnement {target.value}",
            webhook=(
                f"{settings.backend_url}/api/v1/restaurants/{restaurant.id}/subscription/webhook"
                f"?sig={sign_konnect_webhook(restaurant.id)}"
            ),
            success_url=f"{settings.frontend_url}/dashboard?konnect=success",
            fail_url=f"{settings.frontend_url}/dashboard?konnect=fail",
            lifespan_minutes=60,
        )
    except KonnectError as err:
        log_event(logger, "subscription.checkout_init_failed", restaurant_id=restaurant_id, error=str(err))
        raise HTTPException(
            status_code=502, detail={"code": "PAYMENT_INIT_FAILED", "message": "could not start the payment"}
        ) from err

    restaurant.subscription_payment_ref = payment_ref
    restaurant.subscription_pending_tier = target
    db.commit()
    log_event(
        logger, "subscription.checkout_initiated",
        restaurant_id=restaurant_id, tier=target.value, payment_ref=payment_ref, provider="konnect",
    )
    return schemas.SubscriptionCheckoutOut(mode="konnect", pay_url=pay_url)


@router.get("/{restaurant_id}/subscription/webhook")
def subscription_webhook(
    restaurant_id: int,
    sig: str,
    db: Session = Depends(get_db),
    _rate: None = Depends(rate_limit()),
):
    """
    Appelée en GET par Konnect avec `?payment_ref=…` ajouté à l'URL fournie à
    l'init-payment (non utilisé ici : le règlement relit toujours le paiement
    depuis l'API Konnect, jamais depuis les query params). `sig` signe
    `restaurant_id` (voir sign_konnect_webhook) — sans elle, un id connu ne
    suffit pas à forger un règlement.

    En dev local, Konnect ne peut pas joindre localhost : le filet de sécurité
    est `POST /subscription/check`, appelée par la page de retour.
    """
    if not is_konnect_enabled():
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "not found"})
    if not verify_konnect_webhook(restaurant_id, sig):
        log_event(logger, "subscription.webhook_bad_signature", restaurant_id=restaurant_id)
        raise HTTPException(status_code=401, detail={"code": "INVALID_SIGNATURE", "message": "invalid signature"})

    result = settle_subscription_payment(db, restaurant_id)
    log_event(logger, "subscription.webhook", restaurant_id=restaurant_id, result=result)
    return {"received": True, "result": result}


@router.post("/{restaurant_id}/subscription/check", response_model=schemas.RestaurantOut)
def check_subscription_payment(
    restaurant_id: int,
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER_EVEN_IF_INACTIVE),
):
    """
    Filet de sécurité appelé par la page de retour (`?konnect=success`) : en
    dev local, le webhook Konnect ci-dessus ne peut jamais être atteint
    (Konnect ne joint pas localhost). Sans effet si rien n'est en attente
    (idempotent, voir settle_subscription_payment) — donc sans risque à
    appeler même quand Konnect est désactivé.
    """
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    restaurant = _restaurant_or_404(db, restaurant_id)
    settle_subscription_payment(db, restaurant_id)
    db.refresh(restaurant)
    return schemas.serialize_restaurant(restaurant)
