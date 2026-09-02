from datetime import datetime, timedelta, timezone
from hashlib import sha256

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
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
from app.core import stripe_gateway
from app.core.markets import current_market
from app.core.rate_limit import rate_limit
from app.core.subscription import (
    SUBSCRIPTION_DURATION_DAYS,
    effective_tier,
    tier_price,
    require_tier,
    tier_includes,
)
from app.core.subscription_payments import handle_stripe_subscription_event, settle_subscription_payment
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


def _clean_social_url(value: str | None, field: str) -> str | None:
    """
    http(s) uniquement : ces liens finissent en `href` brut sur le menu
    public (frontend/components/ReseauxSociaux.tsx), donc un schéma non
    filtré (`javascript:`...) serait un XSS stocké déclenché au clic par
    n'importe quel client. Bornée à 300 caractères pour matcher la colonne
    (String(300), models.py) — sans ce contrôle ici, un lien trop long fait
    échouer le commit avec une erreur Postgres brute au lieu d'un 422 propre.
    """
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if not value.lower().startswith(("http://", "https://")):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_SOCIAL_URL",
                "message": "link must start with http:// or https://",
                "field": field,
            },
        )
    if len(value) > 300:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "SOCIAL_URL_TOO_LONG",
                "message": "link is too long (300 characters max)",
                "field": field,
            },
        )
    return value


@router.patch("/{restaurant_id}/social-links", response_model=schemas.RestaurantOut)
def set_social_links(
    restaurant_id: int,
    payload: schemas.SocialLinksUpdate,
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER),
    _tier: Staff = Depends(require_tier(SubscriptionTier.PRO)),
):
    """
    Icônes réseaux sociaux + lien d'avis Google du menu client (Phase D1 de
    ROADMAP_DESIGN.md, point 3, et Phase D1bis). Les cinq liens sont posés
    ensemble (un seul formulaire côté Réglages) — envoyer None sur l'un
    d'eux le retire sans toucher aux autres, à la différence d'un PATCH
    partiel classique.

    Réservé à Pro et Business (retrofit décidé le 2026-09-01, même palier
    que l'avis Google) : le verrou est ici, à l'écriture, comme le mode
    Ramadan — pas relu à l'affichage sur la route publique
    (`get_restaurant_by_qr_token`), qui reste un passthrough simple.
    """
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    restaurant = _restaurant_or_404(db, restaurant_id)

    restaurant.facebook_url = _clean_social_url(payload.facebook_url, "facebook_url")
    restaurant.instagram_url = _clean_social_url(payload.instagram_url, "instagram_url")
    restaurant.tiktok_url = _clean_social_url(payload.tiktok_url, "tiktok_url")
    restaurant.whatsapp_url = _clean_social_url(payload.whatsapp_url, "whatsapp_url")
    restaurant.google_review_url = _clean_social_url(payload.google_review_url, "google_review_url")
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
    if restaurant.is_demo:
        # Un établissement de démo (jetable, purgé sous 2h) ne doit jamais
        # pouvoir connecter un vrai wallet — le paiement carte du client y
        # est déjà simulé automatiquement tant qu'aucun n'est connecté (voir
        # orders/service.py::start_card_payment) ; laisser passer de vraies
        # clés reviendrait à basculer un compte éphémère sur un vrai
        # encaissement (retour utilisateur, 2026-09-02).
        raise HTTPException(
            status_code=400,
            detail={"code": "DEMO_RESTAURANT", "message": "card payment is already simulated in demo mode"},
        )

    restaurant.konnect_api_key_encrypted = encrypt_field(payload.api_key)
    restaurant.konnect_wallet_id = payload.wallet_id
    db.commit()
    db.refresh(restaurant)
    log_event(logger, "restaurant.konnect_credentials_set", restaurant_id=restaurant_id)
    return schemas.serialize_restaurant(restaurant)


