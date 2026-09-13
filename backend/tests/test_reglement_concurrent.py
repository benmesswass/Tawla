"""
Course de règlement d'une part carte (ROADMAP_PRODUCTION.md §P1.4).

Le scénario que `settle_card_payment` dit couvrir dans son propre commentaire —
« webhook + retour client arrivés en même temps » — et qu'elle ne couvrait pas :
la mise à jour dite idempotente filtrait sur `id` et `payment_ref`, deux
valeurs qui ne changent pas au règlement, mais **pas sur le statut**. Les deux
appelants obtenaient donc `rowcount = 1`, se croyaient tous deux gagnants, et
rejouaient `_after_share_paid`.

Ce que ça produisait, reproduit sur PostgreSQL le 2026-09-10 :

    fidelite order_count = 2      au lieu de 1
    facture  F2026-00002          au lieu de F2026-00001
    compteur last_number = 2      pour UNE seule commande payee

Le numéro `F2026-00001` était donc consommé et rattaché à aucune facture : un
trou dans la séquence continue, précisément l'invariant que
`core/invoice_number.py` existe pour garantir sur le marché français. Ce n'est
**pas** un double débit — le prestataire n'a encaissé qu'une fois — mais
l'e-mail et la facture PDF partaient deux fois au client.

Postgres réel obligatoire : sur SQLite, le `StaticPool` de la suite partage une
connexion unique et sérialise les écritures, donc les deux appelants ne se
chevauchent jamais et la course est invisible. Même parti pris que
`test_pool_connexions.py` et `test_concurrence_commandes.py`.
"""
import os
import threading

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import invoice_number as invoice_number_module
from app.core import markets as markets_module
from app.core import payment_provider
from app.core.database import Base
from app.core.markets import FRANCE
from app.core.payment_provider import PaymentState
from app.modules.loyalty.models import LoyaltyMember
from app.modules.menu.models import MenuItem
from app.modules.orders import service as orders_service
from app.modules.orders.models import (
    InvoiceCounter,
    Order,
    OrderItem,
    OrderPayment,
    OrderPaymentStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.modules.tables.models import Table
from app.modules.tenants.models import Restaurant, SubscriptionTier

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

besoin_de_postgres = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL non posée — test de course ignoré (voir docstring du module)",
)

TELEPHONE = "+33600000000"


class _FournisseurQuiADejaEncaisse:
    """Le prestataire confirme le paiement : c'est notre côté qui doit être
    idempotent, pas le sien."""

    def is_available(self):
        return True

    def get_payment(self, ref):
        return PaymentState(status="completed", reached_amount=10_000_000)

    def to_smallest_unit(self, amount):
        return int(amount * 1000)


