"""
Démonstrations simultanées.

Ce que ces tests protègent tient en une phrase : deux restaurateurs qui font
la démo au même moment ne doivent rien partager. Un compte de démo unique
aurait mis les deux sur le même `restaurant_id`, donc sur le même canal temps
réel (`notifications/manager.py` groupe par `(restaurant_id, channel)`) — la
commande de l'un serait tombée sur l'écran cuisine de l'autre.
"""
from datetime import datetime, timedelta, timezone

from app.core.markets import FRANCE, TUNISIA
from app.modules.demo import service
from app.modules.menu.models import MenuItem
from app.modules.orders.models import Order, OrderItem
from app.modules.staff.models import Staff
from app.modules.tables.models import Table
from app.modules.tenants.models import Restaurant, SubscriptionTier



def ouvrir_demo(client):
    reponse = client.post("/api/v1/demo/sessions")
    assert reponse.status_code == 201, reponse.text
    return reponse.json()


def test_une_demo_est_utilisable_immediatement(client):
    demo = ouvrir_demo(client)

    # Palier Pro et compte actif : sans ça le visiteur tomberait sur l'écran
    # d'activation au lieu du tableau de bord, et la démo ne montrerait rien.
    entetes = {"Authorization": f"Bearer {demo['access_token']}"}
    restaurant = client.get(f"/api/v1/restaurants/{demo['restaurant_id']}", headers=entetes).json()
    assert restaurant["subscription_tier"] == "pro"

    # Le tableau de bord répond, la carte est garnie, la table est scannable.
    assert client.get(f"/api/v1/stats/dashboard/{demo['restaurant_id']}", headers=entetes).status_code == 200
    carte = client.get(f"/api/v1/menu-items/by-restaurant/{demo['restaurant_id']}", headers=entetes).json()
    assert len(carte) == len(service.CARTE)
    assert client.get(f"/api/v1/tables/by-token/{demo['qr_token']}").status_code == 200


def test_deux_demos_simultanees_sont_etanches(client):
    a = ouvrir_demo(client)
    b = ouvrir_demo(client)

    assert a["restaurant_id"] != b["restaurant_id"]
    assert a["qr_token"] != b["qr_token"]
    assert a["staff"]["email"] != b["staff"]["email"]

    # Une commande passée sur la table de A ne doit pas exister pour B.
    table_a = client.get(f"/api/v1/tables/by-token/{a['qr_token']}").json()
    carte_a = client.get(
        f"/api/v1/menu-items/by-restaurant/{a['restaurant_id']}",
        headers={"Authorization": f"Bearer {a['access_token']}"},
    ).json()
    creation = client.post(
        "/api/v1/orders",
        json={
            "qr_token": a["qr_token"],
            "items": [{"menu_item_id": carte_a[0]["id"], "quantity": 1}],
        },
    )
    assert creation.status_code == 201, creation.text

    actives_a = client.get(
        f"/api/v1/orders/by-restaurant/{a['restaurant_id']}/active",
        headers={"Authorization": f"Bearer {a['access_token']}"},
    ).json()
    actives_b = client.get(
        f"/api/v1/orders/by-restaurant/{b['restaurant_id']}/active",
        headers={"Authorization": f"Bearer {b['access_token']}"},
    ).json()
    assert len(actives_a) == 1
    assert actives_a[0]["table_id"] == table_a["id"]
    assert actives_b == []


def test_le_manager_dune_demo_ne_voit_pas_lautre(client):
    a = ouvrir_demo(client)
    b = ouvrir_demo(client)

    # Même garde que pour deux vrais clients : le jeton de A ne franchit pas
    # la frontière de B. C'est l'isolation multi-tenant existante qui fait le
    # travail — ce test vérifie que la démo en bénéficie vraiment.
    interdit = client.get(
        f"/api/v1/stats/dashboard/{b['restaurant_id']}",
        headers={"Authorization": f"Bearer {a['access_token']}"},
    )
    assert interdit.status_code == 403


def test_une_demo_expiree_est_effacee_entierement(client, db_session):
    demo = ouvrir_demo(client)
    rid = demo["restaurant_id"]
    carte = client.get(
        f"/api/v1/menu-items/by-restaurant/{rid}",
        headers={"Authorization": f"Bearer {demo['access_token']}"},
    ).json()
    client.post(
        "/api/v1/orders",
        json={"qr_token": demo["qr_token"], "items": [{"menu_item_id": carte[0]["id"], "quantity": 2}]},
    )

    restaurant = db_session.get(Restaurant, rid)
    restaurant.demo_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    assert service.purger_demos_expirees(db_session) == 1

    # Rien ne doit survivre : ni la commande, ni ses lignes, ni les comptes,
    # ni les tables, ni la carte. Une purge partielle laisserait des lignes
    # orphelines que plus rien ne référence.
    assert db_session.get(Restaurant, rid) is None
    for modele in (Staff, Table, MenuItem, Order):
        assert db_session.query(modele).filter(modele.restaurant_id == rid).count() == 0
    assert db_session.query(OrderItem).count() == 0


def test_une_demo_vivante_survit_a_la_purge(client, db_session):
    demo = ouvrir_demo(client)
    assert service.purger_demos_expirees(db_session) == 0
    assert db_session.get(Restaurant, demo["restaurant_id"]) is not None


