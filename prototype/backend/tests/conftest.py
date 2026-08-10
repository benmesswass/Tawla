import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import model_registry  # noqa: F401 — enregistre tous les modèles
from app.core.database import Base, get_db
from app.main import app

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
