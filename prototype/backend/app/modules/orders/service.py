from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload

from app.core.logging import get_logger, log_event
from app.modules.menu.models import MenuItem
from app.modules.notifications.manager import manager
from app.modules.orders import schemas
from app.modules.orders.models import Order, OrderItem, OrderStatus
from app.modules.tables.models import Table

logger = get_logger("orders")

# États qu'un écran serveur/cuisine considère encore "en cours" : à recharger
# au montage de la page, en complément du push WebSocket (qui ne rattrape
# jamais ce qui s'est passé avant la connexion — cf. audit du 2026-08-10).
ACTIVE_STATUSES: set[OrderStatus] = {
    OrderStatus.PENDING_CONFIRMATION,
    OrderStatus.CONFIRMED,
    OrderStatus.SENT_TO_KITCHEN,
    OrderStatus.IN_PREPARATION,
    OrderStatus.READY,
}

# Transitions autorisées : on refuse explicitement tout le reste plutôt
# que de laisser un état incohérent se produire silencieusement.
ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING_CONFIRMATION: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.SENT_TO_KITCHEN, OrderStatus.CANCELLED},
    OrderStatus.SENT_TO_KITCHEN: {OrderStatus.IN_PREPARATION, OrderStatus.CANCELLED},
    OrderStatus.IN_PREPARATION: {OrderStatus.READY},
    OrderStatus.READY: {OrderStatus.SERVED},
    OrderStatus.SERVED: set(),
    OrderStatus.CANCELLED: set(),
}


def _order_channel(order_id: int) -> str:
    """Canal WS dédié à une commande : c'est ce que le client scanne-QR écoute
    pour suivre sa commande en temps réel après validation (audit PO #1)."""
    return f"order-{order_id}"


async def list_active_orders(db: Session, restaurant_id: int) -> list[Order]:
    """
    Rechargement d'état au montage des écrans serveur/cuisine — sans ça, un
    écran ouvert/rafraîchi APRÈS qu'une commande soit passée ne la voit
    jamais (elle ne vit que dans le state React alimenté par le WebSocket).
    """
    return (
        db.query(Order)
        .filter(Order.restaurant_id == restaurant_id, Order.status.in_(ACTIVE_STATUSES))
        .order_by(Order.created_at)
        .all()
    )


async def get_order(db: Session, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "order not found"})
    return order


async def create_order(db: Session, payload: schemas.OrderCreate) -> Order:
    table = db.get(Table, payload.table_id)
    if not table or table.restaurant_id != payload.restaurant_id:
        raise HTTPException(
            status_code=404,
            detail={"code": "TABLE_NOT_FOUND", "message": "table not found for this restaurant"},
        )
    if not payload.items:
        raise HTTPException(
            status_code=422,
            detail={"code": "EMPTY_ORDER", "message": "order must contain at least one item"},
        )

    order = Order(restaurant_id=payload.restaurant_id, table_id=payload.table_id)

    for line in payload.items:
        menu_item = db.get(MenuItem, line.menu_item_id)
        if not menu_item or menu_item.restaurant_id != payload.restaurant_id:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "ITEM_NOT_FOUND",
                    "message": f"menu item {line.menu_item_id} not found",
                    "menu_item_id": line.menu_item_id,
                },
            )
        if not menu_item.is_available:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "ITEM_UNAVAILABLE",
                    "message": f"'{menu_item.name}' is no longer available",
                    "item_name": menu_item.name,
                    "menu_item_id": menu_item.id,
                },
            )

        # Prix figé au moment T : voir commentaire dans models.py
        order.items.append(
            OrderItem(
                menu_item_id=menu_item.id,
                menu_item_name=menu_item.name,
                unit_price=menu_item.price,
                quantity=line.quantity,
                notes=line.notes,
            )
        )

    db.add(order)
    db.commit()
    db.refresh(order)

    log_event(
        logger, "order.created",
        restaurant_id=order.restaurant_id, order_id=order.id, table_id=order.table_id,
    )

    # Le serveur assigné à la table doit voir la commande immédiatement.
    await manager.broadcast(
        order.restaurant_id, channel="staff",
        message={"event": "order.pending_confirmation", "order_id": order.id, "table_id": order.table_id},
    )
    return order


async def transition_status(db: Session, order_id: int, new_status: OrderStatus) -> Order:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "order not found"})

    allowed = ALLOWED_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "INVALID_TRANSITION",
                "message": f"cannot go from '{order.status.value}' to '{new_status.value}'",
                "from": order.status.value,
                "to": new_status.value,
            },
        )

    order.status = new_status
    now = datetime.now(timezone.utc)
    if new_status == OrderStatus.CONFIRMED:
        order.confirmed_at = now
    if new_status == OrderStatus.SENT_TO_KITCHEN:
        order.sent_to_kitchen_at = now

    db.commit()
    db.refresh(order)

    log_event(
        logger, "order.status_changed",
        restaurant_id=order.restaurant_id, order_id=order.id, new_status=new_status.value,
    )

    # La cuisine ne doit voir la commande QUE une fois validée par le serveur.
    if new_status == OrderStatus.SENT_TO_KITCHEN:
        await manager.broadcast(
            order.restaurant_id, channel="kitchen",
            message={
                "event": "order.sent_to_kitchen",
                "order_id": order.id,
                "table_id": order.table_id,
                "items": [
                    {"name": i.menu_item_name, "quantity": i.quantity, "notes": i.notes}
                    for i in order.items
                ],
            },
        )

    # Le plat est prêt : le serveur doit venir le chercher et le servir.
    # Sans ce broadcast, "ready" n'a jamais eu de porte de sortie dans l'UI
    # (audit QA — statut "served" mort).
    if new_status == OrderStatus.READY:
        await manager.broadcast(
            order.restaurant_id, channel="staff",
            message={"event": "order.ready", "order_id": order.id, "table_id": order.table_id},
        )

    # Le client qui a scanné le QR suit sa commande en direct (audit PO —
    # aucune visibilité après "commande envoyée" jusqu'ici).
    await manager.broadcast(
        order.restaurant_id, channel=_order_channel(order.id),
        message={"event": "order.status_changed", "order_id": order.id, "status": new_status.value},
    )

    return order
