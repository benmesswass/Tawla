from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload

from app.core.logging import get_logger, log_event
from app.core.push import send_push_notification
from app.modules.loyalty import schemas as loyalty_schemas
from app.modules.loyalty import service as loyalty_service
from app.modules.menu.models import MenuItem
from app.modules.notifications.manager import manager
from app.modules.orders import schemas
from app.modules.orders.models import Order, OrderItem, OrderStatus, PaymentMethod, PaymentStatus
from app.modules.staff.models import Staff
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

# Au-delà de ce délai, une commande encore en attente de confirmation est
# considérée comme perdue : personne ne l'a prise en charge. C'est la moitié de
# la définition de « commande perdue » utilisée par la page de preuve
# (`stats/service.py::get_proof_stats`), l'autre moitié étant les annulations.
#
# Dix minutes est une proposition, pas une vérité : c'est le seuil à confronter
# au premier restaurant pilote (Phase 13.3 de la ROADMAP). Un service de midi
# tendu peut légitimement mettre 5 minutes à prendre une commande ; au-delà de
# 10, le client a déjà relevé la tête pour chercher un serveur.
ABANDONED_PENDING_AFTER = timedelta(minutes=10)

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


async def list_pending_cash_payments(db: Session, restaurant_id: int) -> list[Order]:
    """
    Tables ayant demandé à payer en espèces mais pas encore encaissées. Séparé
    de `list_active_orders` : le paiement arrive souvent APRÈS "servie", donc
    hors de `ACTIVE_STATUSES` — sans cette requête dédiée, un écran serveur
    rafraîchi après la demande de paiement ne la verrait jamais (même classe
    de bug que l'audit du 2026-08-10 sur les commandes en attente).
    """
    return (
        db.query(Order)
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.payment_method == PaymentMethod.CASH,
            Order.payment_status == PaymentStatus.PENDING,
        )
        .order_by(Order.created_at)
        .all()
    )


def save_push_subscription(db: Session, order_id: int, subscription: schemas.PushSubscriptionIn) -> None:
    """
    Enregistre l'abonnement Web Push du navigateur qui suit cette commande
    — opt-in explicite côté client (voir menu/[qrToken]/page.tsx), jamais
    déclenché automatiquement.
    """
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "order not found"})

    order.push_subscription = subscription.model_dump_json()
    db.commit()


async def create_order(db: Session, payload: schemas.OrderCreate) -> Order:
    # La table est retrouvée par son token de QR code, et le restaurant en est
    # déduit : aucun identifiant numérique n'est accepté du client, donc rien
    # n'est devinable (Phase 12.2).
    table = db.query(Table).filter(Table.qr_token == payload.qr_token).first()
    if not table:
        raise HTTPException(
            status_code=404,
            detail={"code": "INVALID_TABLE_CODE", "message": "invalid table code"},
        )
    if not payload.items:
        raise HTTPException(
            status_code=422,
            detail={"code": "EMPTY_ORDER", "message": "order must contain at least one item"},
        )

    restaurant_id = table.restaurant_id
    order = Order(
        restaurant_id=restaurant_id,
        table_id=table.id,
        scheduled_for=payload.scheduled_for,
        loyalty_phone=payload.loyalty_phone,
    )

    for line in payload.items:
        menu_item = db.get(MenuItem, line.menu_item_id)
        if not menu_item or menu_item.restaurant_id != restaurant_id:
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
                is_shared=line.is_shared,
            )
        )

    db.add(order)
    db.commit()
    db.refresh(order)

    # Enregistre la fiche fidélité dès la commande si le client a saisi son
    # numéro (même s'il n'est jamais passé par une vérification de statut
    # séparée) — le compteur, lui, n'avance qu'au paiement confirmé.
    if order.loyalty_phone:
        loyalty_service.lookup_or_create(
            db, loyalty_schemas.LoyaltyLookup(restaurant_id=order.restaurant_id, phone_number=order.loyalty_phone)
        )

    log_event(
        logger, "order.created",
        restaurant_id=order.restaurant_id, order_id=order.id, table_id=order.table_id,
    )

    # Le serveur assigné à la table doit voir la commande immédiatement.
    await manager.broadcast(
        order.restaurant_id, channel="staff",
        message={
            "event": "order.pending_confirmation",
            "order_id": order.id,
            "table_id": order.table_id,
            "scheduled_for": order.scheduled_for.isoformat() if order.scheduled_for else None,
        },
    )
    return order


