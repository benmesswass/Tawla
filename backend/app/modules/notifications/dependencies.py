from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.modules.orders.models import Order
from app.modules.staff.models import Staff, StaffRole
from app.modules.staff.security import TOKEN_TYPE, decode_access_token
from app.modules.tables.models import Table

# Code de fermeture applicatif (plage 4000-4999 réservée aux applications) :
# la poignée de main WebSocket n'a pas de 401.
WS_UNAUTHORIZED = 4401


async def _reject(websocket: WebSocket) -> None:
    """
    Refuse une connexion en la fermant avec un code que le frontend peut
    distinguer d'une coupure réseau.

    La poignée de main est acceptée puis immédiatement fermée, à dessein :
    fermer AVANT `accept()` produit un rejet au niveau HTTP, que le navigateur
    rapporte en code 1006 (« fermeture anormale ») indistinguable d'une perte de
    réseau — le client réessaierait alors indéfiniment sur un canal auquel il
    n'aura jamais droit. La socket n'est jamais enregistrée dans le
    `ConnectionManager` et aucun message n'est émis : accepter puis fermer ne
    donne accès à rien.
    """
    await websocket.accept()
    await websocket.close(code=WS_UNAUTHORIZED)


async def authenticate_staff_socket(
    websocket: WebSocket, restaurant_id: int, token: str | None, db: Session, *roles: StaffRole
) -> bool:
    """
    Canaux staff et cuisine : réservés au personnel de CE restaurant, et
    depuis S-4 (audit 2026-08-18) au(x) rôle(s) `roles` — même séparation que
    les routes HTTP équivalentes (`require_role`) : `/ws/staff` pour
    serveur/manager, `/ws/kitchen` pour cuisine/manager.

    Ces canaux diffusaient jusqu'ici en clair, sans aucun contrôle, l'activité
    complète d'un établissement à qui connaissait son identifiant numérique
    (constat 5 de la revue du 2026-08-13).
    """
    if not token:
        await _reject(websocket)
        return False

    try:
        payload = decode_access_token(token)
    except Exception:
        await _reject(websocket)
        return False

    # Défense en profondeur, même motif que `get_current_staff` : `sub` d'un
    # token `platform_admin` (même secret de signature) est aussi un entier,
    # donc `int(payload["sub"])` réussirait quand même — sans ce contrôle, un
    # token admin dont l'ID coïncide avec celui d'un Staff authentifierait
    # silencieusement ce canal comme CE membre du personnel.
    if payload.get("type") != TOKEN_TYPE:
        await _reject(websocket)
        return False

    staff = db.get(Staff, int(payload["sub"]))
    if not staff or not staff.is_active or staff.restaurant_id != restaurant_id:
        await _reject(websocket)
        return False

    if roles and staff.role not in roles:
        await _reject(websocket)
        return False

    return True


async def authenticate_table_socket(
    websocket: WebSocket, restaurant_id: int, qr_token: str, db: Session
) -> Table | None:
    """
    Canal d'une table : réservé au navigateur qui a scanné son QR.

    Il porte ce qui concerne la table sans concerner une commande précise — la
    résolution d'un appel serveur, par exemple, que le client émet avant même
    d'avoir commandé. Le canal `menu` ne pouvait pas s'en charger : il est
    volontairement ouvert et ne porte que la disponibilité des plats, y glisser
    l'activité de service dirait à quiconque ouvre l'URL du menu quelles tables
    appellent un serveur.
    """
    table = db.query(Table).filter(Table.qr_token == qr_token).first()
    if not table or table.restaurant_id != restaurant_id:
        await _reject(websocket)
        return None

    return table


async def authenticate_order_socket(
    websocket: WebSocket, restaurant_id: int, order_id: int, token: str | None, db: Session
) -> bool:
    """
    Canal de suivi d'une commande : réservé au navigateur qui l'a passée, via
    le `public_token` reçu à la création (même règle que les routes HTTP de
    cette commande).
    """
    if not token:
        await _reject(websocket)
        return False

    order = db.get(Order, order_id)
    if not order or order.public_token != token or order.restaurant_id != restaurant_id:
        await _reject(websocket)
        return False

    return True
