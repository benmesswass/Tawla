"""
Le billet d'entrée des canaux WebSocket du personnel
(ROADMAP_PRODUCTION.md §P2.4, F9).

**Le problème.** Le JWT du personnel n'a volontairement pas de claim `exp`
(décision produit de Wassim, 2026-09-09 : la seule déconnexion voulue est le
bouton « Se déconnecter », jamais une expiration qui éjecterait un serveur en
plein coup de feu). Et la poignée de main WebSocket d'un navigateur ne permet
aucun en-tête personnalisé : le jeton devait donc voyager en **query string**.

Les URLs, elles, sont journalisées — par Cloudflare, par l'hébergeur, par tout
proxy sur le trajet. Un jeton éternel retrouvé dans un log d'accès reste
valide **indéfiniment**, et rien ne permet de le révoquer.

**La correction garde l'intention produit intacte.** Ce n'est pas la session
du serveur en salle qui devient courte — elle ne change pas d'un iota — c'est
le **jeton de transport** qui devient jetable. Le JWT long ne quitte plus
jamais l'en-tête `Authorization` ; ce qui passe dans l'URL est un billet
opaque, valable **30 secondes** et **une seule fois**. Retrouvé dans un log,
il est déjà consommé ou déjà périmé.

Deux gardes, pas une seule, parce qu'elles couvrent deux fuites différentes :

- **usage unique** — contre le billet lu dans un log d'accès *avant* sa
  péremption ;
- **durée courte** — contre le billet demandé puis jamais utilisé, qui
  resterait sinon valable pour toujours.

Le billet identifie une **personne**, pas un canal : c'est le socket qui
autorise ensuite le canal, en relisant le rôle et le restaurant en base
(`notifications/dependencies.py::authenticate_staff_socket`). Un billet
délivré à la cuisine n'ouvre donc pas l'écran serveur, exactement comme le JWT
ne le permettait pas.

Stocké dans `core/etat_partage.py::magasin`, et ce n'est pas un détail depuis
P2.1 : le billet est délivré par l'instance qui a servi la requête HTTP et
consommé par celle qui reçoit la connexion WebSocket, et rien ne garantit que
ce soit la même.
"""
import json
import secrets
import time

from app.core.etat_partage import magasin

# 30 secondes : le temps entre « je demande un billet » et « j'ouvre la
# socket » est celui d'un aller-retour HTTP. Assez large pour un réseau
# médiocre, assez court pour qu'un billet oublié dans un log soit inerte.
DUREE_BILLET_SECONDES = 30

CHAMP = "billet"


def _cle(billet: str) -> str:
    return f"billet-ws:{billet}"


def creer_billet(staff_id: int) -> str:
    """
    Délivre un billet pour ce membre du personnel. Appelé depuis une route
    **déjà authentifiée** par le JWT dans l'en-tête `Authorization` — c'est
    tout l'intérêt : l'échange se fait là où le jeton long est en sécurité.
    """
    billet = secrets.token_urlsafe(32)
    magasin.ecrire(
        _cle(billet),
        CHAMP,
        json.dumps({"staff_id": staff_id, "expire_a": time.time() + DUREE_BILLET_SECONDES}),
    )
    return billet


def consommer_billet(billet: str | None) -> int | None:
    """
    Rend l'identifiant du membre du personnel, et **détruit le billet au
    passage** — `vider_et_lire` est atomique, donc deux connexions qui
    présentent le même billet au même instant ne peuvent pas réussir toutes
    les deux, même servies par deux instances différentes.

    Rend `None` pour tout le reste : billet absent, inconnu, déjà consommé,
    périmé, ou illisible. L'appelant ne distingue pas les cas — il refuse.
    """
    if not billet:
        return None

    stocke = magasin.vider_et_lire(_cle(billet)).get(CHAMP)
    if not stocke:
        return None

    try:
        contenu = json.loads(stocke)
        if contenu["expire_a"] < time.time():
            return None
        return int(contenu["staff_id"])
    except (ValueError, TypeError, KeyError):
        return None
