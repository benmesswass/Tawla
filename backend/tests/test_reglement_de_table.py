"""
Le règlement au niveau de la TABLE : encaissable par le serveur (sans demande
du client), visible en salle, et compté honnêtement au patron.

Trois défauts fermés ici, tous de la même famille — Tawla savait encaisser un
paiement mais pas l'enregistrer quand le client ne le demandait pas depuis son
téléphone, pas le montrer au serveur, et pas le compter tant que la commande
n'était pas soldée en entier.
"""
from datetime import timedelta

from app.core.dates import service_day_start
from app.modules.orders.models import Order, OrderPayment, OrderPaymentStatus, PaymentMethod, PaymentStatus
from app.modules.orders.reglement import montant_encaisse, reglements_du_restaurant, reste_a_encaisser
from app.modules.staff.models import StaffRole
from app.modules.stats.service import revenue_by_method
from tests.conftest import _TestingSessionLocal, auth_headers, create_restaurant, create_staff, order_headers


def _salle(nom="Café Règlement", slug="cafe-reglement", prix=20):
    """Un restaurant, un manager, une table, un plat — le décor minimal."""
    restaurant = create_restaurant(name=nom, slug=slug)
    headers = auth_headers(create_staff(restaurant.id))
    return restaurant, headers, prix


def _table(client, restaurant, headers, label="Table 1"):
    return client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": label}, headers=headers
    ).json()


def _plat(client, restaurant, headers, prix=20, nom="Couscous"):
    return client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": nom, "price": prix},
        headers=headers,
    ).json()


def _commande(client, table, item, headers, quantity=2, confirmee=True):
    order = client.post(
        "/api/v1/orders",
        json={"qr_token": table["qr_token"], "items": [{"menu_item_id": item["id"], "quantity": quantity}]},
    ).json()
    if confirmee:
        confirmee_res = client.post(f"/api/v1/orders/{order['id']}/confirm", headers=headers).json()
        order = {**order, **confirmee_res}
    return order


def _servir(client, order, headers):
    """Jusqu'au bout de la cuisine : c'est l'état d'une table qu'on encaisse
    puis qu'on libère."""
    for etape in ("send-to-kitchen", "start-preparation", "mark-ready", "mark-served"):
        client.post(f"/api/v1/orders/{order['id']}/{etape}", headers=headers)


def _decor(client, quantity=2, slug="cafe-reglement"):
    restaurant, headers, prix = _salle(slug=slug, prix=20)
    table = _table(client, restaurant, headers)
    item = _plat(client, restaurant, headers, prix=prix)
    order = _commande(client, table, item, headers, quantity=quantity)
    return restaurant, headers, table, item, order


# ─────────────────────────── Encaissement par le serveur ───────────────────────────


def test_le_serveur_encaisse_le_restant_sans_demande_du_client(client):
    """Le cas ordinaire en salle : la table paie en espèces au comptoir, sans
    avoir rien demandé depuis son téléphone. Aucun chemin n'existait pour
    l'enregistrer — la commande restait UNPAID pour toujours."""
    _restaurant, headers, _table_, _item, order = _decor(client)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/collect", json={"method": "cash"}, headers=headers)

    assert res.status_code == 200
    body = res.json()
    assert body["payment_status"] == "paid"
    assert body["amount_paid"] == 40
    assert body["amount_remaining"] == 0
    assert body["payment_method"] == "cash"


def test_un_encaissement_serveur_emet_la_facture(client):
    """Même chemin de finalisation que les autres moyens : sans numéro de
    facture, un règlement encaissé à la main n'aurait pas de note."""
    _restaurant, headers, _table_, _item, order = _decor(client)

    client.post(f"/api/v1/orders/{order['id']}/pay/collect", json={"method": "cash"}, headers=headers)

    with _TestingSessionLocal() as db:
        enregistree = db.get(Order, order["id"])
        assert enregistree.paid_at is not None
        payment = db.query(OrderPayment).filter(OrderPayment.order_id == order["id"]).one()
        assert payment.status == OrderPaymentStatus.PAID
        assert payment.method == PaymentMethod.CASH


