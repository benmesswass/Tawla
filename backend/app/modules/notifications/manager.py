import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from fastapi import WebSocket
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.etat_partage import magasin
from app.core.logging import get_logger, log_event

CANAL_DIFFUSION = "tawla:diffusion"

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

    Connexions groupées par (restaurant_id, channel) où channel = "staff" ou
    "kitchen".

    **Le registre des sockets reste local, et c'est obligatoire** : une
    WebSocket est une connexion TCP détenue par un seul processus, aucun
    magasin partagé ne peut la détenir à sa place. Ce qui voyage entre
    instances depuis P2.1, c'est le **message**, pas la connexion.

    Deux chemins, selon `magasin.diffuse_entre_instances` :

    - **mémoire** (défaut, aucune `REDIS_URL`) — `broadcast` écrit directement
      sur les sockets locales. Comportement identique à avant P2.1.
    - **Redis** — `broadcast` se contente de **publier** ; c'est l'écoute de
      fond (`ecouter_les_diffusions`, lancée au démarrage de l'app) qui livre
      aux sockets locales, sur chaque instance, **y compris celle qui a
      publié**. Publier *et* livrer localement enverrait deux fois le même
      message aux clients de l'instance émettrice — d'où les deux chemins
      exclusifs plutôt qu'un seul chemin auquel on ajoute une publication.
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
        if magasin.diffuse_entre_instances:
            await run_in_threadpool(
                magasin.publier,
                CANAL_DIFFUSION,
                json.dumps(
                    {"restaurant_id": restaurant_id, "channel": channel, "message": message},
                    ensure_ascii=False,
                ),
            )
            return
        await self.livrer_en_local(restaurant_id, channel, message)

    async def livrer_en_local(self, restaurant_id: int, channel: str, message: dict) -> None:
        """
        L'écriture réelle sur les sockets de CE processus. Seul point d'où
        l'on écrit sur une WebSocket, appelé soit directement (mode mémoire),
        soit par l'écoute de fond (mode Redis).
        """
        conns = list(self._connections.get((restaurant_id, channel), []))
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


DELAI_RECONNEXION_SECONDES = 1.0


async def ecouter_les_diffusions() -> None:
    """
    L'écoute de fond qui livre aux sockets de CE processus les messages
    publiés par n'importe quelle instance (ROADMAP_PRODUCTION.md §P2.1).

    Lancée au démarrage de l'app et **seulement en mode Redis** ; sans
    `REDIS_URL`, `broadcast` livre en direct et il n'y a rien à écouter.

    Boucle de reconnexion volontaire : si Redis devient injoignable une
    minute, l'instance doit se rabrancher toute seule quand il revient. Sans
    elle, la tâche mourrait au premier hoquet réseau et cette instance
    cesserait **silencieusement** de recevoir les commandes des autres — la
    panne la plus coûteuse du système, et la plus difficile à voir.
    """
    import redis.asyncio as redis_async

    while True:
        client = redis_async.Redis.from_url(settings.redis_url, decode_responses=True)
        canal = client.pubsub(ignore_subscribe_messages=True)
        try:
            await canal.subscribe(CANAL_DIFFUSION)
            log_event(logger, "ws.ecoute_demarree", canal=CANAL_DIFFUSION)
            async for brut in canal.listen():
                if brut.get("type") != "message":
                    continue
                await _livrer(brut["data"])
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("ws.ecoute_interrompue")
            await asyncio.sleep(DELAI_RECONNEXION_SECONDES)
        finally:
            await _fermer(canal)
            await _fermer(client)


async def _livrer(charge_brute: str) -> None:
    try:
        charge = json.loads(charge_brute)
    except (ValueError, TypeError):
        # Message illisible sur le canal : on le jette et on continue. Un
        # `raise` ici tuerait l'écoute de toute l'instance pour un octet de
        # travers.
        logger.exception("ws.diffusion_illisible")
        return
    await manager.livrer_en_local(charge["restaurant_id"], charge["channel"], charge["message"])


async def _fermer(ressource) -> None:
    try:
        await ressource.aclose()
    except Exception:
        pass

