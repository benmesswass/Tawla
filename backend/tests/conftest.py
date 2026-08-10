import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import model_registry  # noqa: F401 — enregistre tous les modèles
from app.core.database import Base, get_db
from app.main import app
from app.modules.staff.models import Staff, StaffRole
from app.modules.staff.security import create_access_token, hash_password

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