def test_un_encaissement_serveur_garde_la_trace_de_qui_a_encaisse(client):
    """« Qui a pris cet argent » n'avait aucune réponse : la colonne
    n'existait pas."""
    restaurant, _manager, prix = _salle()
    manager_headers = auth_headers(create_staff(restaurant.id))
    serveur = create_staff(restaurant.id, role=StaffRole.WAITER, password="test-pass-5678")
    table = _table(client, restaurant, manager_headers)
    item = _plat(client, restaurant, manager_headers, prix=prix)
    order = _commande(client, table, item, manager_headers)

    client.post(
        f"/api/v1/orders/{order['id']}/pay/collect",
        json={"method": "card_terminal"},
        headers=auth_headers(serveur),
    )

    with _TestingSessionLocal() as db:
        payment = db.query(OrderPayment).filter(OrderPayment.order_id == order["id"]).one()
        assert payment.collected_by_staff_id == serveur.id
        assert payment.collected_by_name == serveur.name


def test_un_encaissement_partiel_laisse_la_commande_partiellement_reglee(client):
    _restaurant, headers, _table_, _item, order = _decor(client)

    res = client.post(
        f"/api/v1/orders/{order['id']}/pay/collect", json={"method": "cash", "amount": 15}, headers=headers
    )

    assert res.status_code == 200
    body = res.json()
    assert body["payment_status"] == "partially_paid"
    assert body["amount_paid"] == 15
    assert body["amount_remaining"] == 25


def test_le_serveur_ne_peut_pas_encaisser_plus_que_le_restant(client):
    _restaurant, headers, _table_, _item, order = _decor(client)

    res = client.post(
        f"/api/v1/orders/{order['id']}/pay/collect", json={"method": "cash", "amount": 100}, headers=headers
    )

    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "AMOUNT_ABOVE_REMAINING"


def test_le_serveur_doit_confirmer_une_demande_en_attente_plutot_que_dencaisser(client):
    """Sans ce refus, la part demandée par le client et l'encaissement du
    serveur feraient payer deux fois le même argent."""
    _restaurant, headers, _table_, _item, order = _decor(client)
    client.post(f"/api/v1/orders/{order['id']}/pay/cash", json={}, headers=order_headers(order))

    res = client.post(f"/api/v1/orders/{order['id']}/pay/collect", json={"method": "cash"}, headers=headers)

    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "PENDING_SHARE_EXISTS"


def test_un_encaissement_sur_une_commande_deja_payee_est_refuse(client):
    _restaurant, headers, _table_, _item, order = _decor(client)
    client.post(f"/api/v1/orders/{order['id']}/pay/collect", json={"method": "cash"}, headers=headers)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/collect", json={"method": "cash"}, headers=headers)

    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "ALREADY_PAID"


def test_la_carte_en_ligne_nest_pas_encaissable_a_la_main(client):
    """Elle se règle chez le fournisseur : personne en salle ne peut la
    déclarer encaissée."""
    _restaurant, headers, _table_, _item, order = _decor(client)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/collect", json={"method": "card"}, headers=headers)

    assert res.status_code == 422


def test_un_encaissement_exige_d_etre_du_bon_restaurant(client):
    _restaurant, _headers, _table_, _item, order = _decor(client)
    autre = create_restaurant(name="Ailleurs", slug="ailleurs")
    intrus = auth_headers(create_staff(autre.id, password="test-pass-9999"))

    res = client.post(f"/api/v1/orders/{order['id']}/pay/collect", json={"method": "cash"}, headers=intrus)

    assert res.status_code == 404
    assert res.json()["detail"]["code"] == "ORDER_NOT_FOUND"


def test_un_encaissement_exige_une_authentification(client):
    _restaurant, _headers, _table_, _item, order = _decor(client)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/collect", json={"method": "cash"})

    assert res.status_code in (401, 403)


# ─────────────────────────── Règlement agrégé par table ───────────────────────────


