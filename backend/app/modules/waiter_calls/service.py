from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_event
from app.modules.notifications.manager import manager
from app.modules.staff.models import Staff
from app.modules.tables.models import Table
from app.modules.waiter_calls import schemas
from app.modules.waiter_calls.models import WaiterCall

logger = get_logger("waiter_calls")


async def create_call(db: Session, payload: schemas.WaiterCallCreate) -> WaiterCall:
    table = db.get(Table, payload.table_id)
    if not table or table.restaurant_id != payload.restaurant_id:
        raise HTTPException(
            status_code=404,
            detail={"code": "TABLE_NOT_FOUND", "message": "table not found for this restaurant"},
        )

    call = WaiterCall(restaurant_id=payload.restaurant_id, table_id=payload.table_id)
    db.add(call)
    db.commit()
    db.refresh(call)

    log_event(logger, "waiter_call.created", restaurant_id=call.restaurant_id, table_id=call.table_id)

    # Diffusé sur le même canal "staff" que les commandes/demandes de
    # paiement cash — pas de canal dédié pour un événement aussi ponctuel.
    await manager.broadcast(
        call.restaurant_id, channel="staff",
        message={
            "event": "waiter_call.created",
            "call_id": call.id,
            "table_id": call.table_id,
        },
    )
    return call


async def list_pending_calls(db: Session, restaurant_id: int) -> list[WaiterCall]:
    """Rechargement au montage de l'écran serveur — sans ça, un appel émis
    avant l'ouverture/reconnexion de la page reste invisible."""
    return (
        db.query(WaiterCall)
        .filter(WaiterCall.restaurant_id == restaurant_id, WaiterCall.resolved_at.is_(None))
        .order_by(WaiterCall.created_at)
        .all()
    )


async def resolve_call(db: Session, call_id: int, staff: Staff) -> WaiterCall:
    call = db.get(WaiterCall, call_id)
    if not call or call.restaurant_id != staff.restaurant_id:
        raise HTTPException(status_code=404, detail={"code": "CALL_NOT_FOUND", "message": "waiter call not found"})
    if call.resolved_at is not None:
        raise HTTPException(
            status_code=409, detail={"code": "ALREADY_RESOLVED", "message": "waiter call already resolved"}
        )

    call.resolved_at = datetime.now(timezone.utc)
    call.resolved_by_staff_id = staff.id
    db.commit()
    db.refresh(call)

    log_event(logger, "waiter_call.resolved", restaurant_id=call.restaurant_id, call_id=call.id, staff_id=staff.id)

    await manager.broadcast(
        call.restaurant_id, channel="staff",
        message={"event": "waiter_call.resolved", "call_id": call.id},
    )
    return call
