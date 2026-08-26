import re
import unicodedata
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.subscription import SUBSCRIPTION_DURATION_DAYS, get_launch_campaign, launch_promo_grants_used
from app.modules.staff import schemas, security, service
from app.modules.staff.dependencies import get_current_staff, require_role
from app.modules.staff.models import Staff, StaffRole
from app.modules.tenants.models import Restaurant

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Gestion de l'équipe par le manager — préfixe distinct de /auth, qui ne
# porte que la connexion et l'inscription d'un nouvel établissement.
management_router = APIRouter(prefix="/api/v1/staff", tags=["staff"])

_MANAGER = require_role(StaffRole.MANAGER)

# Hash bcrypt valide d'un mot de passe factice — comparé même quand l'email
# n'existe pas, pour ne pas révéler l'existence d'un compte par le timing
# (même stratégie qu'un login public classique, gardée ici par cohérence
# même si le staff n'est pas grand public).
_DUMMY_HASH = "$2b$12$f/0oq4Vt.wjtcqw76TM1DONwSQqoVa/lcI0H/3sTvjhBSBTJBjYHG"  # nosemgrep: generic.secrets.security.detected-bcrypt-hash.detected-bcrypt-hash


def _slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "restaurant"


def _unique_slug(db: Session, name: str) -> str:
    base = _slugify(name)
    slug = base
    suffix = 2
    while db.query(Restaurant).filter(Restaurant.slug == slug).first():
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


@router.get("/launch-promo", response_model=schemas.LaunchPromoStatus)
def launch_promo_status(db: Session = Depends(get_db)):
    """
    Public, sans authentification : la page `/signup` l'interroge AVANT même
    que le visiteur ne s'inscrive, pour savoir s'il faut afficher la bannière
    de campagne et avec quels termes (2026-08-21, réglages configurables
    depuis l'écran admin — voir platform_admin/router.py). `max_grants` est
    la taille TOTALE de la campagne (une donnée marketing, pas un signal
    sensible) ; le nombre de places déjà prises, lui, n'est volontairement
    jamais exposé publiquement — il révélerait la vitesse d'inscription de
    Tawla à qui regarde cette route.
    """
    campaign = get_launch_campaign(db)
    available = launch_promo_grants_used(db) < campaign.max_grants
    return schemas.LaunchPromoStatus(
        available=available, discount_percent=campaign.discount_percent, max_grants=campaign.max_grants
    )


@router.post("/register", response_model=schemas.LoginResponse, status_code=201, dependencies=[Depends(rate_limit())])
def register(payload: schemas.RegisterRequest, db: Session = Depends(get_db)):
    """
    Onboarding self-service d'un nouvel établissement : crée le restaurant
    et son premier compte manager en une seule fois, puis connecte
    immédiatement (même paire access_token/staff que /login) — pas d'étape
    de vérification d'e-mail (aucun service d'envoi en place, cohérent avec
    le reste du projet qui n'a aucune dépendance payante obligatoire).

    `is_active=False` explicitement (2026-08-20) : aucun palier — y compris
    Essentiel — n'est jamais gratuit par défaut, y compris passé par ce
    chemin-là — voir Restaurant.is_active et CLAUDE.md. Le manager verra
    l'écran d'activation (au prix du palier choisi) au premier chargement du
    dashboard tant qu'il n'a pas payé ou qu'aucune dérogation promo n'est
    posée (écran admin). Les restaurants créés par setup_restaurant.py
    (pilotes facturés à la main) gardent le défaut `True`.

    Palier choisi (2026-08-21, cartes tarifs cliquables sur la page
    d'accueil) : `payload.tier`, Essentiel si l'inscrit arrive par un chemin
    générique. Posé sur `subscription_tier` dès la création — ne rend rien
    utilisable avant activation (voir require_active_restaurant), juste
    l'intention commerciale de l'inscrit.

    Offre de lancement (2026-08-21, réglages configurables depuis l'écran
    admin — voir platform_admin/router.py) : tant que la campagne en cours a
    des places, l'inscrit reçoit `launch_promo_discount_percent` figé à la
    réduction actuelle de la campagne, pour LE PALIER QU'IL A CHOISI — un
    historique, jamais recalculé si la campagne change ensuite (voir
    Restaurant.launch_promo_discount_percent). Seule une réduction de 100 %
    active le compte immédiatement, au palier choisi (0 DT ne se facture pas
    via Konnect, voir core/subscription.py::tier_price) — même mécanique
    qu'un paiement (`subscription_period_end` à 30 jours) sauf que
    `has_paid_for_subscription` reste `False`, ce n'est pas un vrai paiement.
    En dessous de 100 %, le compte reste inactif comme d'habitude : le
    manager verra l'écran d'activation, au tarif réduit (voir
    `start_subscription_checkout`). Décompte non verrouillé (pas de
    `SELECT ... FOR UPDATE`) : au pire quelques inscriptions simultanées
    dépassent le plafond de peu, acceptable pour une offre marketing, pas une
    garantie financière.
    """
    email = payload.email.lower()
    if db.query(Staff).filter(Staff.email == email).first():
        raise HTTPException(
            status_code=409, detail={"code": "EMAIL_EXISTS", "message": "an account already exists with this email"}
        )

    restaurant = Restaurant(
        name=payload.restaurant_name,
        slug=_unique_slug(db, payload.restaurant_name),
        subscription_tier=payload.tier,
        is_active=False,
        has_paid_for_subscription=False,
    )
    campaign = get_launch_campaign(db)
    if launch_promo_grants_used(db) < campaign.max_grants:
        restaurant.launch_promo_discount_percent = campaign.discount_percent
        if campaign.discount_percent >= 100:
            restaurant.is_active = True
            restaurant.subscription_period_end = datetime.now(timezone.utc) + timedelta(
                days=SUBSCRIPTION_DURATION_DAYS
            )
    db.add(restaurant)
    db.flush()

    staff = Staff(
        restaurant_id=restaurant.id,
        name=payload.manager_name,
        role=StaffRole.MANAGER,
        email=email,
        password_hash=security.hash_password(payload.password),
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)

    token = security.create_access_token(staff.id, staff.restaurant_id, staff.role.value)
    return schemas.LoginResponse(access_token=token, staff=staff)


