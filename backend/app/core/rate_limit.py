from fastapi import HTTPException, Request

from app.core.etat_partage import magasin

# Limiteur par IP + route. But : ralentir un brute-force sur l'auth, pas une
# garantie absolue.
#
# Le compteur vit dans `core/etat_partage.py::magasin` depuis P2.1 : en mémoire
# par défaut (exactement comme avant), partagé dès que `REDIS_URL` est
# renseignée. Sans ça, N instances derrière un répartiteur donnent N fois le
# plafond à qui tente un brute-force — un compteur par processus n'est pas un
# plafond, c'est une suggestion.
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
        cle = f"debit:{client_ip(request)}:{request.url.path}"
        # Le coup en cours est compté AVANT le test, comme avant : dépasser
        # signifie « ce coup-ci est le coup de trop », pas « le précédent
        # l'était ». Le plafond observable est donc inchangé (le 21ᵉ appel
        # échoue avec un plafond de 20).
        if magasin.incrementer(cle, _WINDOW_SECONDS) > max_requests:
            raise HTTPException(
                status_code=429,
                detail={"code": "RATE_LIMITED", "message": "too many attempts, try again later"},
            )

    return _dependency
