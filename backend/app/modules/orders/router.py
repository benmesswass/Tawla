from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import ORDER_VOLUME_MAX_REQUESTS, rate_limit
from app.modules.orders import schemas, service
from app.modules.orders.dependencies import get_order_by_token
from app.modules.orders.models import Order, OrderStatus
from app.modules.staff.dependencies import get_current_staff, require_role
from app.modules.staff.models import Staff, StaffRole

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])

_WAITER_OR_MANAGER = require_role(StaffRole.WAITER, StaffRole.MANAGER)
_KITCHEN_OR_MANAGER = require_role(StaffRole.KITCHEN, StaffRole.MANAGER)


@router.post(
    "",
    response_model=schemas.OrderCreatedOut,
    status_code=201,
    # Toute la salle commande depuis le même Wi-Fi, donc la même IP (S-2b).
    dependencies=[Depends(rate_limit(ORDER_VOLUME_MAX_REQUESTS))],
)
async def create_order(payload: schemas.OrderCreate, db: Session = Depends(get_db)):
    """
    Appelé par le client après validation du panier — sans compte, mais avec le
    `qr_token` de la table qu'il vient de scanner. La réponse contient le
    `public_token` de la commande : c'est la seule fois où il est renvoyé, le
    navigateur doit le garder pour suivre et payer sa commande.
    """
    return await service.create_order(db, payload)


@router.get("/by-restaurant/{restaurant_id}/active", response_model=list[schemas.OrderOutStaff])
async def list_active_orders(
    restaurant_id: int, db: Session = Depends(get_db), staff: Staff = Depends(get_current_staff)
):
    """
    Rechargement d'état pour les écrans serveur/cuisine au montage : le
    WebSocket seul ne rattrape jamais ce qui s'est passé avant la connexion.
    """
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    return await service.list_active_orders(db, restaurant_id)


@router.get("/{order_id}", response_model=schemas.OrderOut)
async def get_order(order: Order = Depends(get_order_by_token)):
    """
    Suivi de commande côté client, y compris après un rafraîchissement de page.
    Sans compte, mais lié : exige l'en-tête `X-Order-Token` reçu à la création.
    """
    return order


@router.get(
    "/by-restaurant/{restaurant_id}/pending-cash-payments", response_model=list[schemas.OrderOutStaff]
)
async def list_pending_cash_payments(
    restaurant_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)
):
    """Tables ayant demandé à payer en espèces, pas encore encaissées."""
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    return await service.list_pending_cash_payments(db, restaurant_id)


@router.post("/{order_id}/push-subscription", status_code=204)
async def save_push_subscription(
    payload: schemas.PushSubscriptionIn,
    order: Order = Depends(get_order_by_token),
    db: Session = Depends(get_db),
):
    """
    Opt-in du client pour être notifié quand SA commande passe « prête ».
    Lié au token : sans ça, n'importe qui pouvait remplacer l'abonnement push
    d'une commande et détourner sa notification.
    """
    service.save_push_subscription(db, order.id, payload)


@router.post("/{order_id}/pay/card", response_model=schemas.OrderOut)
async def pay_by_card(
    payload: schemas.PayCardRequest,
    order: Order = Depends(get_order_by_token),
    db: Session = Depends(get_db),
):
    """
    Paiement carte par le client — mode simulé. Lié au token : sans ça,
    n'importe qui pouvait marquer n'importe quelle commande « payée » sans
    régler un dinar (constat 2 de la revue).
    """
    return await service.pay_by_card_simulated(db, order.id, payload.tip_amount)


@router.post("/{order_id}/pay/cash", response_model=schemas.OrderOut)
async def request_cash_payment(
    payload: schemas.PayCashRequest = schemas.PayCashRequest(),
    order: Order = Depends(get_order_by_token),
    db: Session = Depends(get_db),
):
    """Le client demande à payer en espèces — prévient le serveur en temps réel."""
    return await service.request_cash_payment(db, order.id, payload.tip_amount)


@router.post("/{order_id}/pay/cash/confirm", response_model=schemas.OrderOutStaff)
async def confirm_cash_payment(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)):
    """Le serveur confirme avoir encaissé le cash à table."""
    return await service.confirm_cash_payment(db, order_id, staff)


@router.post("/{order_id}/claim", response_model=schemas.OrderOutStaff)
async def claim_order(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)):
    """Un serveur prend en charge une commande en attente depuis le pool partagé."""
    return await service.claim_order(db, order_id, staff)


@router.post("/{order_id}/confirm", response_model=schemas.OrderOutStaff)
async def confirm_order(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)):
    """Le serveur confirme la commande APRÈS l'avoir vérifiée avec la table."""
    return await service.transition_status(db, order_id, OrderStatus.CONFIRMED, staff)


@router.post("/{order_id}/send-to-kitchen", response_model=schemas.OrderOutStaff)
async def send_to_kitchen(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)):
    """Validation finale du serveur -> part sur l'écran cuisine."""
    return await service.transition_status(db, order_id, OrderStatus.SENT_TO_KITCHEN, staff)


@router.post("/{order_id}/cancel", response_model=schemas.OrderOutStaff)
async def cancel_order(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)):
    return await service.transition_status(db, order_id, OrderStatus.CANCELLED, staff)


@router.post("/{order_id}/start-preparation", response_model=schemas.OrderOutStaff)
async def start_preparation(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_KITCHEN_OR_MANAGER)):
    """Bouton côté écran cuisine."""
    return await service.transition_status(db, order_id, OrderStatus.IN_PREPARATION, staff)


@router.post("/{order_id}/mark-ready", response_model=schemas.OrderOutStaff)
async def mark_ready(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_KITCHEN_OR_MANAGER)):
    return await service.transition_status(db, order_id, OrderStatus.READY, staff)


@router.post("/{order_id}/mark-served", response_model=schemas.OrderOutStaff)
async def mark_served(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)):
    return await service.transition_status(db, order_id, OrderStatus.SERVED, staff)
