"""
Allergènes structurés (14 codes INCO, règlement UE 1169/2011) et défaut
`is_halal` conscient du marché — France, MARCHE_FRANCE.md F5/A6.

Trois défauts concrets que le champ libre + le `is_halal=True` codé en dur
ne pouvaient pas éviter, chacun couvert ici :
- un code hors des 14 valeurs romprait silencieusement tout affichage futur
  plutôt que d'échouer à la saisie (comme VatCategory, voir A4) ;
- `is_halal=True` par défaut est faux en France (l'exception y est inverse
  de la Tunisie) — codé en dur à TROIS endroits avant ce correctif (schéma,
  colonne, import CSV), chacun testé séparément ci-dessous ;
- `allergen_codes` coexiste avec `allergens` (texte libre), ne le remplace
  pas — les deux doivent pouvoir être posés en même temps.
"""
import app.modules.menu.csv_import as csv_import_module
import app.modules.menu.schemas as menu_schemas_module
from app.core.markets import FRANCE
from app.modules.menu.csv_import import parse_menu_csv
from tests.conftest import auth_headers, create_restaurant, create_staff


def _setup_restaurant(client, slug: str):
    restaurant = create_restaurant(name="Le Bistrot Test", slug=slug)
    headers = auth_headers(create_staff(restaurant.id))
    return restaurant, headers


# --- allergen_codes : validation contre les 14 codes INCO -------------------


def test_menu_item_defaults_to_no_allergen_codes(client):
    restaurant, headers = _setup_restaurant(client, "allergens-default")
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Couscous", "price": 15.0},
        headers=headers,
    ).json()

    assert item["allergen_codes"] is None


def test_menu_item_can_be_created_with_valid_allergen_codes(client):
    restaurant, headers = _setup_restaurant(client, "allergens-create")
    item = client.post(
        "/api/v1/menu-items",
        json={
            "restaurant_id": restaurant.id, "name": "Gratin", "price": 12.0,
            "allergen_codes": "gluten, milk, eggs",
        },
        headers=headers,
    ).json()

    # Normalisé (espaces retirés), jamais renvoyé tel quel.
    assert item["allergen_codes"] == "gluten,milk,eggs"


def test_menu_item_allergen_codes_are_case_insensitive(client):
    """"GLUTEN"/"Milk" désignent le même code que "gluten"/"milk" — un
    manager qui recopie sa liste depuis un CSV ou une autre carte ne doit
    pas voir sa saisie rejetée pour une simple différence de casse."""
    restaurant, headers = _setup_restaurant(client, "allergens-case-insensitive")
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Gratin", "price": 12.0, "allergen_codes": "GLUTEN, Milk"},
        headers=headers,
    ).json()

    assert item["allergen_codes"] == "gluten,milk"


def test_menu_item_allergen_codes_are_deduplicated(client):
    """Un allergène collé deux fois (copier-coller, casse différente) ne
    doit ni être rejeté ni stocker une répétition qui doublerait
    l'affichage — l'ordre de première apparition est conservé."""
    restaurant, headers = _setup_restaurant(client, "allergens-dedup")
    item = client.post(
        "/api/v1/menu-items",
        json={
            "restaurant_id": restaurant.id, "name": "Gratin", "price": 12.0,
            "allergen_codes": "milk,gluten,MILK,eggs,milk",
        },
        headers=headers,
    ).json()

    assert item["allergen_codes"] == "milk,gluten,eggs"


def test_menu_item_rejects_an_unknown_allergen_code(client):
    restaurant, headers = _setup_restaurant(client, "allergens-invalid")
    res = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Mystère", "price": 6.0, "allergen_codes": "gluten,noix"},
        headers=headers,
    )

    assert res.status_code == 422


def test_menu_item_update_can_set_allergen_codes(client):
    restaurant, headers = _setup_restaurant(client, "allergens-update")
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Tarte", "price": 5.0},
        headers=headers,
    ).json()

    updated = client.patch(
        f"/api/v1/menu-items/{item['id']}", json={"allergen_codes": "gluten,eggs"}, headers=headers
    ).json()

    assert updated["allergen_codes"] == "gluten,eggs"


def test_allergen_codes_coexists_with_the_free_text_allergens_field(client):
    """Coexistence, pas remplacement : les deux peuvent être posés en même
    temps — le texte libre pour une nuance ("traces possibles de sésame"),
    le champ structuré pour l'affichage réglementaire."""
    restaurant, headers = _setup_restaurant(client, "allergens-coexist")
    item = client.post(
        "/api/v1/menu-items",
        json={
            "restaurant_id": restaurant.id, "name": "Houmous maison", "price": 7.0,
            "allergens": "traces possibles de fruits à coque",
            "allergen_codes": "sesame",
        },
        headers=headers,
    ).json()

    assert item["allergens"] == "traces possibles de fruits à coque"
    assert item["allergen_codes"] == "sesame"


# --- is_halal : défaut conscient du marché (schéma) -------------------------


def test_menu_item_defaults_halal_true_on_tunisia(client):
    restaurant, headers = _setup_restaurant(client, "halal-default-tn")
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Couscous", "price": 15.0},
        headers=headers,
    ).json()

    assert item["is_halal"] is True


def test_menu_item_defaults_halal_false_on_france(client, monkeypatch):
    """Régression F5/A6 : `is_halal=True` était codé en dur, faux en France
    où l'exception est inverse (halal signalé, jamais supposé)."""
    monkeypatch.setattr(menu_schemas_module, "current_market", FRANCE)
    restaurant, headers = _setup_restaurant(client, "halal-default-fr")

    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Brasserie du coin", "price": 15.0},
        headers=headers,
    ).json()

    assert item["is_halal"] is False


def test_menu_item_can_still_mark_halal_explicitly_on_france(client, monkeypatch):
    monkeypatch.setattr(menu_schemas_module, "current_market", FRANCE)
    restaurant, headers = _setup_restaurant(client, "halal-explicit-fr")

    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Kebab halal", "price": 9.0, "is_halal": True},
        headers=headers,
    ).json()

    assert item["is_halal"] is True


# --- is_halal : défaut conscient du marché (import CSV) ---------------------


def test_csv_import_defaults_halal_true_on_tunisia():
    content = "nom,prix\nCouscous,15.0\n"
    result = parse_menu_csv(content)

    assert result.items[0].is_halal is True


def test_csv_import_defaults_halal_false_on_france(monkeypatch):
    monkeypatch.setattr(csv_import_module, "current_market", FRANCE)
    content = "nom,prix\nBrasserie du coin,15.0\n"

    result = parse_menu_csv(content)

    assert result.items[0].is_halal is False


def test_csv_import_still_honors_an_explicit_halal_column_on_france(monkeypatch):
    monkeypatch.setattr(csv_import_module, "current_market", FRANCE)
    content = "nom,prix,halal\nKebab halal,9.0,oui\n"

    result = parse_menu_csv(content)

    assert result.items[0].is_halal is True
