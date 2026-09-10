from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.modules.notifications.dependencies import (
    authenticate_order_socket,
    authenticate_staff_socket,
    authenticate_table_socket,
)
from app.modules.notifications.manager import manager, table_channel
from app.modules.orders import schemas as orders_schemas
from app.modules.orders import service as orders_service
from app.modules.orders import table_cart
from app.modules.staff.models import StaffRole
from app.modules.tables import roster as table_roster
from app.modules.tables import split_mode as table_split_mode
from app.modules.tables.models import Table

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
    Réservé au personnel serveur/manager du restaurant (JWT en paramètre
    `token` : la poignée de main WebSocket du navigateur ne permet pas
    d'en-tête personnalisé).
    """
    if not await authenticate_staff_socket(websocket, restaurant_id, token, db, StaffRole.WAITER, StaffRole.MANAGER):
        return
    await manager.connect(websocket, restaurant_id, channel="staff")
    await _pump(websocket, restaurant_id, "staff")


@router.websocket("/ws/kitchen/{restaurant_id}")
async def ws_kitchen(
    websocket: WebSocket, restaurant_id: int, token: str | None = None, db: Session = Depends(get_db)
):
    """Le grand écran cuisine reçoit ici les commandes validées par le serveur.
    Réservé au personnel cuisine/manager, comme les routes HTTP équivalentes."""
    if not await authenticate_staff_socket(websocket, restaurant_id, token, db, StaffRole.KITCHEN, StaffRole.MANAGER):
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
    concerner une commande précise. Porte la résolution de l'appel serveur —
    sans lui, le bouton « Appeler le serveur » restait grisé jusqu'à ce que le
    client pense à recharger sa page — et, depuis le chantier « panier
    synchronisé multi-appareils » (`ROADMAP.md` §Override), les mutations du
    panier partagé de la table : tout appareil qui scanne ce QR reçoit l'état
    courant à la connexion, puis chaque mise à jour, et peut valider pour
    toute la table (`table_cart.py`). Porte aussi, depuis la même extension,
    qui commande sous quel prénom (`tables/roster.py`) — purement déclaratif,
    jamais lu pour une règle métier.
    """
    table = await authenticate_table_socket(websocket, restaurant_id, qr_token, db)
    if not table:
        return
    channel = table_channel(table.id)
    await manager.connect(websocket, restaurant_id, channel=channel)
    # Rattrapage : un appareil qui rejoint une table déjà en train de composer
    # son panier (ou déjà déclarée par un autre convive) doit voir tout de
    # suite ce que les autres ont déjà fait, sans attendre leur prochaine
    # mutation.
    await websocket.send_json(table_cart.snapshot_message(table.id))
    await websocket.send_json(table_roster.roster_message(table.id))
    await websocket.send_json(table_split_mode.split_mode_message(table.id))
    await _pump_table(websocket, restaurant_id, table, db, channel)


def _cart_error_payload(exc: HTTPException) -> dict:
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "ERROR", "message": str(exc.detail)}
    return {"event": "cart.error", **detail}


async def _pump_table(websocket: WebSocket, restaurant_id: int, table: Table, db: Session, channel: str) -> None:
    """
    Boucle de la table : contrairement à `_pump`, les messages entrants sont
    lus et traités (panier partagé) plutôt que seulement gardés pour détecter
    la déconnexion.
    """
    try:
        while True:
            raw = await websocket.receive_json()
            action = raw.get("action") if isinstance(raw, dict) else None
            try:
                if action == "cart.set":
                    item = orders_schemas.OrderItemCreate.model_validate(
                        {k: v for k, v in raw.items() if k != "action"}
                    )
                    table_cart.validate_cart_line(db, restaurant_id, item)
                    table_cart.table_cart_store.set_line(table.id, item)
                    await manager.broadcast(restaurant_id, channel, table_cart.snapshot_message(table.id))
                elif action == "cart.validate":
                    client_order_id = raw.get("client_order_id")
                    await orders_service.create_order_from_table_cart(db, table, client_order_id=client_order_id)
                elif action == "identity.set":
                    device_key = str(raw.get("device_key", ""))[:80]
                    name = str(raw.get("name", ""))
                    if device_key:
                        table_roster.table_roster_store.set_name(table.id, device_key, name)
                        await manager.broadcast(restaurant_id, channel, table_roster.roster_message(table.id))
                elif action == "identity.add_guest":
                    name = str(raw.get("name", ""))
                    table_roster.table_roster_store.add_guest(table.id, name)
                    await manager.broadcast(restaurant_id, channel, table_roster.roster_message(table.id))
                elif action == "split_mode.set":
                    mode = str(raw.get("mode", ""))
                    table_split_mode.table_split_mode_store.set_mode(table.id, mode)
                    await manager.broadcast(restaurant_id, channel, table_split_mode.split_mode_message(table.id))
                # Action inconnue ou message malformé sans champ "action" :
                # ignoré plutôt que de casser la connexion — un client d'une
                # version plus récente ou plus ancienne ne doit jamais faire
                # tomber le canal des autres appareils de la table.
            except HTTPException as exc:
                # Rollback défensif : aucune écriture n'a pu aboutir sur ces
                # chemins (échec de validation avant tout commit), mais la
                # session reste ouverte pour toute la durée de la connexion —
                # sans ça, une transaction implicite resterait ouverte sans
                # raison entre deux messages du même appareil.
                db.rollback()
                await websocket.send_json(_cart_error_payload(exc))
            except (ValidationError, TypeError, ValueError):
                db.rollback()
                await websocket.send_json(
                    {"event": "cart.error", "code": "INVALID_MESSAGE", "message": "malformed cart message"}
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket, restaurant_id, channel)
        # Plus aucune purge sur déconnexion (2026-09-09, demande de Wassim) :
        # le panier/les convives d'une table survivent à toute coupure, aussi
        # longue soit-elle — les clients doivent pouvoir prendre leur temps
        # pour commander sans risquer de perdre leur panier en route. Seule
        # `tables/service.py::release_table` (bouton dédié serveur/manager)
        # les remet à zéro désormais. Le risque de fuite mémoire que l'ancien
        # mécanisme corrigeait (PR #160) reste couvert : `release_table` vide
        # ces stores dès que la table repart, dans le cas normal comme dans
        # celui d'une table réellement abandonnée sans commande.


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
