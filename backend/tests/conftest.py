import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import model_registry  # noqa: F401 — enregistre tous les modèles
from app.core.database import Base, get_db
from app.core.rate_limit import _hits as _rate_limit_hits
from app.main import app
from app.modules.staff.models import Staff, StaffRole
from app.modules.staff.security import create_access_token, hash_password
from app.modules.tenants.models import Restaurant, SubscriptionTier

# Base SQLite en mémoire dédiée aux tests. StaticPool = une seule connexion
# partagée, sinon chaque session SQLite :memory: repart d'une DB vide.
_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
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
def _fresh_rate_limiter():
    """
    Le limiteur de débit de `/auth/login` et `/auth/register` compte les appels
    dans un dict de module (20 req/60s par IP+route). Toute la suite tourne
    dans le même processus, depuis la même « IP » TestClient : sans cette
    remise à zéro, le nombre total d'appels d'authentification de la suite
    finit par déclencher des 429, et les tests deviennent dépendants de leur
    ordre et de leur nombre. Découvert en ajoutant les tests de la Phase 12.1.
    """
    _rate_limit_hits.clear()
    yield
    _rate_limit_hits.clear()


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
    name: str = "Resto de test", slug: str | None = None, subscription_tier: SubscriptionTier = SubscriptionTier.BUSINESS
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
    """
    db = _TestingSessionLocal()
    restaurant = Restaurant(
        name=name, slug=slug or f"resto-{uuid.uuid4().hex[:8]}", subscription_tier=subscription_tier
    )
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    db.close()
    return restaurant


@pytest.fixture()
def client():
    # Volontairement PAS de "with TestClient(app) as c" : ça déclencherait
    # le lifespan de l'app (donc create_all sur la VRAIE base Postgres,
    # qui n'existe pas dans cet environnement de test).
    return TestClient(app)


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


def order_headers(order: dict) -> dict[str, str]:
    """
    En-tête des routes client d'une commande (suivi, paiement, abonnement
    push) : le `public_token` renvoyé à la création prouve que l'appel vient
    bien du navigateur qui a passé cette commande (Phase 12.2).
    """
    return {"X-Order-Token": order["public_token"]}
