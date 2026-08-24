"""
Import de carte depuis un CSV (Phase 13.2).

Les cas testés sont ceux d'un vrai fichier de restaurateur : export Excel en
locale française (point-virgule, virgule décimale, BOM), colonnes nommées à sa
façon, et une ou deux fautes de frappe qui ne doivent pas faire échouer les
trente-huit autres lignes.
"""
from tests.conftest import auth_headers, create_restaurant, create_staff

from app.modules.menu.csv_import import parse_menu_csv
from app.modules.staff.models import StaffRole


def _manager(restaurant_slug: str):
    restaurant = create_restaurant(name="Chez Slah", slug=restaurant_slug)
    return restaurant, create_staff(restaurant.id, StaffRole.MANAGER)


def _import(client, manager, content: str, replace: bool = False):
    return client.post(
        "/api/v1/menu-items/import-csv",
        json={"content": content, "replace_existing": replace},
        headers=auth_headers(manager),
    )


# --- Lecture du format ------------------------------------------------------


def test_reads_a_simple_comma_file():
    result = parse_menu_csv("nom,categorie,prix\nCouscous,Plats,24\nBrik,Entrées,4\n")
    assert not result.errors
    assert [i.name for i in result.items] == ["Couscous", "Brik"]
    assert result.items[0].price == 24.0
    assert result.items[0].category == "Plats"


def test_reads_a_french_excel_export():
    """Point-virgule, virgule décimale, BOM : l'export réel d'un tableur en
    locale française."""
    content = "﻿Nom;Catégorie;Prix\nCouscous poisson;Plats;24,500\nThé;Boissons;2,5\n"
    result = parse_menu_csv(content)
    assert not result.errors
    assert result.items[0].price == 24.5
    assert result.items[1].price == 2.5


def test_accepts_column_aliases_and_accents():
    result = parse_menu_csv("PLAT;FAMILLE;TARIF;DETAIL\nLablabi;Plats;7;Bien relevé\n")
    assert not result.errors
    assert result.items[0].name == "Lablabi"
    assert result.items[0].category == "Plats"
    assert result.items[0].description == "Bien relevé"


def test_optional_columns_have_sensible_defaults():
    result = parse_menu_csv("nom,prix\nCafé,2\n")
    assert not result.errors
    item = result.items[0]
    assert item.category == "Autre"
    assert item.spice_level == 0
    assert item.allergens is None
    assert item.is_halal is True  # défaut du modèle, la quasi-totalité des restos


def test_reads_spice_allergens_and_halal():
    content = "nom,prix,piment,allergenes,halal\nMerguez,12,3,Gluten,oui\nVin,20,0,,non\n"
    result = parse_menu_csv(content)
    assert not result.errors
    assert result.items[0].spice_level == 3
    assert result.items[0].allergens == "Gluten"
    assert result.items[0].is_halal is True
    assert result.items[1].is_halal is False


