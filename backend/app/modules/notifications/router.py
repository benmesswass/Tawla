from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.modules.notifications.dependencies import (
    authenticate_order_socket,
    authenticate_staff_socket,
    authenticate_table_socket,
)
from app.modules.notifications.manager import manager, table_channel

router = APIRouter(tags=["notifications"])


@router.get("/api/v1/notifications/vapid-public-key")
async def get_vapid_public_key():
    """
    Clé publique VAPID pour l'abonnement Web Push côté client — chaîne vide
    si les clés ne sont pas configurées (le frontend n'affiche alors pas
    l'option de notification plutôt que d'échouer silencieusement).
    """
    return {"public_key": settings.vapid_public_key}


async def _pump(websocket: WebSocket, restaurant_id: int, channel: str) -> None:
    """Boucle de maintien de la connexion, identique sur tous les canaux : le
    client envoie des pings, on ne fait que garder la socket ouverte."""
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, restaurant_id, channel)


@router.websocket("/ws/staff/{restaurant_id}")
async def ws_staff(
    websocket: WebSocket, restaurant_id: int, token: str | None = None, db: Session = Depends(get_db)
):
    """
    Le serveur reçoit ici les nouvelles commandes à confirmer pour ses tables.
    Réservé au personnel du restaurant (JWT en paramètre `token` : la poignée
    de main WebSocket du navigateur ne permet pas d'en-tête personnalisé).
    """
    if not await authenticate_staff_socket(websocket, restaurant_id, token, db):
        return
    await manager.connect(websocket, restaurant_id, channel="staff")
    await _pump(websocket, restaurant_id, "staff")


@router.websocket("/ws/kitchen/{restaurant_id}")
async def ws_kitchen(
    websocket: WebSocket, restaurant_id: int, token: str | None = None, db: Session = Depends(get_db)
):
    """Le grand écran cuisine reçoit ici les commandes validées par le serveur."""
    if not await authenticate_staff_socket(websocket, restaurant_id, token, db):
        return
    await manager.connect(websocket, restaurant_id, channel="kitchen")
    await _pump(websocket, restaurant_id, "kitchen")


@router.websocket("/ws/menu/{restaurant_id}")
async def ws_menu(websocket: WebSocket, restaurant_id: int):
    """
    Le client qui parcourt le menu (avant même de commander) doit voir une
    rupture de stock disparaître instantanément, sans attendre de tenter de
    commander pour le découvrir. Volontairement ouvert, et il le reste après la
    Phase 12.2 : ce canal ne porte que la disponibilité des plats — la même
    information que le menu public lui-même, aucune donnée de commande ni
    d'activité de l'établissement.
    """
    await manager.connect(websocket, restaurant_id, channel="menu")
    await _pump(websocket, restaurant_id, "menu")


@router.websocket("/ws/table/{restaurant_id}/{qr_token}")
async def ws_table(websocket: WebSocket, restaurant_id: int, qr_token: str, db: Session = Depends(get_db)):
    """
    Canal de la table scannée : ce qui concerne le client attablé sans
    concerner une commande précise. Aujourd'hui la résolution de son appel
    serveur — sans lui, le bouton « Appeler le serveur » restait grisé jusqu'à
    ce que le client pense à recharger sa page.
    """
    table = await authenticate_table_socket(websocket, restaurant_id, qr_token, db)
    if not table:
        return
    channel = table_channel(table.id)
    await manager.connect(websocket, restaurant_id, channel=channel)
    await _pump(websocket, restaurant_id, channel)


@router.websocket("/ws/order/{restaurant_id}/{order_id}")
async def ws_order(
    websocket: WebSocket,
    restaurant_id: int,
    order_id: int,
    token: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Suivi temps réel côté client après validation de la commande (confirmée /
    en préparation / prête / servie). Réservé au navigateur qui a passé la
    commande, via son `public_token`.
    """
    if not await authenticate_order_socket(websocket, restaurant_id, order_id, token, db):
        return
    channel = f"order-{order_id}"
    await manager.connect(websocket, restaurant_id, channel=channel)
    await _pump(websocket, restaurant_id, channel)