@router.post("/{restaurant_id}/stripe-connect/start", response_model=schemas.StripeConnectStartOut)
def start_stripe_connect(restaurant_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_MANAGER)):
    """
    Démarre (ou reprend) l'onboarding Stripe Connect du restaurant —
    équivalent Stripe de `set_konnect_credentials` ci-dessus, mais le
    restaurant ne saisit rien ici : il est redirigé vers une page hébergée
    par Stripe (Account Links), voir `stripe_gateway.create_onboarding_link`.
    Réutilise le compte existant si l'inscription avait déjà démarré, plutôt
    que d'en créer un second orphelin à chaque clic.
    """
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    restaurant = _restaurant_or_404(db, restaurant_id)
    if restaurant.is_demo:
        # Même garde que set_konnect_credentials ci-dessus — sans elle, un
        # établissement de démo pourrait créer un vrai compte Connect Stripe
        # orphelin (jamais nettoyé, la ligne restaurant est purgée sous 2h,
        # pas le compte Stripe), et si l'onboarding allait au bout, ferait
        # basculer le paiement carte du client de simulé à réel.
        raise HTTPException(
            status_code=400,
            detail={"code": "DEMO_RESTAURANT", "message": "card payment is already simulated in demo mode"},
        )

    account_id = restaurant.stripe_account_id
    if not account_id:
        try:
            account_id = stripe_gateway.create_connected_account(country=current_market.code.upper())
        except stripe_gateway.StripeGatewayError as err:
            raise HTTPException(
                status_code=502, detail={"code": "STRIPE_ACCOUNT_CREATE_FAILED", "message": str(err)}
            ) from err
        restaurant.stripe_account_id = account_id
        db.commit()

    try:
        onboarding_url = stripe_gateway.create_onboarding_link(
            account_id=account_id,
            refresh_url=f"{settings.frontend_url}/dashboard?stripe=refresh",
            return_url=f"{settings.frontend_url}/dashboard?stripe=return",
        )
    except stripe_gateway.StripeGatewayError as err:
        raise HTTPException(
            status_code=502, detail={"code": "STRIPE_ONBOARDING_LINK_FAILED", "message": str(err)}
        ) from err

    log_event(logger, "restaurant.stripe_connect_started", restaurant_id=restaurant_id, account_id=account_id)
    return schemas.StripeConnectStartOut(onboarding_url=onboarding_url)


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

    # Fournisseur résolu par current_market (un déploiement ne sert qu'un
    # marché) : Stripe n'a pas de second jeu de clés "Tawla elle-même" à
    # vérifier séparément comme Konnect (`is_subscription_konnect_enabled`) —
    # la même clé secrète plateforme sert la charge directe restaurant
    # (Connect) et la charge directe Tawla (abonnement, sans compte connecté,
    # voir stripe_gateway.py) — donc `is_stripe_enabled()` seul suffit.
    is_provider_enabled = (
        stripe_gateway.is_stripe_enabled()
        if current_market.payment_provider == "stripe"
        else is_subscription_konnect_enabled()
    )
    # Un établissement de démo (jetable, purgé sous 2h) reste TOUJOURS en
    # mode démo ici, même si le déploiement a PAYMENT_MODE=stripe pour ses
    # vrais restaurants — sans quoi "S'abonner à Business" créerait un vrai
    # abonnement Stripe récurrent sur un compte qui n'existera plus dans 2h :
    # plus aucun tableau de bord pour le résilier, prélèvement indéfini
    # (retour utilisateur, 2026-09-02). Même raisonnement que
    # `pay_by_card_simulated` côté client (orders/service.py), qui lui est
    # protégé par construction (jamais de vraies clés sur un compte démo,
    # voir set_konnect_credentials/start_stripe_connect ci-dessus).
    if not is_provider_enabled or restaurant.is_demo:
        # Mode démonstration : aucune clé réelle pour Tawla elle-même pour
        # l'instant (voir app/core/konnect.py / stripe_gateway.py) — le palier
        # est appliqué immédiatement, comme pay_by_card_simulated pour le
        # paiement d'une commande. Même calcul de prolongation que le
        # règlement réel (settle_subscription_payment) : reproduire ce même
        # comportement ici en mode démo évite un abonnement qui se
        # comporterait différemment le jour où le paiement réel s'active.
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
    if current_market.payment_provider == "stripe":
        # Déjà abonné (stripe_subscription_id posé par
        # handle_stripe_subscription_event au premier paiement) : modifier
        # CET abonnement, jamais en créer un second en parallèle — bug réel
        # corrigé le 2026-09-02, chaque clic empilait un nouvel abonnement
        # sans annuler le précédent (double, triple facturation constatée en
        # conditions réelles). Seule la toute première souscription (pas
        # encore de stripe_subscription_id) passe par une session de
        # paiement.
        if restaurant.stripe_subscription_id:
            # `target == essentiel` est TOUJOURS payable même sans dépasser
            # le palier courant (voir le garde-fou plus haut, pensé pour
            # payer un palier en attente pendant le mois gratuit) — mais ici,
            # abonnement déjà actif, ce serait une RÉTROGRADATION immédiate
            # avec prorata, pas ce que ce chemin doit faire (voir
            # schedule_subscription_downgrade pour ça, en différé, sans
            # prorata).
            if not (tier_includes(target, effective_tier(restaurant)) and target != effective_tier(restaurant)):
                raise HTTPException(
                    status_code=400,
                    detail={"code": "NOT_AN_UPGRADE", "message": "use the downgrade endpoint for a lower tier"},
                )
            try:
                # Une rétrogradation programmée (schedule_subscription_downgrade)
                # écraserait cet upgrade à l'échéance si on ne l'annule pas
                # d'abord — un manager qui change deux fois d'avis doit voir
                # la DERNIÈRE décision gagner, jamais la première (retour
                # utilisateur, 2026-09-02).
                if restaurant.subscription_downgrade_pending_tier:
                    stripe_gateway.release_schedule_if_any(subscription_id=restaurant.stripe_subscription_id)
                stripe_gateway.change_tier_immediately(
                    subscription_id=restaurant.stripe_subscription_id,
                    new_tier=target.value,
                    new_amount_eur=price,
                    description=f"Tawla — abonnement {target.value}",
                )
            except stripe_gateway.StripeGatewayError as err:
                log_event(logger, "subscription.tier_change_failed", restaurant_id=restaurant_id, error=str(err))
                raise HTTPException(
                    status_code=502, detail={"code": "PAYMENT_INIT_FAILED", "message": "could not change tier"}
                ) from err
            restaurant.subscription_tier = target
            restaurant.is_active = True
            restaurant.has_paid_for_subscription = True
            restaurant.subscription_downgrade_pending_tier = None
            db.commit()
            db.refresh(restaurant)
            log_event(
                logger, "subscription.tier_changed_immediately",
                restaurant_id=restaurant_id, tier=target.value, provider="stripe",
            )
            return schemas.SubscriptionCheckoutOut(mode="stripe", restaurant=schemas.serialize_restaurant(restaurant))

        # Abonnement récurrent (mode Netflix, retour utilisateur 2026-09-02)
        # — jamais `subscription_payment_ref`/`subscription_pending_tier`
        # ici : ces deux champs gardent l'idempotence d'un paiement PONCTUEL
        # (Konnect, et l'ACTIVATION initiale ci-dessous), sans objet pour un
        # abonnement qui se facture tout seul chaque mois sans jamais
        # ré-émettre de référence. Seul le webhook
        # (`handle_stripe_subscription_event`) fait foi, voir
        # subscription_payments.py.
        try:
            pay_url, payment_ref = stripe_gateway.create_subscription_checkout_session(
                amount_eur=price,
                restaurant_id=restaurant.id,
                tier=target.value,
                description=f"Tawla — abonnement {target.value}",
                success_url=f"{settings.frontend_url}/dashboard?stripe_subscription=success",
                cancel_url=f"{settings.frontend_url}/dashboard?stripe_subscription=fail",
                customer_email=None,
            )
        except stripe_gateway.StripeGatewayError as err:
            log_event(logger, "subscription.checkout_init_failed", restaurant_id=restaurant_id, error=str(err))
            raise HTTPException(
                status_code=502, detail={"code": "PAYMENT_INIT_FAILED", "message": "could not start the payment"}
            ) from err
        log_event(
            logger, "subscription.checkout_initiated",
            restaurant_id=restaurant_id, tier=target.value, payment_ref=payment_ref, provider="stripe",
        )
        return schemas.SubscriptionCheckoutOut(mode="stripe", pay_url=pay_url)

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


