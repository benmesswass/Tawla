import time
from collections import defaultdict

from fastapi import HTTPException, Request

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
    L'IP du client, pas celle du pair TCP.

    Vérifié en conditions réelles (Phase 20, 19.3, 2026-08-18) : sur Render, le
    pair TCP vu par le conteneur est une IP interne qui change à chaque
    requête (plusieurs nœuds internes en rotation) — ni lui, ni la dernière
    valeur de `X-Forwarded-For` (Render y ajoute la même IP interne en bout de
    chaîne) n'identifient le client. La première valeur, elle, est
    trivialement forgeable par le client lui-même : Cloudflare l'ajoute après
    la sienne sans écraser ce qui précède (confirmé en envoyant un
    `X-Forwarded-For` forgé, retrouvé tel quel en tête de liste côté serveur).

    Seul `CF-Connecting-IP` est fiable : Cloudflare — devant Render, y compris
    sur le sous-domaine `onrender.com` brut, donc pas une config à maintenir —
    le fixe lui-même à l'IP réelle du client, et rejette en 403 à son propre
    niveau toute requête qui tente de le forger (confirmé : un `CF-Connecting-IP`
    forgé n'atteint jamais le conteneur).
    """
    cf_connecting_ip = request.headers.get("cf-connecting-ip")
    if cf_connecting_ip:
        return cf_connecting_ip
    return request.client.host if request.client else "unknown"


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
