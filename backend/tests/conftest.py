import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import model_registry  # noqa: F401 — enregistre tous les modèles
from app.core.database import Base, get_db
from app.core.etat_partage import magasin
from app.main import app
from app.modules.staff.models import Staff, StaffRole
from app.modules.staff import ws_tickets
from app.modules.staff.security import create_access_token, hash_password
from app.modules.tenants.models import Restaurant, SubscriptionTier

# Base SQLite en mémoire dédiée aux tests. StaticPool = une seule connexion
# partagée, sinon chaque session SQLite :memory: repart d'une DB vide.
_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


# SQLite n'applique pas les contraintes de clé étrangère sans qu'on le lui
# demande, contrairement à Postgres en production. Deux fois (MenuRegime, puis
# les repères de plan et les compteurs de facture le 2026-09-08) la purge des
# démos a laissé des lignes orphelines : la suite restait verte, Postgres
# refusait la suppression du restaurant, et *toute* création de démo échouait
# derrière — `purger_demos_expirees` tourne avant chaque `creer_demo`. Les
# tests ne servent à rien s'ils ne contraignent pas ce que la production
# contraint.
@event.listens_for(_engine, "connect")
def _appliquer_les_cles_etrangeres(dbapi_connection, _record):
    curseur = dbapi_connection.cursor()
    curseur.execute("PRAGMA foreign_keys=ON")
    curseur.close()
_TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def _override_get_db():
    db = _TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _fresh_schema():
    """Schéma recréé à chaque test : aucune fuite d'état entre les tests."""
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture(autouse=True)
def _magasin_partage_neuf():
    """
    Tout l'état hors base vit dans `core/etat_partage.py::magasin` depuis P2.1
    — panier de table, roster des convives, mode de répartition, compteurs du
    limiteur de débit. Une seule remise à zéro les couvre donc tous, là où il
    en fallait deux avant.

    Les deux raisons d'origine tiennent toujours, et elles sont
    indépendantes :

    - **Le limiteur** (20 req/60 s par IP+route) : toute la suite tourne dans
      le même processus depuis la même « IP » TestClient. Sans remise à zéro,
      le nombre total d'appels d'authentification de la suite finit par
      déclencher des 429 et les tests deviennent dépendants de leur ordre et
      de leur nombre (découvert Phase 12.1).
    - **Les magasins de table** : ils ne sont plus purgés sur simple
      déconnexion (2026-09-09, seul `release_table` le fait). Sans remise à
      zéro, un test qui rouvre un canal de table hériterait du panier laissé
      par le test précédent.
    """
    magasin.reinitialiser()
    yield
    magasin.reinitialiser()


@pytest.fixture(autouse=True)
def _no_real_analytics(monkeypatch):
    """
    Empêche tout envoi réel à PostHog pendant les tests, même si
    POSTHOG_API_KEY est posée dans backend/.env (cas du poste de dev local) —
    sinon chaque test qui traverse settle_subscription_payment pollue le
    projet PostHog réel avec des faux événements purchase_completed.
    """
    monkeypatch.setattr("app.core.analytics._client", None)
    yield


