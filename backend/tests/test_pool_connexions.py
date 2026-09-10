"""
Le pool de connexions et sa tenue sous WebSockets (ROADMAP_PRODUCTION.md §P1.2, §P1.3).

Ces tests ferment le défaut le plus grave trouvé par l'audit du 2026-09-10 :
chaque canal WebSocket authentifié gardait pour lui une connexion Postgres
pendant TOUTE sa durée de vie (la session ouvre une transaction à
l'authentification, et ne la referme qu'au `close()` de fin de requête — donc à
la déconnexion du client, des heures plus tard). Plafond mesuré : **14
WebSockets pour toute la plateforme**, tous restaurants confondus. Au-delà,
`pg_stat_activity` montrait 15 connexions `idle in transaction` et l'API
entière devenait injoignable.

Pourquoi un fichier séparé, et pourquoi Postgres : le reste de la suite tourne
sur SQLite en mémoire avec un `StaticPool` — une connexion unique partagée, sans
plafond. Ce défaut y est **structurellement invisible** : il fallait un vrai
pool pour le voir, ce qui explique qu'il ait survécu à 789 tests verts. Ces
tests-ci sautent donc quand `TEST_DATABASE_URL` n'est pas posée (poste de dev
sans Postgres), et tournent en CI où le service est fourni.
"""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, engine as engine_applicatif, get_db
from app.main import app
from app.modules.menu.models import MenuItem
from app.modules.tables.models import Table
from app.modules.tenants.models import Restaurant, SubscriptionTier

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

besoin_de_postgres = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL non posée — test de pool ignoré (voir docstring du module)",
)

# Pool volontairement minuscule : 2 + 3 = 5 connexions au total. Le but n'est
# pas de mesurer une capacité mais de rendre le défaut visible en quelques
# connexions plutôt qu'en quinze — et de rester rapide en CI. Avec le défaut,
# la 6ᵉ WebSocket épuisait le pool ; sans lui, on peut en ouvrir bien plus.
POOL_SIZE = 2
MAX_OVERFLOW = 3
PLAFOND_DU_POOL = POOL_SIZE + MAX_OVERFLOW
WEBSOCKETS_OUVERTES = 12


def test_le_pool_applicatif_est_dimensionne_explicitement():
    """
    Garde-fou sans Postgres : les défauts de SQLAlchemy (5 + 10, attente 30 s)
    ne doivent jamais redevenir le plafond de capacité du produit. Ce test
    échoue si quelqu'un retire le dimensionnement de `core/database.py`.
    """
    pool = engine_applicatif.pool
    assert pool.size() > 5, "pool_size est retombé au défaut SQLAlchemy (5)"
    assert pool._max_overflow > 10, "max_overflow est retombé au défaut SQLAlchemy (10)"
    assert pool._timeout <= 10, (
        "pool_timeout doit rester court : une requête qui n'obtient pas de "
        "connexion doit échouer franchement, pas pendre une demi-minute"
    )


@pytest.fixture()
def app_sur_postgres():
    """
    L'application réelle, branchée sur un Postgres réel avec un pool étroit.

    Surcharge `get_db` — le même point d'injection que `conftest.py`, restauré
    à la sortie. C'est précisément pour garder ce point d'injection utilisable
    que les canaux WebSocket conservent `Depends(get_db)` et libèrent leur
    connexion à la main plutôt que d'ouvrir une session de leur côté.
    """
    engine = create_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        # Court : sans ça, un test qui régresse mettrait 30 s par connexion à
        # échouer au lieu de 2.
        pool_timeout=2,
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    def _get_db_postgres():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    precedent = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = _get_db_postgres
    try:
        yield engine, Session
    finally:
        if precedent is not None:
            app.dependency_overrides[get_db] = precedent
        else:
            app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _preparer_salle(Session, nb_tables: int) -> tuple[int, list[str]]:
    db = Session()
    restaurant = Restaurant(
        name="Chez le pool",
        slug="chez-le-pool",
        is_active=True,
        subscription_tier=SubscriptionTier.BUSINESS,
        has_paid_for_subscription=True,
    )
    db.add(restaurant)
    db.flush()
    tables = [Table(restaurant_id=restaurant.id, label=f"Table {i}") for i in range(nb_tables)]
    db.add_all(tables)
    db.add(MenuItem(restaurant_id=restaurant.id, name="Couscous", price=20.0, category="Plats"))
    db.commit()
    identifiants = (restaurant.id, [t.qr_token for t in tables])
    db.close()
    return identifiants