@router.post("/login", response_model=schemas.LoginResponse, dependencies=[Depends(rate_limit())])
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    staff = db.query(Staff).filter(Staff.email == payload.email.lower()).first()

    if not staff:
        security.verify_password(payload.password, _DUMMY_HASH)
        raise HTTPException(
            status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "invalid email or password"}
        )

    if not security.verify_password(payload.password, staff.password_hash):
        raise HTTPException(
            status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "invalid email or password"}
        )

    # Mot de passe vérifié d'abord : un ancien salarié apprend que son compte
    # est désactivé, pas qu'un e-mail donné existe dans le système.
    if not staff.is_active:
        raise HTTPException(
            status_code=401, detail={"code": "ACCOUNT_DISABLED", "message": "this account has been disabled"}
        )

    token = security.create_access_token(staff.id, staff.restaurant_id, staff.role.value)
    return schemas.LoginResponse(access_token=token, staff=staff)


@router.get("/me", response_model=schemas.StaffOut)
def me(staff: Staff = Depends(get_current_staff)):
    return staff


@management_router.post("", response_model=schemas.StaffCreatedOut, status_code=201)
def create_staff(payload: schemas.StaffCreate, db: Session = Depends(get_db), manager: Staff = Depends(_MANAGER)):
    """
    Le manager crée les comptes de son équipe (serveurs, cuisine, autres
    managers). Sans cet endpoint, un établissement inscrit en self-service
    n'avait aucun moyen de donner accès au pool serveur ni à l'écran cuisine.
    """
    staff, generated_password = service.create_staff(db, payload, manager)
    return schemas.StaffCreatedOut(staff=staff, temporary_password=generated_password)


@management_router.get("/by-restaurant/{restaurant_id}", response_model=list[schemas.StaffOut])
def list_staff(restaurant_id: int, db: Session = Depends(get_db), manager: Staff = Depends(_MANAGER)):
    if manager.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    return service.list_staff(db, restaurant_id)


@management_router.patch("/{staff_id}", response_model=schemas.StaffOut)
def update_staff(
    staff_id: int,
    payload: schemas.StaffUpdate,
    db: Session = Depends(get_db),
    manager: Staff = Depends(_MANAGER),
):
    """Renommer, changer de rôle, activer ou désactiver un compte. Pas de
    suppression : elle emporterait l'historique des commandes prises en
    charge (cf. commentaire sur `Staff.is_active`)."""
    return service.update_staff(db, staff_id, payload, manager)


@management_router.post("/{staff_id}/reset-password", response_model=schemas.StaffCreatedOut)
def reset_staff_password(staff_id: int, db: Session = Depends(get_db), manager: Staff = Depends(_MANAGER)):
    """Le manager régénère un mot de passe et le transmet de la main à la
    main — il n'est lisible que dans cette réponse."""
    staff, password = service.reset_password(db, staff_id, manager)
    return schemas.StaffCreatedOut(staff=staff, temporary_password=password)
