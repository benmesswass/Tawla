from collections import defaultdict

from fastapi import WebSocket

from app.core.logging import get_logger, log_event

logger = get_logger("notifications")


class ConnectionManager:
    """
    Le point le plus sensible du système : c'est ce qui garantit qu'une
    commande arrive bien en cuisine / chez le bon serveur en temps réel.

    Connexions groupées par (restaurant_id, channel) où channel = "staff" ou "kitchen".
    En mono-instance, un dict en mémoire suffit (KISS). Le jour où on
    scale sur plusieurs instances backend, on remplace ce manager par un
    pub/sub Redis SANS toucher aux modules appelants (c'est tout l'intérêt
    d'isoler ça dans une seule classe).
    """

    def __init__(self) -> None:
        self._connections: dict[tuple[int, str], list[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, restaurant_id: int, channel: str) -> None:
        await websocket.accept()
        self._connections[(restaurant_id, channel)].append(websocket)
        log_event(logger, "ws.connected", restaurant_id=restaurant_id, channel=channel)

    def disconnect(self, websocket: WebSocket, restaurant_id: int, channel: str) -> None:
        conns = self._connections.get((restaurant_id, channel), [])
        if websocket in conns:
            conns.remove(websocket)
        log_event(logger, "ws.disconnected", restaurant_id=restaurant_id, channel=channel)

    async def broadcast(self, restaurant_id: int, channel: str, message: dict) -> None:
        conns = self._connections.get((restaurant_id, channel), [])
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, restaurant_id, channel)
        log_event(
            logger,
            "ws.broadcast",
            restaurant_id=restaurant_id,
            channel=channel,
            recipients=len(conns) - len(dead),
            event=message.get("event"),
        )


manager = ConnectionManager()
