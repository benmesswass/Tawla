from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.modules.notifications.manager import manager

router = APIRouter(tags=["notifications"])


@router.get("/api/v1/notifications/vapid-public-key")
async def get_vapid_public_key():
    """
    Clé publique VAPID pour l'abonnement Web Push côté client — chaîne vide
    si les clés ne sont pas configurées (le frontend n'affiche alors pas
    l'option de notification plutôt que d'échouer silencieusement).
    """
    return {"public_key": settings.vapid_public_key}


@router.websocket("/ws/staff/{restaurant_id}")
async def ws_staff(websocket: WebSocket, restaurant_id: int):
    """Le serveur reçoit ici les nouvelles commandes à confirmer pour ses tables."""
    await manager.connect(websocket, restaurant_id, channel="staff")
    try:
        while True:
            await websocket.receive_text()  # keep-alive / ping du client
    except WebSocketDisconnect:
        manager.disconnect(websocket, restaurant_id, channel="staff")


@router.websocket("/ws/kitchen/{restaurant_id}")
async def ws_kitchen(websocket: WebSocket, restaurant_id: int):
    """Le grand écran cuisine reçoit ici les commandes validées par le serveur."""
    await manager.connect(websocket, restaurant_id, channel="kitchen")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, restaurant_id, channel="kitchen")


@router.websocket("/ws/menu/{restaurant_id}")
async def ws_menu(websocket: WebSocket, restaurant_id: int):
    """
    Le client qui parcourt le menu (avant même de commander) doit voir une
    rupture de stock disparaître instantanément, sans attendre de tenter de
    commander pour le découvrir. Public comme le reste du parcours client —
    pas d'auth, pas de donnée sensible sur ce canal.
    """
    await manager.connect(websocket, restaurant_id, channel="menu")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, restaurant_id, channel="menu")


@router.websocket("/ws/order/{restaurant_id}/{order_id}")
async def ws_order(websocket: WebSocket, restaurant_id: int, order_id: int):
    """
    Suivi temps réel côté client après validation de la commande (confirmée
    / en préparation / prête / servie) — canal ajouté suite à l'audit du
    2026-08-10 : le client n'avait jusqu'ici aucune visibilité après avoir
    commandé, alors que toute l'infra WebSocket existait déjà pour
    serveur/cuisine.
    """
    channel = f"order-{order_id}"
    await manager.connect(websocket, restaurant_id, channel=channel)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, restaurant_id, channel=channel)