def test_is_halal_default_suit_le_marche(monkeypatch):
    """F5-A6 (MARCHE_FRANCE.md) : le défaut s'inverse en France, sans qu'aucune
    colonne halal ne soit présente dans le fichier."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "market", "fr")
    result = parse_menu_csv("nom,prix\nCafé,2\n")
    assert not result.errors
    assert result.items[0].is_halal is False


def test_reads_allergen_codes_and_dietary_markers():
    content = (
        "nom,prix,allergenes ue,vegetarien,vegan,sans gluten\n"
        "Salade,8,\"gluten,eggs\",oui,non,non\n"
    )
    result = parse_menu_csv(content)
    assert not result.errors
    item = result.items[0]
    assert item.allergen_codes == "gluten,eggs"
    assert item.is_vegetarian is True
    assert item.is_vegan is False
    assert item.is_gluten_free is False


def test_allergen_codes_and_dietary_markers_default_to_absent():
    result = parse_menu_csv("nom,prix\nCafé,2\n")
    item = result.items[0]
    assert item.allergen_codes is None
    assert item.is_vegetarian is False
    assert item.is_vegan is False
    assert item.is_gluten_free is False


# --- Tolérance aux erreurs -------------------------------------------------


def test_one_bad_line_does_not_lose_the_others():
    """Le cas qui compte : 3 plats bons, 1 prix illisible. Recommencer tout le
    fichier pour une faute de frappe serait inacceptable sur 40 lignes."""
    content = "nom,prix\nCouscous,24\nBrik,quatre\nThé,2.5\nSalade,8\n"
    result = parse_menu_csv(content)
    assert [i.name for i in result.items] == ["Couscous", "Thé", "Salade"]
    assert len(result.errors) == 1
    assert "Ligne 3" in result.errors[0]
    assert "Brik" in result.errors[0]


def test_missing_name_is_reported_with_its_line_number():
    result = parse_menu_csv("nom,prix\n,12\nCouscous,24\n")
    assert [i.name for i in result.items] == ["Couscous"]
    assert "Ligne 2" in result.errors[0]


def test_trailing_empty_lines_are_ignored():
    result = parse_menu_csv("nom,prix\nCouscous,24\n\n\n")
    assert len(result.items) == 1
    assert not result.errors


def test_negative_price_is_refused():
    result = parse_menu_csv("nom,prix\nCadeau,-5\n")
    assert not result.items
    assert "négatif" in result.errors[0]


def test_spice_level_out_of_range_is_refused():
    result = parse_menu_csv("nom,prix,piment\nHarissa,3,9\n")
    assert not result.items
    assert "piment" in result.errors[0]


def test_missing_mandatory_column_explains_what_was_found():
    result = parse_menu_csv("plat,categorie\nCouscous,Plats\n")
    assert not result.items
    assert "prix" in result.errors[0]
    assert "categorie" in result.errors[0]  # rappelle les colonnes trouvées


def test_empty_file_is_reported():
    assert parse_menu_csv("")
    assert parse_menu_csv("").errors == ["Le fichier est vide."]


def test_error_messages_never_leak_python_internals():
    """
    Ces messages s'affichent dans le dashboard d'un restaurateur. Laisser
    remonter « could not convert string to float » ou « invalid literal for
    int() » le laisserait sans aucune idée de quoi corriger — c'est arrivé au
    premier essai, d'où ce garde-fou.
    """
    content = "nom,prix,piment,halal\nBrik,gratuit,0,oui\nHarissa,3,neuf,oui\nVin,20,0,peut-être\n"
    errors = parse_menu_csv(content).errors
    assert len(errors) == 3
    for message in errors:
        assert "float" not in message
        assert "int()" not in message
        assert "literal" not in message
        assert "convert" not in message
    assert "prix illisible « gratuit »" in errors[0]
    assert "niveau de piment illisible « neuf »" in errors[1]
    assert "oui/non attendue" in errors[2]


# --- Endpoint --------------------------------------------------------------


def test_manager_imports_a_menu(client):
    restaurant, manager = _manager("csv-import-ok")

    response = _import(client, manager, "nom,categorie,prix\nCouscous,Plats,24\nBrik,Entrées,4\n")
    assert response.status_code == 200
    body = response.json()
    assert body["created_count"] == 2
    assert body["updated_count"] == 0
    assert body["disabled_count"] == 0
    assert body["errors"] == []

    listed = client.get(f"/api/v1/menu-items/by-restaurant/{restaurant.id}", headers=auth_headers(manager)).json()
    assert {i["name"] for i in listed} == {"Couscous", "Brik"}


def test_import_lands_in_the_manager_restaurant_only(client):
    restaurant, manager = _manager("csv-import-scope-a")
    other, other_manager = _manager("csv-import-scope-b")

    _import(client, manager, "nom,prix\nCouscous,24\n")

    assert len(client.get(f"/api/v1/menu-items/by-restaurant/{restaurant.id}", headers=auth_headers(manager)).json()) == 1
    assert client.get(f"/api/v1/menu-items/by-restaurant/{other.id}", headers=auth_headers(other_manager)).json() == []


def test_reimporting_the_same_file_updates_instead_of_duplicating(client):
    """Le geste réel : « j\'ai corrigé mon fichier, remets-le ». Créer
    systématiquement donnerait la carte en double à la deuxième passe — c\'est
    ce qui s\'est produit au premier essai en navigateur."""
    restaurant, manager = _manager("csv-import-rejoue")
    _import(client, manager, "nom,categorie,prix\nCouscous,Plats,24\n")

    response = _import(client, manager, "nom,categorie,prix\nCouscous,Plats,26\n")
    assert response.status_code == 200
    assert response.json() == {
        "created_count": 0, "updated_count": 1, "disabled_count": 0, "errors": []
    }

    listed = client.get(f"/api/v1/menu-items/by-restaurant/{restaurant.id}", headers=auth_headers(manager)).json()
    assert len(listed) == 1
    assert listed[0]["price"] == 26.0  # le prix corrigé a bien été repris


