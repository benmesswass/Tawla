"""
Sonde `/health` (Phase 12.3).

C'est la route qu'un monitoring externe interroge toutes les minutes. Sa seule
raison d'exister est de dire la vérité quand ça va mal : une sonde qui répond
« ok » pendant que la base est injoignable est pire qu'aucune sonde, parce
qu'elle certifie que le service tourne au moment exact où il faut réveiller
quelqu'un.
"""
from sqlalchemy.exc import OperationalError

from app.core.database import get_db
from app.main import app


def test_health_is_ok_when_the_database_answers(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_reports_503_when_the_database_is_unreachable(client):
    class BrokenSession:
        def execute(self, *_args, **_kwargs):
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = lambda: BrokenSession()
    try:
        response = client.get("/health")
    finally:
        app.dependency_overrides[get_db] = previous

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "DATABASE_UNREACHABLE"


def test_health_never_leaks_the_connection_details(client):
    """L'erreur SQLAlchemy contient l'hôte, le port et le nom de la base. Cette
    route est publique : elle ne doit rien en dire."""
    class LeakySession:
        def execute(self, *_args, **_kwargs):
            raise OperationalError(
                "SELECT 1", {}, Exception("could not connect to db.interne.tawla.tn:5432")
            )

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = lambda: LeakySession()
    try:
        response = client.get("/health")
    finally:
        app.dependency_overrides[get_db] = previous

    assert "tawla.tn:5432" not in response.text
    assert "could not connect" not in response.text
