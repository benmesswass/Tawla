from datetime import date as date_type
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.subscription import require_tier
from app.modules.staff.dependencies import get_current_staff, require_role
from app.modules.staff.models import Staff, StaffRole
from app.modules.stats import schemas, service
from app.modules.tenants.models import SubscriptionTier

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])

_MANAGER = require_role(StaffRole.MANAGER)
_KITCHEN_OR_MANAGER = require_role(StaffRole.KITCHEN, StaffRole.MANAGER)


# Déclarée avant les routes à segment variable : « ma-soiree » n'est pas un
# identifiant, et n'a aucun `restaurant_id` dans son chemin — le membre
# d'équipe est identifié par son seul JWT, donc rien à deviner.
@router.get("/ma-soiree", response_model=schemas.MyShift)
async def my_shift(
    date: date_type | None = None,
    db: Session = Depends(get_db),
    staff: Staff = Depends(get_current_staff),
):
    """Sa soirée à lui. Ouverte à tous les rôles : le poste chaud prend rarement
    des commandes, l'écran doit répondre zéro plutôt que refuser l'accès."""
    return await service.get_my_shift(db, staff, date or datetime.now(timezone.utc).date())


@router.get("/dashboard/{restaurant_id}", response_model=schemas.DashboardStats)
async def dashboard(
    restaurant_id: int,
    date: date_type | None = None,
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER),
):
    """Vue d'ensemble manager : commandes en cours, timing moyen, performance
    serveurs, plats les plus vendus, heures de pointe — pour une journée donnée
    (par défaut aujourd'hui)."""
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    day = date or datetime.now(timezone.utc).date()
    return await service.get_dashboard_stats(db, restaurant_id, day)


@router.get("/preuve/{restaurant_id}", response_model=schemas.ProofStats)
async def proof(
    restaurant_id: int,
    start: date_type | None = None,
    end: date_type | None = None,
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER),
    _tier: Staff = Depends(require_tier(SubscriptionTier.PRO)),
):
    """
    Les trois chiffres à montrer au patron à la fin d'un pilote : commandes
    perdues, délai commande → cuisine, panier moyen — et les mêmes sur la
    période précédente de même longueur, pour avoir un « avant ».

    Par défaut les 7 derniers jours, aujourd'hui inclus.

    Réservé à Pro et Business (offre à trois paliers, 2026-08-18).
    """
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})

    today = datetime.now(timezone.utc).date()
    period_end = end or today
    period_start = start or (period_end - timedelta(days=6))
    if period_start > period_end:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_PERIOD", "message": "start must not be after end"},
        )
    return await service.get_proof_stats(db, restaurant_id, period_start, period_end)


@router.get("/equipe/{restaurant_id}", response_model=schemas.TeamReport)
async def team_report(
    restaurant_id: int,
    start: date_type | None = None,
    end: date_type | None = None,
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER),
    _tier: Staff = Depends(require_tier(SubscriptionTier.BUSINESS)),
):
    """
    Activité de chaque membre de l'équipe sur une période — la base des primes
    de rendement. Réservé au manager : c'est un document de direction, pas un
    classement à afficher en salle.

    Réservé à Business seul (offre à trois paliers, 2026-08-18).
    """
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})

    today = datetime.now(timezone.utc).date()
    period_end = end or today
    period_start = start or (period_end - timedelta(days=6))
    if period_start > period_end:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_PERIOD", "message": "start must not be after end"},
        )
    return await service.get_team_report(db, restaurant_id, period_start, period_end)


@router.get("/kitchen-today-count/{restaurant_id}", response_model=schemas.KitchenTodayCount)
async def kitchen_today_count(
    restaurant_id: int,
    db: Session = Depends(get_db),
    staff: Staff = Depends(_KITCHEN_OR_MANAGER),
):
    """Compteur du jour pour l'écran cuisine : nombre de commandes déjà
    envoyées en cuisine aujourd'hui — l'état vide de l'écran cuisine n'affiche
    sinon aucune information (audit Phase 8)."""
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    day = datetime.now(timezone.utc).date()
    return await service.get_kitchen_today_count(db, restaurant_id, day)
