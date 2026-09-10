from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from fastapi import WebSocket
from starlette.concurrency import run_in_threadpool

from app.core.logging import get_logger, log_event

logger = get_logger("notifications")


@dataclass(frozen=True)
class Diffusion:
    """
    Un message à diffuser, décrit mais **pas encore envoyé**
    (ROADMAP_PRODUCTION.md §P1.1).

    C'est la couture qui a permis de sortir les couches métier de la boucle
    d'événements. Avant, une fonction de service faisait son travail en base
    *et* `await manager.broadcast(...)` : elle devait donc être `async`, donc
    son handler aussi, donc tout le SQLAlchemy synchrone qu'elle exécutait
    bloquait la boucle. Résultat mesuré : 40 commandes simultanées et le
    backend mourait définitivement.

    Désormais une fonction de service est **synchrone** et se contente de
    décrire ce qu'il faudra diffuser ; le routeur, lui, tourne le travail
    bloquant dans un thread (`run_in_threadpool`) puis envoie les messages.
    La règle qui en découle est vérifiable à l'œil, et c'est tout l'intérêt :
    **une fonction de service ne diffuse jamais elle-même.**
    """

    restaurant_id: int
    channel: str
    message: dict


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

    def has_connections(self, restaurant_id: int, channel: str) -> bool:
        return bool(self._connections.get((restaurant_id, channel)))

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


async def executer_puis_diffuser(fonction, *args, **kwargs):
    """
    Le chemin standard d'un routeur vers une fonction de service qui diffuse
    (ROADMAP_PRODUCTION.md §P1.1).

    Deux garanties en une ligne d'appel :

    1. **Le travail bloquant sort de la boucle d'événements.** Les fonctions
       de service exécutent du SQLAlchemy synchrone ; les laisser tourner dans
       un handler `async def` bloquait la boucle à chaque requête base — c'est
       ce qui faisait mourir le backend à 40 commandes simultanées.
    2. **La diffusion se fait ensuite, depuis la boucle**, seul endroit d'où
       l'on peut écrire sur les WebSockets.

    La fonction de service doit rendre `(resultat, diffusions)`. Pour une
    lecture qui ne diffuse rien, appeler `run_in_threadpool` directement
    plutôt que d'inventer une liste vide.
    """
    resultat, diffusions = await run_in_threadpool(fonction, *args, **kwargs)
    await diffuser(diffusions)
    return resultat


async def diffuser(diffusions: Iterable[Diffusion]) -> None:
    """
    Envoie ce qu'une couche métier a décrit — le pendant de `Diffusion`.

    Appelé par les routeurs (et par la boucle WebSocket de table), jamais par
    un module métier. Passer une liste vide est le cas courant et ne coûte
    rien : la plupart des appels ne diffusent pas.
    """
    for diffusion in diffusions:
        await manager.broadcast(diffusion.restaurant_id, diffusion.channel, diffusion.message)


def table_channel(table_id: int) -> str:
    """
    Canal du client attablé, écouté dès le scan du QR — donc avant toute
    commande. Défini ici plutôt que dans un module métier : le canal est
    diffusé par `waiter_calls` et ouvert par `notifications`, et deux
    définitions qui divergent d'un caractère font un message qui n'arrive
    jamais, sans erreur nulle part.
    """
    return f"table-{table_id}"
