"""
Vocabulaire de régimes alimentaires par restaurant (« Halal », « Végétarien »,
ou tout nom choisi par le manager) — demande de Wassim (2026-08-26), en
remplacement d'une liste figée de marqueurs pour le marché français. Coexiste
avec `MenuItem.is_halal`, ne le remplace pas.

Le point critique testé ici : modifier le vocabulaire (ajouter/retirer/
réordonner un nom) ne doit JAMAIS décocher silencieusement un régime resté
inchangé sur un article qui le portait déjà — voir
`test_adding_a_regime_never_untags_existing_items`.
"""
from tests.conftest import auth_headers, create_restaurant, create_staff

from app.modules.menu.models import MenuItem, MenuRegime
from app.modules.staff.models import StaffRole
from app.modules.tables.models import Table


def _setup(db_session, slug: str):
    restaurant = create_restaurant(name="Chez Slah", slug=slug)
    table = Table(restaurant_id=restaurant.id, label="Table 1")
    couscous = MenuItem(restaurant_id=restaurant.id, name="Couscous", price=22.0, category="Plats")
    salade = MenuItem(restaurant_id=restaurant.id, name="Salade", price=8.0, category="Entrées")
    db_session.add_all([table, couscous, salade])
    db_session.commit()
    for obj in (table, couscous, salade):
        db_session.refresh(obj)
    return restaurant, table, couscous, salade


def _set_vocab(client, manager, restaurant_id: int, names: list[str]):
    return client.put(
        f"/api/v1/menu-items/by-restaurant/{restaurant_id}/regimes",
        json={"names": names},
        headers=auth_headers(manager),
    )


def _set_item_regimes(client, manager, item_id: int, regime_ids: list[int]):
    return client.put(
        f"/api/v1/menu-items/{item_id}/regimes",
        json={"regime_ids": regime_ids},
        headers=auth_headers(manager),
    )


# --- Vocabulaire -------------------------------------------------------------


def test_manager_creates_and_reads_back_vocabulary(client, db_session):
    restaurant, _table, _couscous, _salade = _setup(db_session, "reg-set")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    response = _set_vocab(client, manager, restaurant.id, ["Halal", "Végétarien", "Vegan"])
    assert response.status_code == 200
    assert [r["name"] for r in response.json()] == ["Halal", "Végétarien", "Vegan"]

    listed = client.get(
        f"/api/v1/menu-items/by-restaurant/{restaurant.id}/regimes", headers=auth_headers(manager)
    ).json()
    assert [r["name"] for r in listed] == ["Halal", "Végétarien", "Vegan"]


def test_blank_and_duplicate_names_are_dropped(client, db_session):
    restaurant, _table, _c, _s = _setup(db_session, "reg-dedupe")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    response = _set_vocab(client, manager, restaurant.id, ["Halal", "  ", "Halal", "Végétarien", ""])
    assert [r["name"] for r in response.json()] == ["Halal", "Végétarien"]


def test_adding_a_regime_never_untags_existing_items(client, db_session):
    """
    Régression ciblée : le manager ajoute « Vegan » à un vocabulaire qui
    contient déjà « Halal » et « Végétarien », dont un article est déjà tagué.
    Cet ajout ne doit ni changer l'id de « Halal »/« Végétarien », ni décocher
    l'article qui les porte.
    """
    restaurant, _table, couscous, _salade = _setup(db_session, "reg-ajout")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    first = _set_vocab(client, manager, restaurant.id, ["Halal", "Végétarien"]).json()
    halal_id = next(r["id"] for r in first if r["name"] == "Halal")
    vege_id = next(r["id"] for r in first if r["name"] == "Végétarien")
    _set_item_regimes(client, manager, couscous.id, [halal_id, vege_id])

    second = _set_vocab(client, manager, restaurant.id, ["Halal", "Végétarien", "Vegan"]).json()
    assert next(r["id"] for r in second if r["name"] == "Halal") == halal_id
    assert next(r["id"] for r in second if r["name"] == "Végétarien") == vege_id

    item = db_session.get(MenuItem, couscous.id)
    db_session.refresh(item)
    assert {r.name for r in item.regimes} == {"Halal", "Végétarien"}