@router.post("/stripe-subscription-webhook")
async def stripe_subscription_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Point d'entrée UNIQUE pour tous les évènements d'abonnement récurrent
    Stripe (mode Netflix, retour utilisateur 2026-09-02) — jamais scopé à un
    `{restaurant_id}` dans l'URL comme les webhooks Konnect : Stripe ne
    connaît pas nos identifiants avant d'avoir vérifié la signature, c'est
    `handle_stripe_subscription_event` qui retrouve le restaurant concerné à
    partir du contenu de l'évènement (subscription_payments.py). Corps BRUT
    (pas `request.json()`) : la vérification de signature porte sur les
    octets exacts envoyés par Stripe, un JSON reparsé puis réencodé ne
    matcherait plus la signature.
    """
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        event = stripe_gateway.construct_webhook_event(payload=payload, signature_header=signature)
    except stripe_gateway.StripeGatewayError as err:
        log_event(logger, "stripe.subscription_webhook_bad_signature", error=str(err))
        raise HTTPException(status_code=401, detail={"code": "INVALID_SIGNATURE", "message": "invalid signature"}) from err

    result = handle_stripe_subscription_event(db, event)
    log_event(logger, "stripe.subscription_webhook", event_type=event["type"], result=result)
    return {"received": True, "result": result}


@router.post("/{restaurant_id}/subscription/manage", response_model=schemas.BillingPortalOut)
def open_billing_portal(restaurant_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_MANAGER)):
    """
    Portail Stripe hébergé où le manager gère lui-même son abonnement —
    annuler, changer de moyen de paiement, voir ses factures (mode Netflix,
    retour utilisateur 2026-09-02). `stripe_customer_id` : posé par
    `handle_stripe_subscription_event` au premier paiement, absent tant
    qu'aucun abonnement récurrent n'a jamais été payé.
    """
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    restaurant = _restaurant_or_404(db, restaurant_id)
    if not restaurant.stripe_customer_id:
        raise HTTPException(status_code=404, detail={"code": "NO_SUBSCRIPTION", "message": "no active subscription"})

    try:
        url = stripe_gateway.create_billing_portal_session(
            customer_id=restaurant.stripe_customer_id,
            return_url=f"{settings.frontend_url}/dashboard?tab=settings#abonnement",
        )
    except stripe_gateway.StripeGatewayError as err:
        raise HTTPException(
            status_code=502, detail={"code": "BILLING_PORTAL_FAILED", "message": str(err)}
        ) from err
    return schemas.BillingPortalOut(portal_url=url)


@router.post("/{restaurant_id}/subscription/downgrade", response_model=schemas.RestaurantOut)
def schedule_subscription_downgrade(
    restaurant_id: int,
    payload: schemas.SubscriptionDowngradeIn,
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER),
):
    """
    Palier INFÉRIEUR à la prochaine échéance, en restant abonné — distinct
    d'une annulation complète (retour utilisateur, 2026-09-02 : Pro/Business
    ont le choix entre annuler et redescendre à un palier moins cher, jamais
    un seul bouton "annuler" qui confondrait les deux). Jamais immédiat,
    jamais de prorata — voir stripe_gateway.schedule_tier_change. Le palier
    affiché ne change qu'au prochain `invoice.paid`
    (subscription_payments.py), pas ici : cet appel programme seulement.
    """
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    restaurant = _restaurant_or_404(db, restaurant_id)

    target = payload.tier
    current = effective_tier(restaurant)
    if not (tier_includes(current, target) and current != target):
        raise HTTPException(
            status_code=400, detail={"code": "NOT_A_DOWNGRADE", "message": "target tier must be strictly lower"}
        )

    if restaurant.is_demo:
        # Un établissement de démo n'a jamais de vrai `stripe_subscription_id`
        # (voir start_subscription_checkout) — rien à programmer chez Stripe,
        # rien à différer non plus : la session dure 2h, personne ne reverra
        # la prochaine échéance. Appliqué tout de suite, comme l'upgrade
        # simulé (retour utilisateur, 2026-09-02 : "un bouton de simulation
        # pour... paiement pour tawla").
        restaurant.subscription_tier = target
        db.commit()
        db.refresh(restaurant)
        log_event(logger, "subscription.downgrade_simulated", restaurant_id=restaurant_id, tier=target.value)
        return schemas.serialize_restaurant(restaurant)

    if not restaurant.stripe_subscription_id:
        raise HTTPException(status_code=404, detail={"code": "NO_SUBSCRIPTION", "message": "no active subscription"})

    try:
        stripe_gateway.schedule_tier_change(
            subscription_id=restaurant.stripe_subscription_id,
            new_tier=target.value,
            new_amount_eur=tier_price(restaurant, target),
            description=f"Tawla — abonnement {target.value}",
        )
    except stripe_gateway.StripeGatewayError as err:
        raise HTTPException(
            status_code=502, detail={"code": "DOWNGRADE_SCHEDULING_FAILED", "message": str(err)}
        ) from err

    # Seul moyen pour l'interface de savoir qu'un changement est en attente
    # avant la prochaine échéance — sans ça, rien ne distinguait un clic
    # réussi d'un clic resté sans effet (retour utilisateur, 2026-09-02 :
    # "je reste à Business sans aucune indication"). Effacé par
    # `invoice.paid` (subscription_payments.py) une fois réellement appliqué.
    restaurant.subscription_downgrade_pending_tier = target
    db.commit()
    db.refresh(restaurant)

    log_event(logger, "subscription.downgrade_scheduled", restaurant_id=restaurant_id, tier=target.value)
    return schemas.serialize_restaurant(restaurant)


@router.post("/{restaurant_id}/subscription/simulate-cancel", response_model=schemas.RestaurantOut)
def simulate_subscription_cancellation(
    restaurant_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_MANAGER)
):
    """
    Résiliation SIMULÉE, réservée aux établissements de démo — un compte
    jetable n'a jamais de vrai abonnement Stripe (voir stripe_subscription_active),
    donc jamais de vrai portail à ouvrir (`open_billing_portal` répondrait
    404 NO_SUBSCRIPTION). Reproduit exactement l'effet réel de
    `customer.subscription.deleted` (subscription_payments.py) : annuler
    N'IMPORTE QUEL palier, y compris Essentiel, veut dire plus aucun service
    (retour utilisateur, 2026-09-02) — jamais un repli gratuit sur Essentiel.
    """
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    restaurant = _restaurant_or_404(db, restaurant_id)
    if not restaurant.is_demo:
        raise HTTPException(
            status_code=400,
            detail={"code": "NOT_A_DEMO_RESTAURANT", "message": "use the real billing portal instead"},
        )

    restaurant.is_active = False
    restaurant.subscription_downgrade_pending_tier = None
    db.commit()
    db.refresh(restaurant)

    log_event(logger, "subscription.cancellation_simulated", restaurant_id=restaurant_id)
    return schemas.serialize_restaurant(restaurant)
