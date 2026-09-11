"""
Le plan de la requête la plus chaude du produit (ROADMAP_PRODUCTION.md §P2.3).

L'écran serveur, le plan de salle et l'écran cuisine lisent tous la même
chose — `restaurant_id = ? AND created_at >= début de la journée de service` —
à chaque montage **et à chaque reconnexion WebSocket**. C'est donc plusieurs
fois par service et par appareil, et c'est la requête qui se dégrade le plus
mal avec l'historique : sans index composite, Postgres lit l'année entière du
restaurant et jette tout ce qui n'est pas d'aujourd'hui.

Mesuré sur 73 000 commandes/an/restaurant (le chiffre de la roadmap), trois
restaurants en base :

    avant : Index Scan (restaurant_id) + Sort — Rows Removed by Filter 72 929,
            813 buffers,  8,611 ms
    après : Index Scan (restaurant_id, created_at) — Rows Removed by Filter 28,
            5 buffers,    0,092 ms

Ce test ne rejoue pas ces 219 000 lignes (ce serait des minutes de CI pour une
propriété que quelques milliers de lignes suffisent à montrer). Il vérifie la
**forme du plan**, c'est-à-dire la seule chose qui régresse silencieusement :
qu'un index composite est bien choisi, et que la borne de date est appliquée
DANS l'index (`Index Cond`) et non après coup (`Filter`). Un jour où quelqu'un
supprimerait l'index, tout resterait vert ailleurs — les résultats seraient
identiques, seulement cent fois plus lents, et personne ne le verrait avant un
service chargé.

Postgres réel obligatoire : SQLite n'a ni `EXPLAIN (FORMAT JSON)` comparable,
ni le même planificateur. Même parti pris que les autres tests de ce palier.
"""
import json
import os
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.modules.orders.models import OrderStatus
from app.modules.tables.models import Table
from app.modules.tenants.models import Restaurant, SubscriptionTier

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

besoin_de_postgres = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL non posée — test de plan ignoré (voir docstring du module)",
)

INDEX_ATTENDU = "ix_orders_restaurant_created"
# Assez d'historique pour que le planificateur ait un vrai choix à faire, assez
# peu pour rester sous la seconde en CI.
COMMANDES_PAR_RESTAURANT = 6_000


@pytest.fixture()
def salle_avec_historique():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    db = Session()
    restaurants = []
    for i in range(2):
        restaurant = Restaurant(
            name=f"Historique {i}", slug=f"historique-{i}", is_active=True,
            subscription_tier=SubscriptionTier.BUSINESS, has_paid_for_subscription=True,
        )
        db.add(restaurant)
        db.flush()
        table = Table(restaurant_id=restaurant.id, label="Table 1")
        db.add(table)
        db.flush()
        restaurants.append((restaurant.id, table.id))
    db.commit()
    db.close()

    # Une année d'historique, insérée en masse : l'ORM ligne à ligne mettrait
    # des dizaines de secondes pour un test qui ne mesure que le plan.
    debut = datetime.now(timezone.utc) - timedelta(days=365)
    pas = timedelta(minutes=int(365 * 24 * 60 / COMMANDES_PAR_RESTAURANT))
    statuts = [s.name for s in OrderStatus]
    brut = engine.raw_connection()
    curseur = brut.cursor()
    for restaurant_id, table_id in restaurants:
        curseur.executemany(
            "INSERT INTO orders (restaurant_id, table_id, status, public_token, created_at, "
            "payment_status, tip_amount) VALUES (%s,%s,%s,%s,%s,'UNPAID',0)",
            [
                (restaurant_id, table_id, statuts[n % len(statuts)],
                 f"jeton-{restaurant_id}-{n}", debut + n * pas)
                for n in range(COMMANDES_PAR_RESTAURANT)
            ],
        )
    curseur.execute("ANALYZE orders")
    brut.commit()
    curseur.close()
    brut.close()

    yield engine, Session, restaurants[0][0]

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _plan(engine, restaurant_id: int) -> dict:
    """
    Le plan de la requête de `orders/service.py::list_active_orders`, telle que
    SQLAlchemy la compile réellement — et non une réécriture à la main qui
    pourrait diverger sans que personne ne le voie.
    """
    from app.modules.orders.models import Order
    from app.modules.orders.service import ACTIVE_STATUSES

    borne = datetime.now(timezone.utc) - timedelta(hours=12)
    requete = (
        select(Order)
        .where(
            Order.restaurant_id == restaurant_id,
            Order.status.in_(ACTIVE_STATUSES),
            Order.created_at >= borne,
        )
        .order_by(Order.created_at)
    )
    with engine.connect() as conn:
        compilee = requete.compile(engine, compile_kwargs={"literal_binds": True})
        brut = conn.execute(text(f"EXPLAIN (ANALYZE, FORMAT JSON) {compilee}")).scalar_one()
    return (json.loads(brut) if isinstance(brut, str) else brut)[0]["Plan"]


def _noeuds(plan: dict):
    yield plan
    for enfant in plan.get("Plans", []):
        yield from _noeuds(enfant)


@besoin_de_postgres
def test_lecran_de_service_passe_par_lindex_composite(salle_avec_historique):
    engine, _Session, restaurant_id = salle_avec_historique
    plan = _plan(engine, restaurant_id)
    noeuds = list(_noeuds(plan))

    index_utilises = {n.get("Index Name") for n in noeuds if n.get("Index Name")}
    assert INDEX_ATTENDU in index_utilises, (
        f"l'index composite n'est pas utilisé (index vus : {index_utilises or 'aucun'}). "
        "La requête lit alors tout l'historique du restaurant à chaque montage d'écran"
    )
    assert not any(n["Node Type"] == "Seq Scan" and n.get("Relation Name") == "orders" for n in noeuds), (
        "balayage séquentiel de `orders` sur le chemin le plus chaud du produit"
    )


@besoin_de_postgres
def test_la_borne_de_journee_est_appliquee_dans_lindex_et_pas_apres(salle_avec_historique):
    """
    **Le test qui compte vraiment.** Un index peut être « utilisé » tout en
    laissant Postgres relire l'année entière : c'est exactement ce que faisait
    l'index sur `restaurant_id` seul — Index Scan, et 72 929 lignes écartées
    ensuite. Ce qui distingue les deux, c'est que `created_at` apparaisse dans
    l'`Index Cond` et non dans le `Filter`.
    """
    engine, _Session, restaurant_id = salle_avec_historique
    noeuds = list(_noeuds(_plan(engine, restaurant_id)))

    noeud = next(n for n in noeuds if n.get("Index Name") == INDEX_ATTENDU)
    assert "created_at" in noeud.get("Index Cond", ""), (
        f"la borne de journée n'est pas dans l'Index Cond : {noeud.get('Index Cond')!r} — "
        "Postgres relit donc tout l'historique avant de filtrer"
    )
    ecartees = noeud.get("Rows Removed by Filter", 0)
    assert ecartees < 500, (
        f"{ecartees} lignes écartées après lecture : la borne de date n'agit pas dans l'index. "
        "Au rythme de 73 000 commandes par an, chaque montage d'écran devient un "
        "balayage complet de l'historique"
    )
