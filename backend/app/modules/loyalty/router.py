from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.loyalty import schemas, service
from app.modules.staff.dependencies import require_role
from app.modules.staff.models import Staff, StaffRole

router = APIRouter(prefix="/api/v1/loyalty", tags=["loyalty"])

_WAITER_OR_MANAGER = require_role(StaffRole.WAITER, StaffRole.MANAGER)


@router.post("/lookup", response_model=schemas.LoyaltyMemberOut)
def lookup_loyalty(payload: schemas.LoyaltyLookup, db: Session = Depends(get_db)):
    """Public — appelé par le client quand il saisit son numéro au moment de commander."""
    return service.lookup_or_create(db, payload)


@router.get("/by-restaurant/{restaurant_id}/member", response_model=schemas.LoyaltyMemberOut)
def get_member_for_staff(
    restaurant_id: int,
    phone_number: str = Query(...),
    db: Session = Depends(get_db),
    staff: Staff = Depends(_WAITER_OR_MANAGER),
):
    """Le serveur consulte la fiche fidélité d'une table pour vérifier une récompense annoncée par le client."""
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    return service.get_member_for_staff(db, restaurant_id, phone_number)


@router.post("/{member_id}/redeem", response_model=schemas.LoyaltyMemberOut)
def redeem_reward(member_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)):
    """Le serveur confirme avoir donné l'article offert — remet le compteur de récompense à zéro."""
    return service.redeem_reward(db, member_id, staff.restaurant_id)
