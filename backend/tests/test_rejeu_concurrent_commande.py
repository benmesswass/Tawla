"""
Rejeu concurrent d'une commande (ROADMAP_PRODUCTION.md §P1.6, F11).

Le téléphone du client garde une file hors ligne : si la réponse se perd en
plein service, il rejoue la même commande, identifiée par son `client_order_id`.
Le contrôle de rejeu était un `SELECT` suivi d'un `INSERT`, sans verrou — deux
rejeux vraiment simultanés passaient donc tous deux le `SELECT`, et le second
heurtait `uq_orders_table_client_order`. L'`IntegrityError` n'étant pas
rattrapée, le client recevait un **500** alors que sa commande existait bel et
bien. Et sa file réessayait, pour retomber sur le même 500.

La contrainte d'unicité faisait donc bien son travail (aucun doublon en base) ;
c'est la réponse qui était fausse.

Le motif de correction n'est pas inventé ici : `core/invoice_number.py` le
pratique déjà pour les deux premiers paiements concurrents de l'année —
rattraper, refaire le `SELECT`, rendre la ligne que l'autre vient de créer.

Postgres réel obligatoire : sur SQLite, le `StaticPool` de la suite sérialise
les écritures, les deux rejeux ne se chevauchent jamais et la course est
invisible. Même parti pris que les autres tests de concurrence.
"""
import os
import threading

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.modules.menu.models import MenuItem
from app.modules.orders import schemas as orders_schemas
from app.modules.orders import service as orders_service
from app.modules.orders.models import Order
from app.modules.tables.models import Table
from app.modules.tenants.models import Restaurant, SubscriptionTier

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

besoin_de_postgres = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL non posée — test de rejeu ignoré (voir docstring du module)",
)

IDENTIFIANT_DE_PANIER = "panier-du-telephone-1"


@pytest.fixture()
def salle():
    engine = create_engine(TEST_DATABASE_URL, pool_size=5, max_overflow=5)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = Session()
    restaurant = Restaurant(
        name="Chez le rejeu",
        slug="chez-le-rejeu",
        is_active=True,
        subscription_tier=SubscriptionTier.BUSINESS,
        has_paid_for_subscription=True,
    )
    db.add(restaurant)
    db.flush()
    table = Table(restaurant_id=restaurant.id, label="Table 1")
    plat = MenuItem(restaurant_id=restaurant.id, name="Couscous", price=20.0, category="Plats")
    db.add_all([table, plat])
    db.commit()
    contexte = {"qr_token": table.qr_token, "plat_id": plat.id, "table_id": table.id}
    db.close()

    yield Session, contexte

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _payload(contexte: dict) -> orders_schemas.OrderCreate:
    return orders_schemas.OrderCreate(
        qr_token=contexte["qr_token"],
        items=[orders_schemas.OrderItemCreate(menu_item_id=contexte["plat_id"], quantity=1)],
        client_order_id=IDENTIFIANT_DE_PANIER,
    )


@besoin_de_postgres
def test_deux_rejeux_simultanes_rendent_la_meme_commande(salle):
    """
    Les deux appelants passent le `SELECT` avant que l'un ne commite. Aucun ne
    doit voir d'erreur, et les deux doivent recevoir LA MÊME commande — c'est
    le `public_token` qu'ils en tirent qui leur permettra de la suivre.
    """
    Session, contexte = salle
    issues: list = []
    verrou = threading.Lock()
    depart = threading.Barrier(2)

    def _commander() -> None:
        db = Session()
        try:
            depart.wait(timeout=30)
            commande, _diffusions = orders_service.create_order(db, _payload(contexte))
            with verrou:
                issues.append(("ok", commande.id, commande.public_token))
        except Exception as err:  # noqa: BLE001 — l'échec EST le résultat mesuré
            with verrou:
                issues.append(("erreur", type(err).__name__, str(err)[:120]))
        finally:
            db.close()

    fils = [threading.Thread(target=_commander) for _ in range(2)]
    for f in fils:
        f.start()
    for f in fils:
        f.join(timeout=60)

    db = Session()
    try:
        commandes = db.query(Order).all()
        nombre_de_commandes = len(commandes)
    finally:
        db.close()

    erreurs = [i for i in issues if i[0] == "erreur"]
    assert not erreurs, (
        f"un rejeu a échoué au lieu de rendre la commande existante : {erreurs} — "
        "le téléphone du client voit un 500 alors que sa commande est bien passée"
    )
    assert len(issues) == 2
    assert nombre_de_commandes == 1, f"{nombre_de_commandes} commandes créées pour un seul panier rejoué"
    # Les deux appelants doivent pointer sur la même commande, avec le même
    # jeton de suivi : deux jetons différents et l'un des deux téléphones ne
    # pourrait plus suivre sa propre commande.
    identifiants = {i[1] for i in issues}
    jetons = {i[2] for i in issues}
    assert len(identifiants) == 1, f"deux commandes différentes rendues : {identifiants}"
    assert len(jetons) == 1, "deux `public_token` différents rendus pour la même commande"


@besoin_de_postgres
def test_un_rejeu_sequentiel_rend_toujours_la_commande_dorigine(salle):
    """
    Le témoin : le rejeu ESPACÉ dans le temps est le cas courant (la file hors
    ligne du téléphone réessaie quelques secondes plus tard). Il passait déjà,
    et la correction ne devait pas l'abîmer.
    """
    Session, contexte = salle

    db = Session()
    try:
        premiere, diffusions_premiere = orders_service.create_order(db, _payload(contexte))
        premiere_id, premier_jeton = premiere.id, premiere.public_token
        seconde, diffusions_seconde = orders_service.create_order(db, _payload(contexte))
        seconde_id, second_jeton = seconde.id, seconde.public_token
        nombre_de_commandes = db.query(Order).count()
    finally:
        db.close()

    assert seconde_id == premiere_id
    assert second_jeton == premier_jeton
    assert nombre_de_commandes == 1
    # La première création prévient l'écran serveur ; le rejeu ne doit PAS le
    # refaire, sinon la commande réapparaît alors qu'elle est déjà prise en
    # charge.
    assert diffusions_premiere, "la création d'origine doit prévenir l'écran serveur"
    assert diffusions_seconde == [], "un rejeu ne doit rien rediffuser"
