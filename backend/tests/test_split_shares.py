"""
Répartition de l'addition par personne — `orders/split.py::compute_shares`.

Ce calcul est celui qui FACTURE (voir `service.py::compute_payable_amount`),
là où `SplitBill.tsx` et `computeSharesLocal` ne font qu'annoncer un montant
avant de cliquer. Les trois doivent donner le même résultat sur les mêmes
données, d'où les cas ci-dessous : ils décrivent l'ordre de priorité entre
`shared_with` (qui a été désigné), `is_shared` (combien de couverts) et
`added_by_name` (qui a ajouté le plat).
"""
from app.modules.orders.models import Order
from app.modules.orders.split import compute_shares
from tests.conftest import auth_headers, create_restaurant, create_staff

CONVIVES = ["Wassim", "Sami", "Karim"]


def _table_avec_couscous(client, slug: str):
    restaurant = create_restaurant(name="Dar Zarrouk", slug=slug)
    headers = auth_headers(create_staff(restaurant.id))
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 4"}, headers=headers
    ).json()
    couscous = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Couscous royal", "category": "Plats", "price": 24.0},
        headers=headers,
    ).json()
    return table, couscous


def _commander(client, db_session, table, item) -> Order:
    commande = client.post("/api/v1/orders", json={"qr_token": table["qr_token"], "items": [item]}).json()
    return db_session.query(Order).filter(Order.id == commande["id"]).one()


def test_un_plat_assigne_a_un_autre_convive_lui_est_facture(client, db_session):
    """
    Le cas qui a motivé le chantier : sur la carte, Wassim se décoche et coche
    Sami — l'écran annonce "Pour Sami". Un plat pour une seule personne n'est
    pas un partage, donc `is_shared` est faux ; `shared_with` doit malgré tout
    faire foi, sinon l'addition facture Wassim ce que l'écran promettait à Sami.
    """
    table, couscous = _table_avec_couscous(client, "dar-zarrouk-assigne")
    order = _commander(
        client,
        db_session,
        table,
        {
            "menu_item_id": couscous["id"],
            "quantity": 1,
            "is_shared": False,
            "shared_with": [2],
            "added_by_name": "Wassim",
        },
    )

    assert compute_shares(order, CONVIVES) == {"Wassim": 0.0, "Sami": 24.0, "Karim": 0.0}


def test_un_plat_partage_entre_deux_convives_est_coupe_en_deux(client, db_session):
    table, couscous = _table_avec_couscous(client, "dar-zarrouk-partage")
    order = _commander(
        client,
        db_session,
        table,
        {
            "menu_item_id": couscous["id"],
            "quantity": 1,
            "is_shared": True,
            "shared_with": [1, 2],
            "added_by_name": "Wassim",
        },
    )

    assert compute_shares(order, CONVIVES) == {"Wassim": 12.0, "Sami": 12.0, "Karim": 0.0}


def test_un_plat_a_partager_sans_convive_designe_va_a_toute_la_table(client, db_session):
    """Case cochée, personne de coché : le sens historique de `is_shared` seul."""
    table, couscous = _table_avec_couscous(client, "dar-zarrouk-table")
    order = _commander(
        client,
        db_session,
        table,
        {
            "menu_item_id": couscous["id"],
            "quantity": 1,
            "is_shared": True,
            "shared_with": [],
            "added_by_name": "Wassim",
        },
    )

    assert compute_shares(order, CONVIVES) == {"Wassim": 8.0, "Sami": 8.0, "Karim": 8.0}


def test_un_plat_sans_assignation_reste_facture_a_son_auteur(client, db_session):
    """Le défaut de la carte : rien de coché, le plat est à celui qui l'a ajouté."""
    table, couscous = _table_avec_couscous(client, "dar-zarrouk-auteur")
    order = _commander(
        client,
        db_session,
        table,
        {"menu_item_id": couscous["id"], "quantity": 1, "added_by_name": "Karim"},
    )

    assert compute_shares(order, CONVIVES) == {"Wassim": 0.0, "Sami": 0.0, "Karim": 24.0}


def test_une_place_qui_a_quitte_la_table_ne_perd_pas_le_plat(client, db_session):
    """
    Une assignation qui ne désigne plus personne (convive parti du roster, donc
    place hors de 1..N) ne doit jamais faire disparaître le plat du calcul :
    même repli que `is_shared` sans précision, toute la table.
    """
    table, couscous = _table_avec_couscous(client, "dar-zarrouk-place-partie")
    order = _commander(
        client,
        db_session,
        table,
        {
            "menu_item_id": couscous["id"],
            "quantity": 1,
            "is_shared": True,
            "shared_with": [7],
            "added_by_name": "Wassim",
        },
    )

    assert compute_shares(order, CONVIVES) == {"Wassim": 8.0, "Sami": 8.0, "Karim": 8.0}