def test_la_purge_refuse_un_vrai_restaurant(db_session):
    """
    Garde-fou : `supprimer_demo` efface un établissement entier. Si un jour
    elle est appelée sur un vrai client — par un script, par erreur — elle
    doit refuser plutôt que de détruire des données irrécupérables.
    """
    vrai = Restaurant(name="Vrai client", slug="vrai-client", subscription_tier=SubscriptionTier.PRO)
    db_session.add(vrai)
    db_session.commit()

    try:
        service.supprimer_demo(db_session, vrai)
        raise AssertionError("la suppression aurait dû être refusée")
    except ValueError as erreur:
        assert "pas une démo" in str(erreur)
    assert db_session.get(Restaurant, vrai.id) is not None


def test_le_plafond_refuse_plutot_que_de_remplir_la_base(client, monkeypatch):
    monkeypatch.setattr(service, "PLAFOND_DEMOS", 1)
    ouvrir_demo(client)
    refus = client.post("/api/v1/demo/sessions")
    assert refus.status_code == 503
    assert refus.json()["detail"]["code"] == "DEMO_UNAVAILABLE"


def test_les_liens_serveur_et_cuisine_authentifient_le_bon_role(client):
    """
    Sans ces deux jetons, un vendeur ne peut ouvrir l'écran serveur ou cuisine
    que sur l'appareil qui a créé la démo — les comptes serveur et cuisine ont
    un mot de passe généré aléatoirement, jamais révélé (creer_demo), donc
    impossible à saisir sur un deuxième appareil. C'est exactement le mur
    rencontré en montrant Tawla à un vrai restaurateur : le client commande
    sur son téléphone, mais rien d'autre ne peut alors afficher l'écran
    serveur en direct.
    """
    demo = ouvrir_demo(client)

    pour_serveur = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {demo['waiter_access_token']}"}
    ).json()
    assert pour_serveur["role"] == "waiter"
    assert pour_serveur["restaurant_id"] == demo["restaurant_id"]

    pour_cuisine = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {demo['kitchen_access_token']}"}
    ).json()
    assert pour_cuisine["role"] == "kitchen"
    assert pour_cuisine["restaurant_id"] == demo["restaurant_id"]

    # Trois comptes, trois rôles distincts : jamais deux jetons pour le même.
    assert len({demo["access_token"], demo["waiter_access_token"], demo["kitchen_access_token"]}) == 3


def test_le_jeton_serveur_dune_demo_ne_donne_pas_acces_a_lautre(client):
    a = ouvrir_demo(client)
    b = ouvrir_demo(client)

    # Le jeton serveur de A doit rester cantonné au restaurant de A, comme
    # n'importe quel jeton staff — même garde que pour un vrai compte. Route
    # ouverte à tout rôle staff (pas seulement manager) : l'échec doit venir
    # de l'isolation par restaurant, pas d'un rôle insuffisant.
    interdit = client.get(
        f"/api/v1/orders/by-restaurant/{b['restaurant_id']}/active",
        headers={"Authorization": f"Bearer {a['waiter_access_token']}"},
    )
    assert interdit.status_code == 403


def test_une_demo_nest_pas_comptee_comme_un_client_payant(client, db_session):
    demo = ouvrir_demo(client)
    restaurant = db_session.get(Restaurant, demo["restaurant_id"])
    assert restaurant.is_demo is True
    # Actif pour être utilisable, mais jamais marqué comme ayant payé : la vue
    # admin cross-tenant ne doit pas prendre une démo pour un client acquis.
    assert restaurant.is_active is True
    assert restaurant.has_paid_for_subscription is False


# --- Démo française : une brasserie, pas une carte tunisienne traduite ---
# (MARCHE_FRANCE.md §3.2, étape 7) — `market=FRANCE` explicite plutôt que de
# dépendre de `MARKET` au démarrage du process de test (même patron que
# `format_money(amount, market=...)`, core/currency.py).


def test_la_demo_francaise_ne_montre_jamais_dar_chaabane(db_session):
    restaurant, _, _ = service.creer_demo(db_session, market=FRANCE)
    assert "Dar Chaabane" not in restaurant.name
    assert restaurant.name == "Brasserie du Vieux Marché (démo)"


def test_la_demo_francaise_a_une_formule_et_une_carte_des_vins(db_session):
    restaurant, _, _ = service.creer_demo(db_session, market=FRANCE)
    items = db_session.query(MenuItem).filter(MenuItem.restaurant_id == restaurant.id).all()
    categories = {item.category for item in items}
    assert "Formules" in categories
    assert "Vins" in categories
    assert "Ftour" not in categories
    assert len(items) == len(service.CARTE_FR)


def test_la_demo_tunisienne_reste_inchangee_par_defaut(db_session):
    restaurant, _, _ = service.creer_demo(db_session, market=TUNISIA)
    assert restaurant.name == "Dar Chaabane (démo)"
    items = db_session.query(MenuItem).filter(MenuItem.restaurant_id == restaurant.id).all()
    assert len(items) == len(service.CARTE)
    assert {item.category for item in items} == {"Entrées", "Plats", "Desserts", "Boissons"}


def test_la_demo_francaise_a_une_equipe_aux_prenoms_francais(db_session):
    _, par_role, _ = service.creer_demo(db_session, market=FRANCE)
    noms = {compte.name for compte in par_role.values()}
    assert noms == {"Julie (manager)", "Thomas (serveur)", "Nicolas (cuisine)"}
    for compte in par_role.values():
        assert compte.email.endswith(".demo.tawla.fr")
