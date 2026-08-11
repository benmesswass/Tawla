from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.orders import schemas, service
from app.modules.orders.models import OrderStatus
from app.modules.staff.dependencies import get_current_staff, require_role
from app.modules.staff.models import Staff, StaffRole

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])

_WAITER_OR_MANAGER = require_role(StaffRole.WAITER, StaffRole.MANAGER)
_KITCHEN_OR_MANAGER = require_role(StaffRole.KITCHEN, StaffRole.MANAGER)


@router.post("", response_model=schemas.OrderOut, status_code=201)
async def create_order(payload: schemas.OrderCreate, db: Session = Depends(get_db)):
    """Appelé par le client après validation du panier (post-scan QR) — public, pas d'auth."""
    return await service.create_order(db, payload)


@router.get("/by-restaurant/{restaurant_id}/active", response_model=list[schemas.OrderOut])
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
async def get_order(order_id: int, db: Session = Depends(get_db)):
    """Utilisé par l'écran client pour retrouver le suivi de sa commande après un rafraîchissement — public."""
    return await service.get_order(db, order_id)


@router.get("/by-restaurant/{restaurant_id}/pending-cash-payments", response_model=list[schemas.OrderOut])
async def list_pending_cash_payments(
    restaurant_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)
):
    """Tables ayant demandé à payer en espèces, pas encore encaissées."""
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    return await service.list_pending_cash_payments(db, restaurant_id)


@router.post("/{order_id}/pay/card", response_model=schemas.OrderOut)
async def pay_by_card(order_id: int, payload: schemas.PayCardRequest, db: Session = Depends(get_db)):
    """Paiement carte par le client — mode simulé, public comme la création de commande."""
    return await service.pay_by_card_simulated(db, order_id, payload.tip_amount)


@router.post("/{order_id}/pay/cash", response_model=schemas.OrderOut)
async def request_cash_payment(order_id: int, db: Session = Depends(get_db)):
    """Le client demande à payer en espèces — public, prévient le serveur en temps réel."""
    return await service.request_cash_payment(db, order_id)


@router.post("/{order_id}/pay/cash/confirm", response_model=schemas.OrderOut)
async def confirm_cash_payment(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)):
    """Le serveur confirme avoir encaissé le cash à table."""
    return await service.confirm_cash_payment(db, order_id, staff)


@router.post("/{order_id}/claim", response_model=schemas.OrderOut)
async def claim_order(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)):
    """Un serveur prend en charge une commande en attente depuis le pool partagé."""
    return await service.claim_order(db, order_id, staff)


@router.post("/{order_id}/confirm", response_model=schemas.OrderOut)
async def confirm_order(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)):
    """Le serveur confirme la commande APRÈS l'avoir vérifiée avec la table."""
    return await service.transition_status(db, order_id, OrderStatus.CONFIRMED, staff)


@router.post("/{order_id}/send-to-kitchen", response_model=schemas.OrderOut)
async def send_to_kitchen(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)):
    """Validation finale du serveur -> part sur l'écran cuisine."""
    return await service.transition_status(db, order_id, OrderStatus.SENT_TO_KITCHEN, staff)


@router.post("/{order_id}/cancel", response_model=schemas.OrderOut)
async def cancel_order(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)):
    return await service.transition_status(db, order_id, OrderStatus.CANCELLED, staff)


@router.post("/{order_id}/start-preparation", response_model=schemas.OrderOut)
async def start_preparation(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_KITCHEN_OR_MANAGER)):
    """Bouton côté écran cuisine."""
    return await service.transition_status(db, order_id, OrderStatus.IN_PREPARATION, staff)


@router.post("/{order_id}/mark-ready", response_model=schemas.OrderOut)
async def mark_ready(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_KITCHEN_OR_MANAGER)):
    return await service.transition_status(db, order_id, OrderStatus.READY, staff)


@router.post("/{order_id}/mark-served", response_model=schemas.OrderOut)
async def mark_served(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)):
    return await service.transition_status(db, order_id, OrderStatus.SERVED, staff)