async def claim_order(db: Session, order_id: int, staff: Staff) -> Order:
    """
    Prise en charge d'une commande en attente depuis le pool partagé —
    c'est ce qui fait passer une commande de "visible par tous les
    serveurs" à "affectée à Sami", et alimente les stats par serveur
    (dashboard manager, Phase 3).
    """
    order = db.get(Order, order_id)
    if not order or order.restaurant_id != staff.restaurant_id:
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "order not found"})
    if order.status != OrderStatus.PENDING_CONFIRMATION:
        raise HTTPException(
            status_code=409,
            detail={"code": "INVALID_TRANSITION", "message": "order is not pending confirmation"},
        )
    if order.taken_by_staff_id is not None and order.taken_by_staff_id != staff.id:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ALREADY_CLAIMED",
                "message": "order already claimed by another staff member",
                "taken_by_staff_id": order.taken_by_staff_id,
            },
        )

    order.taken_by_staff_id = staff.id
    order.taken_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(order)

    log_event(logger, "order.claimed", restaurant_id=order.restaurant_id, order_id=order.id, staff_id=staff.id)

    await manager.broadcast(
        order.restaurant_id, channel="staff",
        message={
            "event": "order.claimed",
            "order_id": order.id,
            "taken_by_staff_id": staff.id,
            "taken_by_staff_name": staff.name,
        },
    )
    await _broadcast_staff_assigned(order, staff)
    return order


async def _broadcast_staff_assigned(order: Order, staff: Staff) -> None:
    """Le client suit sa commande sur son téléphone — dès qu'un serveur est
    affecté (claim explicite ou auto-claim à la confirmation), on le lui dit
    par son prénom plutôt que de le laisser deviner."""
    await manager.broadcast(
        order.restaurant_id, channel=_order_channel(order.id),
        message={"event": "order.staff_assigned", "order_id": order.id, "staff_name": staff.name},
    )


