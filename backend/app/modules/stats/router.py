from datetime import date as date_type
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.staff.dependencies import require_role
from app.modules.staff.models import Staff, StaffRole
from app.modules.stats import schemas, service

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])

_MANAGER = require_role(StaffRole.MANAGER)


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