def test_partial_import_does_not_remove_the_rest_of_the_card(client):
    """Un patron qui envoie trois nouveaux plats ne doit pas voir le reste de sa
    carte disparaître."""
    restaurant, manager = _manager("csv-import-partiel-carte")
    _import(client, manager, "nom,prix\nCouscous,24\nBrik,4\n")

    _import(client, manager, "nom,prix\nTiramisu,7\n")

    listed = client.get(f"/api/v1/menu-items/by-restaurant/{restaurant.id}", headers=auth_headers(manager)).json()
    assert {i["name"] for i in listed} == {"Couscous", "Brik", "Tiramisu"}
    assert all(i["is_available"] for i in listed)


def test_replace_existing_disables_what_is_absent_from_the_file(client):
    """« Ce fichier est ma carte complète » : les articles absents sont rendus
    indisponibles, jamais supprimés — une commande passée référence son
    menu_item_id."""
    restaurant, manager = _manager("csv-import-replace")
    _import(client, manager, "nom,prix\nAncien plat,10\nToujours là,8\n")

    response = _import(client, manager, "nom,prix\nToujours là,8\nNouveau plat,12\n", replace=True)
    assert response.status_code == 200
    body = response.json()
    assert body["created_count"] == 1
    assert body["updated_count"] == 1
    assert body["disabled_count"] == 1

    by_name = {i["name"]: i for i in client.get(f"/api/v1/menu-items/by-restaurant/{restaurant.id}", headers=auth_headers(manager)).json()}
    assert by_name["Ancien plat"]["is_available"] is False
    assert by_name["Toujours là"]["is_available"] is True
    assert by_name["Nouveau plat"]["is_available"] is True


def test_reimport_makes_an_unavailable_item_available_again(client):
    """Une rupture de stock levée en réimportant la carte : le patron ne doit
    pas avoir à rebasculer chaque plat à la main."""
    restaurant, manager = _manager("csv-import-rupture")
    _import(client, manager, "nom,prix\nCouscous,24\n")
    item_id = client.get(f"/api/v1/menu-items/by-restaurant/{restaurant.id}", headers=auth_headers(manager)).json()[0]["id"]
    client.patch(
        f"/api/v1/menu-items/{item_id}/availability",
        json={"is_available": False},
        headers=auth_headers(manager),
    )

    _import(client, manager, "nom,prix\nCouscous,24\n")
    assert client.get(f"/api/v1/menu-items/by-restaurant/{restaurant.id}", headers=auth_headers(manager)).json()[0]["is_available"] is True


def test_import_reports_bad_lines_but_keeps_the_good_ones(client):
    restaurant, manager = _manager("csv-import-partiel")

    response = _import(client, manager, "nom,prix\nCouscous,24\nBrik,gratuit\n")
    assert response.status_code == 200
    assert response.json()["created_count"] == 1
    assert len(response.json()["errors"]) == 1
    assert len(client.get(f"/api/v1/menu-items/by-restaurant/{restaurant.id}", headers=auth_headers(manager)).json()) == 1


def test_unreadable_file_is_refused_with_the_reasons(client):
    _restaurant, manager = _manager("csv-import-illisible")

    response = _import(client, manager, "colonne inconnue\nvaleur\n")
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "CSV_UNREADABLE"
    assert detail["errors"]


def test_import_is_manager_only(client):
    restaurant, _manager_staff = _manager("csv-import-role")
    waiter = create_staff(restaurant.id, StaffRole.WAITER)

    assert _import(client, waiter, "nom,prix\nCouscous,24\n").status_code == 403
    assert client.post(
        "/api/v1/menu-items/import-csv", json={"content": "nom,prix\nCouscous,24\n"}
    ).status_code == 401
