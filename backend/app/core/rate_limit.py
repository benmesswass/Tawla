import time
from collections import defaultdict

from fastapi import HTTPException, Request

from app.core.config import settings

# Limiteur en mémoire, par IP + route — cohérent avec le choix déjà fait
# pour le gestionnaire de connexions WebSocket (mono-instance assumé, cf.
# notifications/manager.py "en mono-instance, un dict en mémoire suffit").
# But : ralentir un brute-force sur l'auth, pas une garantie absolue — pas
# de dépendance externe (Redis...) pour un besoin aussi restreint.
_WINDOW_SECONDS = 60
_MAX_REQUESTS = 20

_hits: dict[tuple[str, str], list[float]] = defaultdict(list)


def client_ip(request: Request) -> str:
    """
    L'IP du client, pas celle du pair TCP. Derrière l'hébergeur, ce pair est
    toujours son proxy : compter sur lui revient à donner un seul compteur de
    20 requêtes par minute à tout le parc, où le premier téléphone qui en abuse
    bloque le restaurant entier (défaut T3 de l'audit du 2026-08-15).

    `X-Forwarded-For` n'est cru que si le pair est un proxy déclaré : sinon
    l'en-tête vient de n'importe qui, et une IP neuve à chaque requête revient
    à ne plus avoir de limiteur du tout.

    C'est la **dernière** valeur de la liste qui est retenue, pas la première :
    un client peut envoyer son propre en-tête, auquel le proxy ajoute l'IP
    qu'il a réellement constatée. Lire la première rendrait le contournement
    trivial. Corollaire assumé : un seul saut de proxy de confiance — en
    empiler un second (un CDN devant l'hébergeur) ramènerait tout le monde sur
    un compteur commun, sans pour autant rouvrir la faille.
    """
    peer = request.client.host if request.client else "unknown"
    trusted = settings.trusted_proxy_ips
    if not trusted or ("*" not in trusted and peer not in trusted):
        return peer

    forwarded = [part.strip() for part in request.headers.get("x-forwarded-for", "").split(",") if part.strip()]
    return forwarded[-1] if forwarded else peer


def rate_limit(request: Request) -> None:
    key = (client_ip(request), request.url.path)
    now = time.monotonic()
    hits = _hits[key]
    while hits and now - hits[0] > _WINDOW_SECONDS:
        hits.pop(0)
    if len(hits) >= _MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail={"code": "RATE_LIMITED", "message": "too many attempts, try again later"},
        )
    hits.append(now)