@besoin_de_postgres
def test_les_websockets_de_table_ne_retiennent_aucune_connexion(app_sur_postgres):
    """
    Le test de non-régression du défaut central.

    12 tables scannent en même temps, avec un pool de 5. Avant correction, la
    6ᵉ connexion épuisait le pool : elle attendait `pool_timeout` puis échouait,
    et TOUTE l'API devenait injoignable — y compris pour les 99 autres
    restaurants. Après correction, la connexion repart au pool dès
    l'authentification faite, et le nombre de sockets ouvertes n'a plus de
    rapport avec le nombre de connexions base.
    """
    engine, Session = app_sur_postgres
    restaurant_id, qr_tokens = _preparer_salle(Session, WEBSOCKETS_OUVERTES)
    client = TestClient(app)

    assert WEBSOCKETS_OUVERTES > PLAFOND_DU_POOL, "le test ne prouverait rien sous le plafond du pool"

    ouvertes = []
    try:
        for qr_token in qr_tokens:
            cm = client.websocket_connect(f"/ws/table/{restaurant_id}/{qr_token}")
            ws = cm.__enter__()
            ouvertes.append((cm, ws))
            # Rattrapage envoyé à la connexion : panier, convives, mode de partage.
            for _ in range(3):
                ws.receive_json()

        assert len(ouvertes) == WEBSOCKETS_OUVERTES

        # Le vrai critère : la base reste jointe pendant que ces sockets vivent.
        assert client.get("/health").json() == {"status": "ok"}

        # Et personne ne tient de transaction ouverte pour rien : c'est ce que
        # montrait `idle in transaction` en production.
        with engine.connect() as conn:
            en_transaction = conn.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity "
                    "WHERE datname = current_database() AND state = 'idle in transaction'"
                )
            ).scalar_one()
        assert en_transaction == 0, (
            f"{en_transaction} connexion(s) 'idle in transaction' alors qu'aucune requête "
            "n'est en cours — une session WebSocket retient sa connexion"
        )
    finally:
        for cm, _ws in ouvertes:
            cm.__exit__(None, None, None)


@besoin_de_postgres
def test_le_panier_partage_fonctionne_toujours_apres_liberation(app_sur_postgres):
    """
    La libération ne doit pas casser ce qu'elle traverse : après avoir rendu sa
    connexion, la session doit rester utilisable pour les mutations du panier —
    qui, elles, relisent bien la base (`validate_cart_line`).
    """
    engine, Session = app_sur_postgres
    restaurant_id, qr_tokens = _preparer_salle(Session, 1)
    db = Session()
    plat = db.query(MenuItem).first()
    plat_id = plat.id
    db.close()

    client = TestClient(app)
    with client.websocket_connect(f"/ws/table/{restaurant_id}/{qr_tokens[0]}") as ws:
        for _ in range(3):
            ws.receive_json()

        ws.send_json({"action": "cart.set", "menu_item_id": plat_id, "quantity": 2})
        snapshot = ws.receive_json()
        assert snapshot["event"] == "cart.updated"
        assert [(l["menu_item_id"], l["quantity"]) for l in snapshot["lines"]] == [(plat_id, 2)]

        # Un plat inexistant doit toujours être refusé proprement, sur une
        # session qui a déjà rendu sa connexion plusieurs fois.
        ws.send_json({"action": "cart.set", "menu_item_id": 999_999, "quantity": 1})
        erreur = ws.receive_json()
        assert erreur["event"] == "cart.error"
        assert erreur["code"] == "ITEM_NOT_FOUND"

        # Et la validation, qui relit la table en base, aboutit.
        ws.send_json({"action": "cart.validate", "client_order_id": "cmd-1"})
        valide = ws.receive_json()
        assert valide["event"] == "cart.validated"
        assert valide["order_id"]

    with engine.connect() as conn:
        en_transaction = conn.execute(
            text(
                "SELECT count(*) FROM pg_stat_activity "
                "WHERE datname = current_database() AND state = 'idle in transaction'"
            )
        ).scalar_one()
    assert en_transaction == 0