def test_le_reglement_dune_table_agrege_ses_deux_commandes(client):
    """Une table qui commande en deux temps porte deux additions séparées :
    tant que la seconde n'est pas réglée, la table ne l'est pas."""
    restaurant, headers, table, item, premiere = _decor(client)
    seconde = _commande(client, table, item, headers, quantity=1)
    client.post(f"/api/v1/orders/{premiere['id']}/pay/collect", json={"method": "cash"}, headers=headers)

    res = client.get(f"/api/v1/orders/by-restaurant/{restaurant.id}/table-settlement", headers=headers)

    assert res.status_code == 200
    etat = res.json()[0]
    assert etat["table_id"] == table["id"]
    assert etat["orders_count"] == 2
    assert etat["total_amount"] == 60
    assert etat["amount_paid"] == 40
    assert etat["amount_remaining"] == 20
    assert etat["fully_paid"] is False

    client.post(f"/api/v1/orders/{seconde['id']}/pay/collect", json={"method": "cash"}, headers=headers)
    etat = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/table-settlement", headers=headers
    ).json()[0]
    assert etat["fully_paid"] is True
    assert etat["amount_remaining"] == 0


def test_le_reglement_survit_a_une_commande_servie(client):
    """Le vrai test de la persistance : une commande servie puis payée sort
    d'`ACTIVE_STATUSES`, donc de tout ce que l'écran serveur rechargeait
    jusqu'ici."""
    restaurant, headers, table, _item, order = _decor(client)
    _servir(client, order, headers)
    client.post(f"/api/v1/orders/{order['id']}/pay/collect", json={"method": "cash"}, headers=headers)

    actives = client.get(f"/api/v1/orders/by-restaurant/{restaurant.id}/active", headers=headers).json()
    etats = client.get(f"/api/v1/orders/by-restaurant/{restaurant.id}/table-settlement", headers=headers).json()

    assert actives == []
    assert etats[0]["fully_paid"] is True
    assert etats[0]["table_label"] == table["label"]


def test_les_parts_reglees_portent_le_moyen_et_qui_a_encaisse(client):
    restaurant, headers, _table_, _item, order = _decor(client)
    client.post(
        f"/api/v1/orders/{order['id']}/pay/collect",
        json={"method": "card_terminal", "amount": 10, "tip_amount": 2},
        headers=headers,
    )

    etats = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/table-settlement", headers=headers
    ).json()

    part = etats[0]["parts"][0]
    assert part["method"] == "card_terminal"
    assert part["amount"] == 10
    assert part["tip_amount"] == 2
    assert part["collected_by_name"] is not None
    assert part["paid_at"] is not None


def test_une_table_entierement_reglee_se_libere_sans_note(client):
    """La cascade du défaut d'origine : sans chemin pour enregistrer un
    encaissement, la libération réclamait une note à chaque fois."""
    _restaurant, headers, table, _item, order = _decor(client)
    _servir(client, order, headers)
    client.post(f"/api/v1/orders/{order['id']}/pay/collect", json={"method": "cash"}, headers=headers)

    res = client.post(f"/api/v1/tables/{table['id']}/release", json={}, headers=headers)

    assert res.status_code == 200
    assert res.json()["occupied_at"] is None


def test_une_table_liberee_puis_reoccupee_repart_a_zero(client):
    """Sinon la tablée suivante hériterait du règlement de la précédente."""
    restaurant, headers, table, _item, order = _decor(client)
    _servir(client, order, headers)
    client.post(f"/api/v1/orders/{order['id']}/pay/collect", json={"method": "cash"}, headers=headers)

    avant = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/table-settlement", headers=headers
    ).json()
    assert avant[0]["fully_paid"] is True

    client.post(f"/api/v1/tables/{table['id']}/release", json={}, headers=headers)
    # Nouveau scan du QR : la table est réoccupée après la commande réglée.
    client.get(f"/api/v1/tables/by-token/{table['qr_token']}")

    apres = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/table-settlement", headers=headers
    ).json()
    assert apres == []


