"""
Le billet d'entrée des canaux WebSocket du personnel
(ROADMAP_PRODUCTION.md §P2.4, F9).

**Ce qui était en jeu.** Le JWT du personnel n'a volontairement pas de claim
`exp` (décision produit de Wassim, 2026-09-09 : la seule déconnexion voulue
est le bouton « Se déconnecter », jamais une expiration qui éjecterait un
serveur en plein coup de feu). Et la poignée de main WebSocket d'un navigateur
n'admet aucun en-tête personnalisé : le jeton voyageait donc en **query
string**, dans des URLs que Cloudflare et l'hébergeur journalisent. Un jeton
éternel retrouvé dans un log d'accès restait valide **indéfiniment**, sans
aucun moyen de le révoquer.

La correction ne touche pas à la session du serveur en salle — elle ne change
pas d'un iota. C'est le **jeton de transport** qui devient jetable.

Ce que ces tests verrouillent, dans l'ordre d'importance :

1. **le JWT n'ouvre plus rien** — sans ça la correction ne ferme rien du tout,
   elle ajoute juste un second chemin ;
2. **le billet ne sert qu'une fois** — contre celui lu dans un log avant sa
   péremption ;
3. **le billet périme** — contre celui demandé et jamais utilisé, qui vaudrait
   sinon pour toujours ;
4. **le billet dit QUI, pas À QUOI on a droit** — un billet de cuisine n'ouvre
   pas l'écran serveur, exactement comme le JWT ne le permettait pas.
"""
import time

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.modules.staff import ws_tickets
from app.modules.staff.models import StaffRole
from app.modules.staff.security import create_access_token
from app.modules.notifications.dependencies import WS_UNAUTHORIZED
from tests.conftest import auth_headers, create_restaurant, create_staff, ws_billet


def _refus(client: TestClient, chemin: str) -> int:
    with pytest.raises(WebSocketDisconnect) as refus:
        with client.websocket_connect(chemin) as ws:
            ws.receive_text()
    return refus.value.code


def test_le_jwt_nouvre_plus_le_canal_du_personnel(client):
    """
    **Le test qui compte.** Si le JWT ouvrait encore, la correction n'aurait
    rien fermé : le jeton éternel continuerait d'atterrir dans les logs de
    quiconque le met dans l'URL, et l'ancien chemin resterait exploitable.
    """
    restaurant = create_restaurant(name="Billet", slug="billet-jwt")
    serveur = create_staff(restaurant.id, StaffRole.WAITER)
    jwt = create_access_token(serveur.id, restaurant.id, serveur.role.value)

    assert _refus(client, f"/ws/staff/{restaurant.id}?billet={jwt}") == WS_UNAUTHORIZED


def test_un_billet_ne_sert_quune_seule_fois(client):
    """
    Un billet lu dans un log d'accès a déjà servi. C'est la garde qui couvre la
    fuite avant péremption — la durée courte, elle, couvre le billet jamais
    utilisé.
    """
    restaurant = create_restaurant(name="Billet", slug="billet-unique")
    serveur = create_staff(restaurant.id, StaffRole.WAITER)
    billet = ws_billet(serveur)

    with client.websocket_connect(f"/ws/staff/{restaurant.id}?billet={billet}") as ws:
        assert ws is not None

    assert _refus(client, f"/ws/staff/{restaurant.id}?billet={billet}") == WS_UNAUTHORIZED


