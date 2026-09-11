"""
Ce qu'un refus WebSocket dit au client (ROADMAP_PRODUCTION.md §P1.6, F12).

Le frontend traite deux situations très différemment
(`frontend/lib/useReconnectingSocket.ts`) :

- code **4401** → « ce canal ne me sera jamais accordé » : il **arrête
  définitivement** de réessayer ;
- toute autre fermeture → coupure réseau : il **réessaie** avec un backoff
  exponentiel.

L'audit du 2026-09-10 supposait qu'un pool saturé produisait un 4401 — un
client au QR parfaitement valide aurait alors vu son panier partagé mourir
jusqu'à rechargement manuel, même après rétablissement. **Mesuré depuis, c'est
faux** : une base injoignable fait échouer la poignée de main au niveau HTTP
(le navigateur rapporte 1006), jamais un 4401. Le 4401 n'est émis que par
`_reject`, appelé uniquement sur un vrai défaut d'autorisation.

La bonne propriété est donc déjà vraie — mais par construction, pas par
intention : elle tient au fait que l'erreur base survient AVANT le `accept()`.
Ces tests la verrouillent, pour qu'un futur remaniement de l'authentification
ne la renverse pas silencieusement. Sans eux, la seule façon de s'en apercevoir
serait qu'un client cesse de recevoir son panier en plein service.
"""
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.modules.notifications.dependencies import WS_UNAUTHORIZED
from app.modules.staff.models import StaffRole
from app.modules.staff.security import create_access_token
from tests.conftest import create_restaurant, create_staff, ws_billet
from app.modules.tables.models import Table
from tests.conftest import _TestingSessionLocal


def _table(restaurant_id: int) -> Table:
    db = _TestingSessionLocal()
    table = Table(restaurant_id=restaurant_id, label="Table 1")
    db.add(table)
    db.commit()
    db.refresh(table)
    db.close()
    return table


def test_un_qr_inconnu_ferme_avec_le_code_qui_arrete_les_tentatives(client: TestClient):
    """
    Vrai défaut d'autorisation : réessayer n'y changera jamais rien, le client
    doit s'arrêter. C'est le seul cas où 4401 est légitime.
    """
    restaurant = create_restaurant(name="Refus", slug="refus-qr")

    with pytest.raises(WebSocketDisconnect) as refus:
        with client.websocket_connect(f"/ws/table/{restaurant.id}/jeton-qui-nexiste-pas") as ws:
            ws.receive_json()

    assert refus.value.code == WS_UNAUTHORIZED


def test_un_jeton_staff_absent_ferme_avec_le_meme_code(client: TestClient):
    """Même règle sur le canal serveur : sans billet, aucun espoir de réussir."""
    restaurant = create_restaurant(name="Refus", slug="refus-staff")

    with pytest.raises(WebSocketDisconnect) as refus:
        with client.websocket_connect(f"/ws/staff/{restaurant.id}") as ws:
            ws.receive_text()

    assert refus.value.code == WS_UNAUTHORIZED


def test_le_mauvais_role_ferme_avec_le_meme_code(client: TestClient):
    """
    Un cuisinier sur le canal serveur : refus définitif, pas une indisponibilité.
    """
    restaurant = create_restaurant(name="Refus", slug="refus-role")
    cuisine = create_staff(restaurant.id, StaffRole.KITCHEN)

    with pytest.raises(WebSocketDisconnect) as refus:
        with client.websocket_connect(f"/ws/staff/{restaurant.id}?billet={ws_billet(cuisine)}") as ws:
            ws.receive_text()

    assert refus.value.code == WS_UNAUTHORIZED


def test_une_base_injoignable_ne_produit_jamais_le_code_qui_arrete_les_tentatives(client, monkeypatch):
    """
    **Le test qui compte.**

    Une indisponibilité de ressource ne doit JAMAIS ressembler à un refus
    d'autorisation : le client doit continuer de réessayer, sinon son panier
    partagé reste mort après le rétablissement.

    Vérifié en conditions réelles avant d'écrire ce test (base réellement
    arrêtée, vrai `uvicorn`) : la poignée de main échoue au niveau HTTP et le
    navigateur rapporte 1006. Ici on reproduit la panne au plus près du code —
    la requête d'authentification lève — et on vérifie la seule chose qui
    compte : **quoi qu'il arrive, ce n'est pas 4401.**
    """
    from app.modules.notifications import dependencies as ws_dependencies

    restaurant = create_restaurant(name="Panne", slug="panne-base")
    table = _table(restaurant.id)

    class _BaseEnPanne(Exception):
        pass

    def _authentification_qui_tombe(*args, **kwargs):
        raise _BaseEnPanne("connection to server failed")

    monkeypatch.setattr(ws_dependencies, "authenticate_table_socket", _authentification_qui_tombe)

    try:
        with client.websocket_connect(f"/ws/table/{restaurant.id}/{table.qr_token}") as ws:
            ws.receive_json()
    except WebSocketDisconnect as fermeture:
        assert fermeture.code != WS_UNAUTHORIZED, (
            "une base injoignable s'est présentée comme un refus d'autorisation : "
            "le client va cesser de réessayer et son panier restera mort après "
            "le rétablissement"
        )
    except _BaseEnPanne:
        # La panne remonte telle quelle : la poignée de main n'aboutit pas, le
        # navigateur verra 1006 et réessaiera. C'est le comportement voulu.
        pass
