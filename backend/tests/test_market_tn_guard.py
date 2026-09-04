"""
Garde de non-régression pour le critère de sortie de la Phase F3
(`MARCHE_FRANCE.md` §6) : « `MARKET=tn` — les 299 tests passent sans
modification. » Ce critère n'avait jamais été prouvé par un test DÉDIÉ —
seulement observé en filigrane par le fait que la suite entière tourne par
défaut sous le marché tunisien (aucun `MARKET` posé en test, voir
`pytest.ini`/`conftest.py`).

`test_markets.py::test_tunisia_is_the_default_market` couvre déjà la
résolution du marché lui-même (`get_market()` -> `TUNISIA`). Ce fichier va
plus loin : un parcours RÉEL de bout en bout (carte -> commande -> paiement
-> facture), sous le marché par défaut, qui aurait attrapé chacun des bugs
réels trouvés et corrigés en construisant les fonctionnalités France de ce
même chantier — chacun un cas où une valeur par défaut pensée pour la France
avait fini codée en dur au point de fuiter sur la Tunisie si on n'y prenait
pas garde : `is_halal` (F5/A6), la ventilation TVA et le numéro de facture
(F5/A4, Phase 22), le paiement carte simulé (jamais Konnect/Stripe sans
PAYMENT_MODE explicite).
"""
from app.core import invoice as invoice_module
from app.core.invoice import generate_invoice_pdf
from app.core.markets import TUNISIA, get_market
from app.modules.orders.models import Order
from app.modules.staff.models import StaffRole
from app.modules.tenants.models import Restaurant
from tests.conftest import auth_headers, create_restaurant, create_staff, order_headers


def test_tunisia_is_the_default_market_for_this_entire_suite():
    """Prémisse de tout ce fichier, et de la suite entière : si ce test
    échoue un jour, plus aucun des tests "par défaut" de ce dépôt ne couvre
    réellement la Tunisie — ils couvriraient la France sans le savoir."""
    assert get_market() is TUNISIA


def test_tunisia_end_to_end_order_stays_unaffected_by_france_only_features(client, db_session):
    manager_headers = auth_headers(create_staff(create_restaurant(slug="tn-guard-e2e").id, StaffRole.MANAGER))
    # Récupère le restaurant fraîchement créé pour ses vérifications (le
    # helper ci-dessus ne renvoie que les headers).
    restaurant = db_session.query(Restaurant).filter_by(slug="tn-guard-e2e").one()

    # 1) Carte : aucun champ France explicitement posé — les défauts doivent
    # rester ceux d'avant les chantiers F4/F5/F6.
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Couscous royal", "price": 18.0},
        headers=manager_headers,
    ).json()
    assert item["is_halal"] is True  # F5/A6 : jamais False par défaut ici
    assert item["vat_category"] is None  # F5/A4
    assert item["allergen_codes"] is None  # F5/A6

    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=manager_headers
    ).json()

    # 2) Commande, confirmation, paiement carte — sans PAYMENT_MODE posé
    # (défaut de ce process de test), donc forcément simulé : ni Konnect ni
    # Stripe ne doivent jamais être sollicités ici.
    order = client.post(
        "/api/v1/orders",
        json={"qr_token": table["qr_token"], "items": [{"menu_item_id": item["id"], "quantity": 2}]},
    ).json()
    client.post(f"/api/v1/orders/{order['id']}/confirm", headers=manager_headers)
    paid = client.post(
        f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0}, headers=order_headers(order)
    ).json()

    assert paid["payment_status"] == "paid"  # réglé immédiatement (mode démo)
    assert paid.get("pay_url") is None  # jamais de redirection Konnect/Stripe

    # 3) Facture : jamais de numéro (Phase 22, MARCHE_FRANCE.md F5/A4 —
    # `Market.invoice_threshold is None` en Tunisie), jamais de ventilation
    # TVA, et le rendu PDF continue de fonctionner exactement comme avant
    # que la France n'existe dans ce code.
    db_order = db_session.get(Order, order["id"])
    db_session.refresh(db_order)
    assert db_order.invoice_number is None

    assert generate_invoice_pdf(db_order, restaurant)
    # `_pdf_money` (core/invoice.py) n'a jamais été appelé qu'avec le marché
    # France dans les tests dédiés à la facture (test_invoice.py) — ici,
    # c'est le marché RÉELLEMENT servi par ce process qui est exercé.
    assert invoice_module._pdf_money(paid["total_amount"]).endswith("DT")
