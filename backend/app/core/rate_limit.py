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

# Les commandes viennent d'une salle entière derrière le Wi-Fi du
# restaurant, donc une seule IP publique une fois le client correctement
# identifié (S-2a, CF-Connecting-IP) — mesuré : un plafond pensé pour un
# individu bloquait tout le monde dès qu'une poignée de tables commandaient
# à la même minute (S-2b, audit 2026-08-18). Pas les appels serveur : y
# insister reste une nuisance qu'on veut freiner par table, pas un volume de
# service à absorber. Proposition, pas une vérité : à confronter au premier
# service réel (Phase 23.3), comme SERVICE_DAY_START_HOUR.
ORDER_VOLUME_MAX_REQUESTS = 120

_hits: dict[tuple[str, str], list[float]] = defaultdict(list)

# Balayage global périodique des clés (IP, route) devenues inactives (S-6,
# audit 2026-08-18) : le trim par clé, dans `_dependency`, ne purge que la
# clé de la requête en cours — une IP qui ne revient jamais (client mobile,
# IP publique qui tourne) laisse sa clé en mémoire pour toujours. Fuite lente,
# sans conséquence à l'échelle visée (quelques dizaines d'établissements),
# mais réelle : un balayage périodique suffit, pas de structure plus lourde.
_SWEEP_INTERVAL_SECONDS = _WINDOW_SECONDS
_last_sweep = time.monotonic()


def _sweep_expired(now: float) -> None:
    global _last_sweep
    if now - _last_sweep < _SWEEP_INTERVAL_SECONDS:
        return
    _last_sweep = now
    expired = [key for key, hits in _hits.items() if not hits or now - hits[-1] > _WINDOW_SECONDS]
    for key in expired:
        del _hits[key]


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


def rate_limit(max_requests: int = _MAX_REQUESTS):
    """
    `Depends(rate_limit())` — 20 requêtes/minute par défaut, pensé pour
    freiner un brute-force sur l'auth. `Depends(rate_limit(ORDER_VOLUME_MAX_REQUESTS))`
    pour les routes où le vrai plafond est celui d'un service, pas celui
    d'un individu (S-2b).
    """

    def _dependency(request: Request) -> None:
        key = (client_ip(request), request.url.path)
        now = time.monotonic()
        _sweep_expired(now)
        hits = _hits[key]
        while hits and now - hits[0] > _WINDOW_SECONDS:
            hits.pop(0)
        if len(hits) >= max_requests:
            raise HTTPException(
                status_code=429,
                detail={"code": "RATE_LIMITED", "message": "too many attempts, try again later"},
            )
        hits.append(now)

    return _dependency
