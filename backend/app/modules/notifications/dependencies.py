from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.modules.orders.models import Order
from app.modules.staff.models import Staff
from app.modules.staff.security import decode_access_token

# Code de fermeture applicatif (plage 4000-4999 réservée aux applications) :
# la poignée de main WebSocket n'a pas de 401, on ferme donc avant `accept()`
# avec un code que le frontend peut distinguer d'une coupure réseau.
WS_UNAUTHORIZED = 4401


async def authenticate_staff_socket(websocket: WebSocket, restaurant_id: int, token: str | None, db: Session) -> bool:
    """
    Canaux staff et cuisine : réservés au personnel de CE restaurant.

    Ces canaux diffusaient jusqu'ici en clair, sans aucun contrôle, l'activité
    complète d'un établissement à qui connaissait son identifiant numérique
    (constat 5 de la revue du 2026-08-13). Le contrôle a lieu avant
    `accept()` : une connexion refusée ne reçoit jamais le premier message.
    """
    if not token:
        await websocket.close(code=WS_UNAUTHORIZED)
        return False

    try:
        payload = decode_access_token(token)
    except Exception:
        await websocket.close(code=WS_UNAUTHORIZED)
        return False

    staff = db.get(Staff, int(payload["sub"]))
    if not staff or not staff.is_active or staff.restaurant_id != restaurant_id:
        await websocket.close(code=WS_UNAUTHORIZED)
        return False

    return True


async def authenticate_order_socket(
    websocket: WebSocket, restaurant_id: int, order_id: int, token: str | None, db: Session
) -> bool:
    """
    Canal de suivi d'une commande : réservé au navigateur qui l'a passée, via
    le `public_token` reçu à la création (même règle que les routes HTTP de
    cette commande).
    """
    if not token:
        await websocket.close(code=WS_UNAUTHORIZED)
        return False

    order = db.get(Order, order_id)
    if not order or order.public_token != token or order.restaurant_id != restaurant_id:
        await websocket.close(code=WS_UNAUTHORIZED)
        return False

    return True
