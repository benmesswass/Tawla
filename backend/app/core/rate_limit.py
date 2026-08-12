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


def rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    key = (ip, request.url.path)
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