def test_un_billet_perime_nouvre_rien(client, monkeypatch):
    """
    Le billet demandé puis jamais utilisé : sans cette borne, il resterait
    valable pour toujours, et on aurait remplacé un jeton éternel par un autre.
    """
    restaurant = create_restaurant(name="Billet", slug="billet-perime")
    serveur = create_staff(restaurant.id, StaffRole.WAITER)
    billet = ws_billet(serveur)

    # Le temps passe : plus rien ne doit s'ouvrir avec ce billet.
    # `vrai_time` capturé AVANT le patch : `ws_tickets.time` est le module
    # `time` lui-même, et une lambda qui rappellerait `time.time()` après le
    # patch s'appellerait elle-même à l'infini.
    vrai_time = time.time
    monkeypatch.setattr(
        ws_tickets.time, "time", lambda: vrai_time() + ws_tickets.DUREE_BILLET_SECONDES + 1
    )
    assert _refus(client, f"/ws/staff/{restaurant.id}?billet={billet}") == WS_UNAUTHORIZED


def test_un_billet_de_cuisine_nouvre_pas_lecran_serveur(client):
    """
    Le billet dit QUI, le socket décide de QUOI — même séparation que S-4
    (audit 2026-08-18) sur les rôles, inchangée par P2.4.
    """
    restaurant = create_restaurant(name="Billet", slug="billet-role")
    cuisine = create_staff(restaurant.id, StaffRole.KITCHEN)

    assert _refus(client, f"/ws/staff/{restaurant.id}?billet={ws_billet(cuisine)}") == WS_UNAUTHORIZED


def test_un_billet_nouvre_pas_le_canal_dun_autre_restaurant(client):
    """Isolation multi-tenant : le billet ne la contourne pas non plus."""
    restaurant = create_restaurant(name="Billet", slug="billet-tenant-a")
    voisin = create_restaurant(name="Voisin", slug="billet-tenant-b")
    intrus = create_staff(voisin.id, StaffRole.WAITER)

    assert _refus(client, f"/ws/staff/{restaurant.id}?billet={ws_billet(intrus)}") == WS_UNAUTHORIZED


def test_un_billet_invente_nouvre_rien(client):
    restaurant = create_restaurant(name="Billet", slug="billet-invente")
    create_staff(restaurant.id, StaffRole.WAITER)

    assert _refus(client, f"/ws/staff/{restaurant.id}?billet=pas-un-vrai-billet") == WS_UNAUTHORIZED


# --- La route d'échange -------------------------------------------------


def test_la_route_de_billet_exige_le_jwt(client):
    """
    L'échange se fait là où le jeton long est en sécurité : dans l'en-tête
    `Authorization`. Sans lui, pas de billet.
    """
    assert client.post("/api/v1/auth/ws-ticket").status_code == 401


def test_deux_appels_rendent_deux_billets_differents(client):
    """
    Un billet réutilisable d'un appel à l'autre ne serait plus à usage unique :
    deux écrans qui se reconnectent en même temps se voleraient le leur.
    """
    restaurant = create_restaurant(name="Billet", slug="billet-deux")
    serveur = create_staff(restaurant.id, StaffRole.WAITER)
    entetes = auth_headers(serveur)

    premier = client.post("/api/v1/auth/ws-ticket", headers=entetes).json()
    second = client.post("/api/v1/auth/ws-ticket", headers=entetes).json()

    assert premier["ticket"] != second["ticket"]
    assert premier["expire_dans"] == ws_tickets.DUREE_BILLET_SECONDES

    # Et les deux fonctionnent : se reconnecter ne doit pas invalider l'écran
    # d'à côté.
    for billet in (premier["ticket"], second["ticket"]):
        with client.websocket_connect(f"/ws/staff/{restaurant.id}?billet={billet}") as ws:
            assert ws is not None


def test_le_billet_obtenu_par_la_route_ouvre_bien_le_canal(client):
    """Le parcours complet, tel que le frontend le joue à chaque connexion."""
    restaurant = create_restaurant(name="Billet", slug="billet-parcours")
    serveur = create_staff(restaurant.id, StaffRole.WAITER)

    reponse = client.post("/api/v1/auth/ws-ticket", headers=auth_headers(serveur))
    assert reponse.status_code == 200

    with client.websocket_connect(f"/ws/staff/{restaurant.id}?billet={reponse.json()['ticket']}") as ws:
        assert ws is not None
