"""
Catégorie de taux de TVA par article — France, MARCHE_FRANCE.md F5/A4.

Trois propriétés à couvrir, chacune motivée par un défaut concret que la
ventilation à taux unique (avant A4) ne pouvait pas éviter :
- validation à la saisie (une clé qui ne correspond à aucun taux du marché
  romprait silencieusement la ventilation, voir core/invoice.py) ;
- valeur par défaut sûre (une carte tunisienne ne doit rien voir changer) ;
- gel à la commande, même principe que menu_item_name/unit_price — un
  article reclassé après coup ne doit jamais changer une facture déjà émise.
"""
import pytest

from app.core.markets import FRANCE
from app.modules.menu import schemas as menu_schemas
from tests.conftest import auth_headers, create_restaurant, create_staff


@pytest.fixture
def _france_market(monkeypatch):
    """Le vocabulaire de `vat_category` dépend du marché servi (F5/A4) : sur
    le marché par défaut des tests (Tunisie, `vat_rates is None`), AUCUNE
    catégorie n'a de sens et toutes sont rejetées — voir
    `test_menu_item_rejects_a_vat_category_outside_the_current_market` plus
    bas. Les tests qui posent une vraie catégorie française basculent donc
    explicitement le marché, même principe que `test_invoice_number.py`."""
    monkeypatch.setattr(menu_schemas, "current_market", FRANCE)


def _setup_restaurant(client, slug: str):
    restaurant = create_restaurant(name="Le Bistrot Test", slug=slug)
    headers = auth_headers(create_staff(restaurant.id))
    return restaurant, headers


def test_menu_item_defaults_to_no_vat_category(client):
    restaurant, headers = _setup_restaurant(client, "vat-category-default")
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Couscous", "price": 15.0},
        headers=headers,
    ).json()

    assert item["vat_category"] is None


def test_menu_item_can_be_created_with_an_explicit_vat_category(client, _france_market):
    restaurant, headers = _setup_restaurant(client, "vat-category-create")
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Vin rouge", "price": 6.0, "vat_category": "alcool"},
        headers=headers,
    ).json()

    assert item["vat_category"] == "alcool"


def test_menu_item_rejects_an_unknown_vat_category(client, _france_market):
    """Une clé hors `market.vat_rates` romprait silencieusement la
    ventilation TVA (`.get()` sans correspondance) plutôt que d'échouer à la
    saisie — contrairement à `category`/`allergens`, du texte libre assumé."""
    restaurant, headers = _setup_restaurant(client, "vat-category-invalid")
    res = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Mystère", "price": 6.0, "vat_category": "reduit"},
        headers=headers,
    )

    assert res.status_code == 422


def test_menu_item_rejects_a_vat_category_outside_the_current_market(client):
    """Le marché par défaut des tests (Tunisie) n'a aucune TVA ventilée
    (`vat_rates is None`) : une catégorie qui aurait un sens en France
    ("alcool") n'en a aucun là où aucune TVA n'est ventilée du tout, et doit
    donc être rejetée elle aussi — avant A4bis, un `Literal` figé sur le
    vocabulaire français l'acceptait sur N'IMPORTE QUEL marché."""
    restaurant, headers = _setup_restaurant(client, "vat-category-wrong-market")
    res = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Vin rouge", "price": 6.0, "vat_category": "alcool"},
        headers=headers,
    )

    assert res.status_code == 422


def test_menu_item_update_can_change_the_vat_category(client, _france_market):
    restaurant, headers = _setup_restaurant(client, "vat-category-update")
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Jus de fruit", "price": 4.0},
        headers=headers,
    ).json()

    updated = client.patch(
        f"/api/v1/menu-items/{item['id']}", json={"vat_category": "a_emporter"}, headers=headers
    ).json()

    assert updated["vat_category"] == "a_emporter"


# --- Gel à la commande : voir orders/models.py::OrderItem.vat_category -----


def _menu_item_with_category(client, restaurant, headers, *, category: str | None) -> dict:
    payload = {"restaurant_id": restaurant.id, "name": "Vin rouge", "price": 6.0}
    if category is not None:
        payload["vat_category"] = category
    return client.post("/api/v1/menu-items", json=payload, headers=headers).json()


def test_placing_an_order_copies_the_menu_items_current_vat_category(client, db_session, _france_market):
    from app.modules.orders.models import OrderItem

    restaurant, headers = _setup_restaurant(client, "vat-category-order-copy")
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=headers
    ).json()
    item = _menu_item_with_category(client, restaurant, headers, category="alcool")

    order = client.post(
        "/api/v1/orders",
        json={"qr_token": table["qr_token"], "items": [{"menu_item_id": item["id"], "quantity": 1}]},
    ).json()

    order_item = db_session.query(OrderItem).filter_by(order_id=order["id"]).one()
    assert order_item.vat_category == "alcool"


def test_reclassifying_a_menu_item_never_changes_an_already_placed_order(client, db_session, _france_market):
    """Même principe que menu_item_name/unit_price (models.py) : un article
    reclassé de "sur_place" à "alcool" après coup ne doit JAMAIS changer la
    ventilation TVA d'une facture déjà émise pour une commande passée avant."""
    from app.modules.orders.models import OrderItem

    restaurant, headers = _setup_restaurant(client, "vat-category-immutable")
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=headers
    ).json()
    item = _menu_item_with_category(client, restaurant, headers, category=None)  # "sur_place" par défaut

    order = client.post(
        "/api/v1/orders",
        json={"qr_token": table["qr_token"], "items": [{"menu_item_id": item["id"], "quantity": 1}]},
    ).json()

    client.patch(f"/api/v1/menu-items/{item['id']}", json={"vat_category": "alcool"}, headers=headers)

    order_item = db_session.query(OrderItem).filter_by(order_id=order["id"]).one()
    assert order_item.vat_category is None
