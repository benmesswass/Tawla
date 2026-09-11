"""
Montant choisi par le convive (Wassim, 2026-09-11) — champ `amount` des
requêtes de paiement.

Les deux modes de répartition ("par plat" / "équitable") étaient les deux
seules réponses possibles à « combien je paie ? ». Un convive qui veut régler
pour toute la table, ou un montant exact convenu à table, n'avait aucun chemin.

Ce que ces tests verrouillent : le montant demandé est honoré, mais plafonné à
ce qui reste dû — payer plus que l'addition ne doit jamais être possible, sans
quoi il faudrait rembourser. Payer MOINS reste permis, c'est le but : le
reliquat reste dû par la table.

Paiement carte (mode simulé, sans prestataire connecté) : il se règle
immédiatement, là où les espèces attendent la confirmation d'un serveur —
c'est donc le chemin qui montre le montant réellement encaissé en un appel.
"""
from tests.conftest import auth_headers, create_restaurant, create_staff, order_headers


def _commande_confirmee_de_40(client):
    """2 × 20 DT, confirmée : une commande payable (garde-fou F-5)."""
    restaurant = create_restaurant(name="Chez Slah", slug="chez-slah-montant")
    manager_headers = auth_headers(create_staff(restaurant.id))
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 2"}, headers=manager_headers
    ).json()
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Couscous", "price": 20},
        headers=manager_headers,
    ).json()
    order = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [{"menu_item_id": item["id"], "quantity": 2, "added_by_name": "Wassim"}],
        },
    ).json()
    confirmed = client.post(f"/api/v1/orders/{order['id']}/confirm", headers=manager_headers).json()
    return {**order, **confirmed}


def test_le_convive_peut_payer_un_montant_exact(client):
    order = _commande_confirmee_de_40(client)

    body = client.post(
        f"/api/v1/orders/{order['id']}/pay/card",
        json={"payer_key": "dev-1", "payer_name": "Wassim", "amount": 12.5},
        headers=order_headers(order),
    ).json()

    assert body["payments"][0]["amount"] == 12.5
    # Le reliquat reste dû par la table : la commande n'est pas réglée.
    assert body["amount_remaining"] == 27.5
    assert body["payment_status"] != "paid"


def test_le_convive_peut_payer_pour_toute_la_table(client):
    order = _commande_confirmee_de_40(client)

    body = client.post(
        f"/api/v1/orders/{order['id']}/pay/card",
        json={"payer_key": "dev-1", "payer_name": "Wassim", "amount": 40},
        headers=order_headers(order),
    ).json()

    assert body["payments"][0]["amount"] == 40
    assert body["payment_status"] == "paid"


def test_un_montant_superieur_au_reste_est_plafonne(client):
    """Payer plus que l'addition obligerait à rembourser : jamais accepté."""
    order = _commande_confirmee_de_40(client)

    body = client.post(
        f"/api/v1/orders/{order['id']}/pay/card",
        json={"payer_key": "dev-1", "payer_name": "Wassim", "amount": 500},
        headers=order_headers(order),
    ).json()

    assert body["payments"][0]["amount"] == 40
    assert body["payment_status"] == "paid"


def test_un_montant_nul_ou_negatif_est_refuse(client):
    order = _commande_confirmee_de_40(client)

    for montant in (0, -5):
        reponse = client.post(
            f"/api/v1/orders/{order['id']}/pay/card",
            json={"payer_key": "dev-1", "payer_name": "Wassim", "amount": montant},
            headers=order_headers(order),
        )
        assert reponse.status_code == 422


def test_sans_montant_choisi_le_calcul_du_serveur_fait_foi(client):
    """Le chemin d'avant cette fonctionnalité, inchangé."""
    order = _commande_confirmee_de_40(client)

    body = client.post(
        f"/api/v1/orders/{order['id']}/pay/card",
        json={"payer_key": "dev-1", "payer_name": "Wassim"},
        headers=order_headers(order),
    ).json()

    # Seul convive connu de la table : sa part est l'addition entière.
    assert body["payments"][0]["amount"] == 40
    assert body["payment_status"] == "paid"


def test_deux_montants_partiels_qui_totalisent_l_addition_la_referment(client):
    order = _commande_confirmee_de_40(client)

    premier = client.post(
        f"/api/v1/orders/{order['id']}/pay/card",
        json={"payer_key": "dev-1", "payer_name": "Wassim", "amount": 10},
        headers=order_headers(order),
    ).json()
    assert premier["amount_remaining"] == 30

    second = client.post(
        f"/api/v1/orders/{order['id']}/pay/card",
        json={"payer_key": "dev-2", "payer_name": "Sami", "amount": 30},
        headers=order_headers(order),
    ).json()
    assert sum(p["amount"] for p in second["payments"]) == 40
    assert second["payment_status"] == "paid"


def test_le_dernier_convive_ne_peut_pas_payer_plus_que_le_reste(client):
    """Le plafond suit les paiements déjà encaissés, pas le total d'origine."""
    order = _commande_confirmee_de_40(client)

    client.post(
        f"/api/v1/orders/{order['id']}/pay/card",
        json={"payer_key": "dev-1", "payer_name": "Wassim", "amount": 25},
        headers=order_headers(order),
    )
    second = client.post(
        f"/api/v1/orders/{order['id']}/pay/card",
        json={"payer_key": "dev-2", "payer_name": "Sami", "amount": 999},
        headers=order_headers(order),
    ).json()

    montants = sorted(p["amount"] for p in second["payments"])
    assert montants == [15, 25]
    assert second["payment_status"] == "paid"
