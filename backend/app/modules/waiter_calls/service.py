from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload

from app.core.dates import service_day_start
from app.core.logging import get_logger, log_event
from app.modules.notifications.manager import manager, table_channel
from app.modules.staff.models import Staff
from app.modules.tables import service as tables_service
from app.modules.waiter_calls import schemas
from app.modules.waiter_calls.models import WaiterCall

logger = get_logger("waiter_calls")


async def create_call(db: Session, payload: schemas.WaiterCallCreate) -> WaiterCall:
    table = tables_service.get_table_by_qr_token(db, payload.qr_token)

    call = WaiterCall(restaurant_id=table.restaurant_id, table_id=table.id)
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
            "table_label": call.table_label,
        },
    )
    return call


async def list_pending_calls(db: Session, restaurant_id: int) -> list[WaiterCall]:
    """Rechargement au montage de l'écran serveur — sans ça, un appel émis
    avant l'ouverture/reconnexion de la page reste invisible."""
    return (
        db.query(WaiterCall)
        .options(selectinload(WaiterCall.table))
        .filter(
            WaiterCall.restaurant_id == restaurant_id,
            WaiterCall.resolved_at.is_(None),
            # Même borne de journée de service que les commandes actives : un
            # appel jamais résolu de la veille n'a plus personne à la table
            # (Phase 19.5).
            WaiterCall.created_at >= service_day_start(),
        )
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
    # Le client aussi doit l'apprendre : sans ça son bouton « Appeler le
    # serveur » restait grisé jusqu'à ce qu'il pense à recharger sa page —
    # alors qu'un serveur venait précisément de répondre à son appel.
    await manager.broadcast(
        call.restaurant_id, channel=table_channel(call.table_id),
        message={"event": "waiter_call.resolved", "call_id": call.id},
    )
    return call
