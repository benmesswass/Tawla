from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.modules.staff.dependencies import get_current_staff, require_role
from app.modules.staff.models import Staff, StaffRole
from app.modules.waiter_calls import schemas, service

router = APIRouter(prefix="/api/v1/waiter-calls", tags=["waiter-calls"])

_WAITER_OR_MANAGER = require_role(StaffRole.WAITER, StaffRole.MANAGER)


@router.post(
    "", response_model=schemas.WaiterCallOut, status_code=201, dependencies=[Depends(rate_limit())]
)
async def create_call(payload: schemas.WaiterCallCreate, db: Session = Depends(get_db)):
    """
    Appelé par le client depuis la page menu — public et lié au `qr_token` de
    sa table, comme la création de commande.

    Le limiteur borne la nuisance restante : le QR est physiquement sur la
    table, donc un client attablé peut insister. On appelle le serveur quelques
    fois par repas, pas vingt.
    """
    return await service.create_call(db, payload)


@router.get("/by-restaurant/{restaurant_id}/pending", response_model=list[schemas.WaiterCallOut])
async def list_pending_calls(
    restaurant_id: int, db: Session = Depends(get_db), staff: Staff = Depends(get_current_staff)
):
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    return await service.list_pending_calls(db, restaurant_id)


@router.post("/{call_id}/resolve", response_model=schemas.WaiterCallOut)
async def resolve_call(call_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)):
    return await service.resolve_call(db, call_id, staff)
