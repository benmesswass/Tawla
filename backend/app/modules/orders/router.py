from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.orders import schemas, service
from app.modules.orders.models import OrderStatus

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.post("", response_model=schemas.OrderOut, status_code=201)
async def create_order(payload: schemas.OrderCreate, db: Session = Depends(get_db)):
    """Appelé par le client après validation du panier (post-scan QR)."""
    return await service.create_order(db, payload)


@router.get("/by-restaurant/{restaurant_id}/active", response_model=list[schemas.OrderOut])
async def list_active_orders(restaurant_id: int, db: Session = Depends(get_db)):
    """
    Rechargement d'état pour les écrans serveur/cuisine au montage : le
    WebSocket seul ne rattrape jamais ce qui s'est passé avant la connexion.
    """
    return await service.list_active_orders(db, restaurant_id)


@router.get("/{order_id}", response_model=schemas.OrderOut)
async def get_order(order_id: int, db: Session = Depends(get_db)):
    """Utilisé par l'écran client pour retrouver le suivi de sa commande après un rafraîchissement."""
    return await service.get_order(db, order_id)


@router.post("/{order_id}/confirm", response_model=schemas.OrderOut)
async def confirm_order(order_id: int, db: Session = Depends(get_db)):
    """Le serveur confirme la commande APRÈS l'avoir vérifiée avec la table."""
    return await service.transition_status(db, order_id, OrderStatus.CONFIRMED)


@router.post("/{order_id}/send-to-kitchen", response_model=schemas.OrderOut)
async def send_to_kitchen(order_id: int, db: Session = Depends(get_db)):
    """Validation finale du serveur -> part sur l'écran cuisine."""
    return await service.transition_status(db, order_id, OrderStatus.SENT_TO_KITCHEN)


@router.post("/{order_id}/cancel", response_model=schemas.OrderOut)
async def cancel_order(order_id: int, db: Session = Depends(get_db)):
    return await service.transition_status(db, order_id, OrderStatus.CANCELLED)


@router.post("/{order_id}/start-preparation", response_model=schemas.OrderOut)
async def start_preparation(order_id: int, db: Session = Depends(get_db)):
    """Bouton côté écran cuisine."""
    return await service.transition_status(db, order_id, OrderStatus.IN_PREPARATION)


@router.post("/{order_id}/mark-ready", response_model=schemas.OrderOut)
async def mark_ready(order_id: int, db: Session = Depends(get_db)):
    return await service.transition_status(db, order_id, OrderStatus.READY)


@router.post("/{order_id}/mark-served", response_model=schemas.OrderOut)
async def mark_served(order_id: int, db: Session = Depends(get_db)):
    return await service.transition_status(db, order_id, OrderStatus.SERVED)