def test_le_reglement_ignore_les_commandes_dhier(client):
    restaurant, headers, table, item, order = _decor(client)
    client.post(f"/api/v1/orders/{order['id']}/pay/collect", json={"method": "cash"}, headers=headers)
    with _TestingSessionLocal() as db:
        vieille = db.get(Order, order["id"])
        vieille.created_at = service_day_start() - timedelta(hours=2)
        db.commit()

    etats = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/table-settlement", headers=headers
    ).json()

    assert etats == []


def test_le_reglement_est_isole_entre_restaurants(client):
    restaurant, headers, _table_, _item, order = _decor(client)
    client.post(f"/api/v1/orders/{order['id']}/pay/collect", json={"method": "cash"}, headers=headers)
    autre = create_restaurant(name="Ailleurs", slug="ailleurs")
    intrus = auth_headers(create_staff(autre.id, password="test-pass-9999"))

    interdit = client.get(f"/api/v1/orders/by-restaurant/{restaurant.id}/table-settlement", headers=intrus)
    sien = client.get(f"/api/v1/orders/by-restaurant/{autre.id}/table-settlement", headers=intrus)

    assert interdit.status_code == 403
    assert sien.json() == []


def test_une_commande_annulee_ne_pese_pas_dans_le_reglement(client):
    restaurant, headers, _table_, _item, order = _decor(client)
    client.post(f"/api/v1/orders/{order['id']}/cancel", headers=headers)

    etats = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/table-settlement", headers=headers
    ).json()

    assert etats == []


# ─────────────────────────── Diffusion en salle ───────────────────────────


def test_un_paiement_en_ligne_previent_la_salle(client):
    """Il ne partait que sur le canal du client : le serveur n'apprenait
    jamais qu'une table venait de payer depuis son téléphone."""
    restaurant, headers, table, _item, order = _decor(client)
    token = headers["Authorization"].split()[1]

    with client.websocket_connect(f"/ws/staff/{restaurant.id}?token={token}") as ws:
        res = client.post(f"/api/v1/orders/{order['id']}/pay/card", json={}, headers=order_headers(order))
        assert res.status_code == 200

        msg = ws.receive_json()
        assert msg["event"] == "order.payment_settled"
        assert msg["table_id"] == table["id"]
        assert msg["table_label"] == table["label"]
        assert msg["method"] == "card"
        assert msg["amount"] == 40
        assert msg["table_fully_paid"] is True
        assert msg["table_amount_remaining"] == 0


def test_lencaissement_dun_collegue_fait_disparaitre_la_demande_des_autres_ecrans(client):
    """Le défaut symétrique : la demande restait affichée chez les autres
    serveurs, qui pouvaient aller réclamer une addition déjà encaissée."""
    restaurant, headers, table, _item, order = _decor(client)
    token = headers["Authorization"].split()[1]
    demande = client.post(
        f"/api/v1/orders/{order['id']}/pay/cash", json={"payer_name": "Salma"}, headers=order_headers(order)
    )
    assert demande.status_code == 200
    with _TestingSessionLocal() as db:
        payment_id = db.query(OrderPayment).filter(OrderPayment.order_id == order["id"]).one().id

    with client.websocket_connect(f"/ws/staff/{restaurant.id}?token={token}") as ws:
        res = client.post(
            f"/api/v1/orders/{order['id']}/pay/cash/confirm/{payment_id}", headers=headers
        )
        assert res.status_code == 200

        msg = ws.receive_json()
        assert msg["event"] == "order.payment_settled"
        assert msg["payment_id"] == payment_id
        assert msg["table_id"] == table["id"]
        assert msg["table_fully_paid"] is True


def test_un_encaissement_serveur_previent_aussi_le_client(client):
    """Le client peut avoir sa page de suivi ouverte pendant que le serveur
    encaisse au comptoir."""
    restaurant, headers, _table_, _item, order = _decor(client)

    with client.websocket_connect(
        f"/ws/order/{restaurant.id}/{order['id']}?token={order['public_token']}"
    ) as ws:
        client.post(f"/api/v1/orders/{order['id']}/pay/collect", json={"method": "cash"}, headers=headers)

        msg = ws.receive_json()
        assert msg["event"] == "order.payment_confirmed"
        assert msg["fully_paid"] is True