@pytest.fixture()
def db_session():
    """Session sur la base de test, pour préparer un état directement en base
    quand passer par l'API n'apporte rien au test."""
    db = _TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_restaurant(
    name: str = "Resto de test",
    slug: str | None = None,
    subscription_tier: SubscriptionTier = SubscriptionTier.BUSINESS,
    subscription_period_end=None,
    is_active: bool = True,
    custom_promo_discount_percent: int | None = None,
    custom_promo_ends_at=None,
    launch_promo_discount_percent: int | None = None,
    has_paid_for_subscription: bool = True,
) -> Restaurant:
    """
    Crée un restaurant directement en base. Remplace l'ancien
    `POST /api/v1/restaurants`, supprimé en Phase 12.2 : cet endpoint n'était
    appelé par aucun frontend, mais restait ouvert sans authentification —
    n'importe qui pouvait créer des établissements. Les tests en avaient
    besoin comme fixture, plus comme contrat public.

    Palier Business par défaut : la quasi-totalité des tests exercent le
    produit, pas le gating par palier (offre à trois paliers, 2026-08-18) —
    les tests qui testent justement ce gating passent leur propre palier.

    `subscription_period_end` : None par défaut (pilote fixé à la main, sans
    expiration) — les tests qui distinguent un palier payé en ligne d'un
    pilote gratuit (dashboard plateforme) passent leur propre échéance. Tous
    les autres défauts suivent le modèle (voir Restaurant.is_active/
    custom_promo_discount_percent/launch_promo_discount_percent/has_paid_for_subscription) :
    la quasi-totalité des tests exercent le produit, pas l'activation ou
    l'offre de lancement (2026-08-20/21) — les tests qui testent justement ça
    passent leurs propres valeurs.
    """
    db = _TestingSessionLocal()
    restaurant = Restaurant(
        name=name,
        slug=slug or f"resto-{uuid.uuid4().hex[:8]}",
        subscription_tier=subscription_tier,
        subscription_period_end=subscription_period_end,
        is_active=is_active,
        custom_promo_discount_percent=custom_promo_discount_percent,
        custom_promo_ends_at=custom_promo_ends_at,
        launch_promo_discount_percent=launch_promo_discount_percent,
        has_paid_for_subscription=has_paid_for_subscription,
    )
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    db.close()
    return restaurant


@pytest.fixture()
def client():
    # `with` obligatoire depuis Starlette 1.x (ROADMAP_PRODUCTION.md §P1.8) :
    # hors contexte, chaque `websocket_connect` ouvre SON PROPRE portail, donc
    # sa propre boucle d'événements dans son propre thread. Les files d'attente
    # de la session, autrefois des `queue.Queue` thread-safe, sont désormais des
    # flux anyio liés à cette boucle : un `broadcast` déclenché par le socket B
    # ne réveille jamais le socket A s'il attend déjà — le test se fige pour
    # toujours (vu sur `test_table_cart.py`, hang à `ws_a.receive_json()`).
    # Dans le contexte, toutes les sessions partagent un portail unique, comme
    # un processus uvicorn réel n'a qu'une boucle. Le commentaire d'origine
    # refusait le `with` à cause du `create_all()` du lifespan : celui-ci a
    # disparu à la Phase 12.2 (`app/main.py::lifespan` ne fait plus que `yield`).
    with TestClient(app) as c:
        yield c


def create_staff(restaurant_id: int, role: StaffRole = StaffRole.MANAGER, password: str = "test-pass-1234") -> Staff:
    """
    Crée un staff directement en base (pas d'endpoint de création API —
    l'onboarding staff est manuel/manager pour l'instant). Utilisé par les
    tests pour obtenir des headers auth sans passer par le flux /auth/login
    à chaque fois.
    """
    db = _TestingSessionLocal()
    staff = Staff(
        restaurant_id=restaurant_id,
        name=f"Staff {role.value}",
        role=role,
        email=f"{role.value}-{uuid.uuid4().hex[:8]}@test.local",
        password_hash=hash_password(password),
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)
    db.close()
    return staff


def auth_headers(staff: Staff) -> dict[str, str]:
    token = create_access_token(staff.id, staff.restaurant_id, staff.role.value)
    return {"Authorization": f"Bearer {token}"}


def ws_billet(staff: Staff) -> str:
    """
    Le billet à usage unique qui autorise un canal WebSocket du personnel
    (ROADMAP_PRODUCTION.md §P2.4, `staff/ws_tickets.py`).

    Délivré ici directement plutôt qu'en appelant `POST /auth/ws-ticket` :
    c'est le socket qu'on teste, pas l'échange. Un seul par connexion — le
    rejouer est précisément ce que la correction empêche.
    """
    return ws_tickets.creer_billet(staff.id)


def order_headers(order: dict) -> dict[str, str]:
    """
    En-tête des routes client d'une commande (suivi, paiement, abonnement
    push) : le `public_token` renvoyé à la création prouve que l'appel vient
    bien du navigateur qui a passé cette commande (Phase 12.2).
    """
    return {"X-Order-Token": order["public_token"]}