@pytest.fixture()
def commande_a_regler(monkeypatch):
    """Une commande confirmée, avec une part carte PENDING et une fiche
    fidélité — les trois choses que la course abîmait."""
    engine = create_engine(TEST_DATABASE_URL, pool_size=5, max_overflow=5)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    monkeypatch.setattr(payment_provider, "get_payment_provider", lambda creds: _FournisseurQuiADejaEncaisse())
    monkeypatch.setattr(orders_service, "get_payment_provider", lambda creds: _FournisseurQuiADejaEncaisse())
    # Marché France : c'est lui qui attribue un numéro de facture, donc le seul
    # où le trou de séquence est observable. `current_market` est résolu à
    # l'import, donc poser la variable d'environnement ici arriverait trop
    # tard — on bascule les deux modules qui le lisent, comme le fait déjà
    # `test_invoice_number.py`. `payment_credentials()` importe `current_market`
    # à l'appel, d'où le patch sur le module `markets` lui-même.
    monkeypatch.setattr(markets_module, "current_market", FRANCE)
    monkeypatch.setattr(invoice_number_module, "current_market", FRANCE)

    db = Session()
    restaurant = Restaurant(
        name="Chez la course",
        slug="chez-la-course",
        is_active=True,
        subscription_tier=SubscriptionTier.PRO,
        has_paid_for_subscription=True,
    )
    restaurant.stripe_account_id = "acct_test"
    db.add(restaurant)
    db.flush()
    table = Table(restaurant_id=restaurant.id, label="Table 1")
    plat = MenuItem(restaurant_id=restaurant.id, name="Couscous", price=20.0, category="Plats")
    db.add_all([table, plat])
    db.flush()

    commande = Order(
        restaurant_id=restaurant.id,
        table_id=table.id,
        status=OrderStatus.CONFIRMED,
        loyalty_phone=TELEPHONE,
    )
    commande.items.append(
        OrderItem(menu_item_id=plat.id, menu_item_name="Couscous", unit_price=20.0, quantity=1)
    )
    db.add(commande)
    db.add(LoyaltyMember(restaurant_id=restaurant.id, phone_number=TELEPHONE))
    db.flush()
    part = OrderPayment(
        order_id=commande.id,
        payer_key="telephone-1",
        payer_name="Karim",
        amount=20.0,
        tip_amount=0,
        method=PaymentMethod.CARD,
        status=OrderPaymentStatus.PENDING,
        payment_ref="PSP-REF-1",
    )
    db.add(part)
    db.commit()
    ids = (commande.id, part.id)
    db.close()

    yield engine, Session, ids

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@besoin_de_postgres
def test_le_webhook_et_le_retour_client_ne_reglent_quune_fois(commande_a_regler):
    """
    Les deux appelants lisent la part AVANT que l'un ne commite — exactement
    « webhook + retour client arrivés en même temps ». Un seul doit gagner.
    """
    _engine, Session, (order_id, payment_id) = commande_a_regler
    resultats: list = []
    verrou = threading.Lock()
    depart = threading.Barrier(2)

    def _regler(_etiquette: str) -> None:
        db = Session()
        try:
            # Force la lecture de la part avant que l'autre ne commite : sans
            # cette barrière, le second appelant relirait une ligne déjà PAID
            # et la course ne se produirait pas.
            part = db.get(OrderPayment, payment_id)
            assert part.status == OrderPaymentStatus.PENDING
            # Borné : sans délai, un échec dans l'autre thread laisserait
            # celui-ci attendre la barrière indéfiniment, et le test
            # ressemblerait à un blocage produit alors qu'il n'en est pas un.
            depart.wait(timeout=30)
            issue, _diffusions = orders_service.settle_card_payment(db, order_id, payment_id)
            with verrou:
                resultats.append(issue)
        finally:
            db.close()

    fils = [threading.Thread(target=_regler, args=(f"appelant-{i}",)) for i in (1, 2)]
    for f in fils:
        f.start()
    for f in fils:
        f.join(timeout=60)

    assert len(resultats) == 2, "un appelant est resté bloqué"

    # Tout est lu PUIS la session est fermée, avant la moindre assertion : une
    # assertion qui échoue laisserait sinon une transaction ouverte sur les
    # tables, et le `drop_all` de la fixture attendrait ce verrou
    # indéfiniment — le test ressemblerait alors à un blocage produit.
    db = Session()
    try:
        commande = db.get(Order, order_id)
        etat_paiement = commande.payment_status
        numero_facture = commande.invoice_number
        commandes_fidelite = db.query(LoyaltyMember).one().order_count
        dernier_numero = db.query(InvoiceCounter).one().last_number
        statuts_des_parts = [p.status for p in db.query(OrderPayment).all()]
    finally:
        db.close()

    assert etat_paiement == PaymentStatus.PAID
    assert commandes_fidelite == 1, (
        f"compteur de fidélité à {commandes_fidelite} — `_after_share_paid` a tourné deux fois "
        "pour un seul paiement (l'e-mail et la facture PDF sont partis autant de fois)"
    )
    assert numero_facture == "F2026-00001", (
        f"facture {numero_facture} — un numéro a été consommé pour rien, "
        "c'est un trou dans la séquence continue exigée par émetteur"
    )
    assert dernier_numero == 1, (
        f"compteur de séquence à {dernier_numero} pour une seule commande payée"
    )
    assert statuts_des_parts == [OrderPaymentStatus.PAID]


@besoin_de_postgres
def test_un_reglement_rejoue_apres_coup_ne_change_rien(commande_a_regler):
    """
    Le cas séquentiel, plus courant que la vraie course : le webhook règle,
    puis la page de retour appelle `/pay/card/check` une seconde plus tard.
    Il passait déjà avant §P1.4 — c'est le témoin qui garantit que la
    correction n'a pas fermé la porte au rejeu légitime.
    """
    _engine, Session, (order_id, payment_id) = commande_a_regler

    db = Session()
    premier, _ = orders_service.settle_card_payment(db, order_id, payment_id)
    second, _ = orders_service.settle_card_payment(db, order_id, payment_id)
    db.close()

    assert premier == "paid"
    assert second == "pending", "un rejeu ne doit rien re-régler, et ne doit pas non plus échouer"

    db = Session()
    try:
        commandes_fidelite = db.query(LoyaltyMember).one().order_count
        numero_facture = db.get(Order, order_id).invoice_number
        dernier_numero = db.query(InvoiceCounter).one().last_number
    finally:
        db.close()
    assert commandes_fidelite == 1
    assert numero_facture == "F2026-00001"
    assert dernier_numero == 1