# ─────────────────────────── Recette réellement encaissée ───────────────────────────


def test_la_recette_compte_un_reglement_partiel(client):
    """Une table de quatre dont trois ont réglé pesait 0 DT : l'argent était
    en caisse et la recette n'en disait rien."""
    restaurant, headers, _table_, _item, order = _decor(client)
    client.post(
        f"/api/v1/orders/{order['id']}/pay/collect", json={"method": "cash", "amount": 15}, headers=headers
    )

    stats = client.get(f"/api/v1/stats/dashboard/{restaurant.id}", headers=headers).json()

    assert stats["revenue_today"] == 15
    assert stats["reste_a_encaisser_today"] == 25


def test_la_recette_dune_commande_payee_sans_parts_enregistrees_ne_disparait_pas(client):
    """Le jeu de démonstration montré aux restaurateurs et les commandes
    d'avant le paiement par personne écrivent `payment_status` sans aucune
    ligne `OrderPayment` : sans repli, leur recette tomberait à zéro."""
    restaurant, headers, _table_, _item, order = _decor(client)
    with _TestingSessionLocal() as db:
        ancienne = db.get(Order, order["id"])
        ancienne.payment_status = PaymentStatus.PAID
        ancienne.payment_method = PaymentMethod.CASH
        db.commit()
        assert ancienne.payments == []
        assert montant_encaisse(ancienne) == 40
        assert reste_a_encaisser(ancienne) == 0

    stats = client.get(f"/api/v1/stats/dashboard/{restaurant.id}", headers=headers).json()

    assert stats["revenue_today"] == 40
    assert stats["reste_a_encaisser_today"] == 0
    assert stats["revenue_by_method"] == [{"method": "cash", "amount": 40, "count": 1}]


def test_la_ventilation_ne_fond_pas_deux_moyens_en_un(client):
    """`Order.payment_method` ne porte que la méthode de la DERNIÈRE part
    réglée : une table moitié espèces moitié carte terminal doit apparaître
    dans les deux."""
    restaurant, headers, _table_, _item, order = _decor(client)
    client.post(
        f"/api/v1/orders/{order['id']}/pay/collect", json={"method": "cash", "amount": 25}, headers=headers
    )
    client.post(
        f"/api/v1/orders/{order['id']}/pay/collect", json={"method": "card_terminal"}, headers=headers
    )

    stats = client.get(f"/api/v1/stats/dashboard/{restaurant.id}", headers=headers).json()

    assert stats["revenue_today"] == 40
    assert stats["revenue_by_method"] == [
        {"method": "cash", "amount": 25, "count": 1},
        {"method": "card_terminal", "amount": 15, "count": 1},
    ]


def test_une_commande_annulee_ne_compte_ni_en_recette_ni_en_restant(client):
    restaurant, headers, _table_, _item, order = _decor(client)
    client.post(f"/api/v1/orders/{order['id']}/cancel", headers=headers)

    stats = client.get(f"/api/v1/stats/dashboard/{restaurant.id}", headers=headers).json()

    assert stats["revenue_today"] == 0
    assert stats["reste_a_encaisser_today"] == 0
    assert stats["revenue_by_method"] == []


def test_la_ventilation_et_le_reglement_lisent_les_memes_parts(client):
    """Garde-fou d'accord entre les deux écrans : le patron et le serveur
    doivent voir le même argent."""
    restaurant, headers, _table_, _item, order = _decor(client)
    client.post(f"/api/v1/orders/{order['id']}/pay/collect", json={"method": "cash"}, headers=headers)

    with _TestingSessionLocal() as db:
        commandes = db.query(Order).filter(Order.restaurant_id == restaurant.id).all()
        ventilation = revenue_by_method(commandes)
        etats = reglements_du_restaurant(db, restaurant.id)

    assert sum(ligne.amount for ligne in ventilation) == sum(etat.amount_paid for etat in etats)