def test_removing_a_regime_from_vocabulary_untags_it_everywhere(client, db_session):
    restaurant, _table, couscous, _salade = _setup(db_session, "reg-retrait")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    first = _set_vocab(client, manager, restaurant.id, ["Halal", "Végétarien"]).json()
    halal_id = next(r["id"] for r in first if r["name"] == "Halal")
    vege_id = next(r["id"] for r in first if r["name"] == "Végétarien")
    _set_item_regimes(client, manager, couscous.id, [halal_id, vege_id])

    _set_vocab(client, manager, restaurant.id, ["Halal"])  # "Végétarien" retiré

    item = db_session.get(MenuItem, couscous.id)
    db_session.refresh(item)
    assert {r.name for r in item.regimes} == {"Halal"}
    # La ligne elle-même doit avoir disparu de la base, pas seulement de la
    # relation (même classe de bug que la régression trouvée sur les options :
    # une DELETE en bloc mal faite laisserait une ligne fantôme).
    assert db_session.get(MenuRegime, vege_id) is None


def test_reordering_vocabulary_keeps_the_same_ids(client, db_session):
    restaurant, _table, _c, _s = _setup(db_session, "reg-ordre")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    first = _set_vocab(client, manager, restaurant.id, ["Halal", "Végétarien"]).json()
    ids_before = {r["name"]: r["id"] for r in first}

    second = _set_vocab(client, manager, restaurant.id, ["Végétarien", "Halal"]).json()
    assert [r["name"] for r in second] == ["Végétarien", "Halal"]
    assert {r["name"]: r["id"] for r in second} == ids_before


def test_setting_vocabulary_is_manager_only(client, db_session):
    restaurant, _table, _c, _s = _setup(db_session, "reg-role")
    waiter = create_staff(restaurant.id, StaffRole.WAITER)

    assert _set_vocab(client, waiter, restaurant.id, ["Halal"]).status_code == 403
    assert client.put(
        f"/api/v1/menu-items/by-restaurant/{restaurant.id}/regimes", json={"names": ["Halal"]}
    ).status_code == 401


def test_cannot_set_vocabulary_of_another_restaurant(client, db_session):
    restaurant, _t, _c, _s = _setup(db_session, "reg-iso-a")
    _other, _t2, _c2, _s2 = _setup(db_session, "reg-iso-b")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    other_manager = create_staff(_other.id, StaffRole.MANAGER)

    _set_vocab(client, other_manager, _other.id, ["Casher"])
    assert _set_vocab(client, manager, _other.id, ["Halal"]).status_code == 403


# --- Régimes cochés sur un article -------------------------------------------


def test_manager_tags_an_item_with_regimes(client, db_session):
    restaurant, table, couscous, _salade = _setup(db_session, "reg-tag")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    vocab = _set_vocab(client, manager, restaurant.id, ["Halal", "Vegan"]).json()
    halal_id = next(r["id"] for r in vocab if r["name"] == "Halal")

    response = _set_item_regimes(client, manager, couscous.id, [halal_id])
    assert response.status_code == 200
    assert [r["name"] for r in response.json()["regimes"]] == ["Halal"]

    # Visible du côté client aussi (parcours public par table).
    menu = client.get(f"/api/v1/menu-items/by-table/{table.qr_token}").json()
    item = next(i for i in menu if i["id"] == couscous.id)
    assert [r["name"] for r in item["regimes"]] == ["Halal"]


def test_an_id_from_another_restaurant_is_silently_dropped(client, db_session):
    """Tolérant plutôt qu'une erreur : contrairement aux options choisies par
    le client à la commande, ceci est un réglage manager sur son propre
    restaurant — un vocabulaire modifié entre le chargement de l'écran et
    l'enregistrement ne doit pas bloquer sur une erreur qu'il ne peut pas
    comprendre."""
    restaurant, _t, couscous, _s = _setup(db_session, "reg-etranger-a")
    other, _t2, _c2, _s2 = _setup(db_session, "reg-etranger-b")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    other_manager = create_staff(other.id, StaffRole.MANAGER)
    own_vocab = _set_vocab(client, manager, restaurant.id, ["Halal"]).json()
    other_vocab = _set_vocab(client, other_manager, other.id, ["Casher"]).json()

    response = _set_item_regimes(
        client, manager, couscous.id, [own_vocab[0]["id"], other_vocab[0]["id"]]
    )
    assert response.status_code == 200
    assert [r["name"] for r in response.json()["regimes"]] == ["Halal"]


def test_cannot_tag_an_item_of_another_restaurant(client, db_session):
    restaurant, _t, _c, _s = _setup(db_session, "reg-tag-iso-a")
    other, _t2, other_item, _s2 = _setup(db_session, "reg-tag-iso-b")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    response = _set_item_regimes(client, manager, other_item.id, [])
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ITEM_NOT_FOUND"