async def transition_status(db: Session, order_id: int, new_status: OrderStatus, staff: Staff) -> Order:
    order = db.get(Order, order_id)
    if not order or order.restaurant_id != staff.restaurant_id:
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
    newly_assigned = False
    if new_status == OrderStatus.CONFIRMED:
        order.confirmed_at = now
        # Un serveur qui confirme sans être passé par le claim explicite
        # (ex: bouton unique côté UI) se voit quand même attribuer la
        # commande — les stats par serveur ne doivent jamais dépendre d'une
        # étape UI facultative.
        if order.taken_by_staff_id is None:
            order.taken_by_staff_id = staff.id
            order.taken_at = now
            newly_assigned = True
    if new_status == OrderStatus.SENT_TO_KITCHEN:
        order.sent_to_kitchen_at = now
    if new_status == OrderStatus.READY:
        order.ready_at = now
    if new_status == OrderStatus.SERVED:
        order.served_at = now

    db.commit()
    db.refresh(order)

    log_event(
        logger, "order.status_changed",
        restaurant_id=order.restaurant_id, order_id=order.id, new_status=new_status.value,
    )

    if newly_assigned:
        await _broadcast_staff_assigned(order, staff)

    # La cuisine ne doit voir la commande QUE une fois validée par le serveur.
    if new_status == OrderStatus.SENT_TO_KITCHEN:
        await manager.broadcast(
            order.restaurant_id, channel="kitchen",
            message={
                "event": "order.sent_to_kitchen",
                "order_id": order.id,
                "table_id": order.table_id,
                "scheduled_for": order.scheduled_for.isoformat() if order.scheduled_for else None,
                "sent_to_kitchen_at": order.sent_to_kitchen_at.isoformat() if order.sent_to_kitchen_at else None,
                "items": [
                    {
                        "name": i.menu_item_name,
                        "quantity": i.quantity,
                        "notes": i.notes,
                        "is_shared": i.is_shared,
                    }
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
        # Le WebSocket ci-dessus ne réveille que l'onglet resté ouvert au
        # premier plan — la notification push touche aussi le client qui a
        # quitté la page (best-effort, no-op si pas d'abonnement/clés VAPID).
        if order.push_subscription:
            send_push_notification(
                order.push_subscription,
                title="Votre commande est prête !",
                body=f"Commande #{order.id} — un serveur arrive à votre table.",
            )

    # Le client qui a scanné le QR suit sa commande en direct (audit PO —
    # aucune visibilité après "commande envoyée" jusqu'ici).
    await manager.broadcast(
        order.restaurant_id, channel=_order_channel(order.id),
        message={"event": "order.status_changed", "order_id": order.id, "status": new_status.value},
    )

    return order


def _get_payable_order(db: Session, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "order not found"})
    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(
            status_code=409, detail={"code": "ORDER_CANCELLED", "message": "cannot pay a cancelled order"}
        )
    if order.payment_status == PaymentStatus.PAID:
        raise HTTPException(status_code=409, detail={"code": "ALREADY_PAID", "message": "order already paid"})
    return order


async def pay_by_card_simulated(db: Session, order_id: int, tip_amount: float) -> Order:
    """
    Paiement carte — mode simulé (Konnect choisi comme prestataire, mais pas
    de vraie intégration tant qu'un pilote resto réel n'a pas de clés API).
    Couvre le prix total de la commande, pas juste des frais de service.
    Confirmation immédiate, comme le fallback simulé de Darna quand Konnect
    est désactivé — `payment_ref` reste vide ici, prêt à accueillir la
    référence Konnect le jour où l'intégration réelle remplace cette fonction.
    """
    order = _get_payable_order(db, order_id)

    order.payment_method = PaymentMethod.CARD
    order.tip_amount = tip_amount
    order.payment_status = PaymentStatus.PAID
    db.commit()
    db.refresh(order)

    if order.loyalty_phone:
        loyalty_service.record_completed_order(db, order.restaurant_id, order.loyalty_phone)

    log_event(
        logger, "order.paid_card_simulated",
        restaurant_id=order.restaurant_id, order_id=order.id,
        amount=order.total_amount, tip_amount=tip_amount,
    )
    return order


async def request_cash_payment(db: Session, order_id: int) -> Order:
    """Le client demande à payer en espèces — prévient le serveur assigné."""
    order = _get_payable_order(db, order_id)

    order.payment_method = PaymentMethod.CASH
    order.payment_status = PaymentStatus.PENDING
    db.commit()
    db.refresh(order)

    log_event(
        logger, "order.cash_payment_requested",
        restaurant_id=order.restaurant_id, order_id=order.id, amount=order.total_amount,
    )

    # Diffusé sur le canal "staff" partagé (pas d'infra par membre du
    # personnel), mais porte taken_by_staff_id : le frontend n'affiche la
    # demande qu'au serveur dédié à cette table (ou au manager, qui voit
    # tout). Toute commande qui en est là est forcément déjà confirmée, donc
    # taken_by_staff_id est garanti non-nul (auto-claim à la confirmation).
    await manager.broadcast(
        order.restaurant_id, channel="staff",
        message={
            "event": "order.cash_requested",
            "order_id": order.id,
            "table_id": order.table_id,
            "amount": order.total_amount,
            "taken_by_staff_id": order.taken_by_staff_id,
            "loyalty_phone": order.loyalty_phone,
        },
    )
    return order


async def confirm_cash_payment(db: Session, order_id: int, staff: Staff) -> Order:
    """Le serveur confirme avoir encaissé le cash à table."""
    order = db.get(Order, order_id)
    if not order or order.restaurant_id != staff.restaurant_id:
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "order not found"})
    if order.payment_method != PaymentMethod.CASH or order.payment_status != PaymentStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail={"code": "NO_PENDING_CASH_PAYMENT", "message": "no pending cash payment for this order"},
        )

    order.payment_status = PaymentStatus.PAID
    db.commit()
    db.refresh(order)

    if order.loyalty_phone:
        loyalty_service.record_completed_order(db, order.restaurant_id, order.loyalty_phone)

    log_event(
        logger, "order.cash_payment_confirmed",
        restaurant_id=order.restaurant_id, order_id=order.id, staff_id=staff.id,
    )

    # Le client qui a demandé à payer en espèces peut avoir sa page ouverte
    # en attendant que le serveur passe encaisser.
    await manager.broadcast(
        order.restaurant_id, channel=_order_channel(order.id),
        message={"event": "order.payment_confirmed", "order_id": order.id},
    )
    return order
