"""
Les migrations décrivent-elles vraiment les modèles ? (Phase 12.3)

C'est le seul écart que la suite de tests ne peut pas voir toute seule : elle
construit son schéma avec `create_all()` sur SQLite (voir conftest.py), la
production le construit avec `alembic upgrade head` sur Postgres. Un champ
ajouté à un modèle sans migration passe donc **toute** la CI et casse en
production, à la première requête qui touche la colonne absente — c'est-à-dire
en plein service.

D'où ces tests, qui font ce que fait la production : lancer les migrations,
puis comparer le schéma obtenu aux modèles.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from app.core import model_registry  # noqa: F401 — enregistre tous les modèles
from app.core.database import Base

BACKEND = Path(__file__).resolve().parent.parent


def _run_alembic(*args: str, database_url: str) -> subprocess.CompletedProcess:
    """
    Alembic tourne en sous-processus, comme en production : `alembic/env.py`
    lit l'URL depuis `settings`, déjà importé et figé dans le processus pytest.
    Un `os.environ[...]` en cours de test n'aurait aucun effet.
    """
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND,
        env={**os.environ, "DATABASE_URL": database_url},
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.fixture()
def migrated_url(tmp_path) -> str:
    url = f"sqlite:///{tmp_path / 'migrations.db'}"
    result = _run_alembic("upgrade", "head", database_url=url)
    assert result.returncode == 0, f"`alembic upgrade head` a échoué :\n{result.stderr}"
    return url


def test_migrations_produce_exactly_the_schema_of_the_models(migrated_url):
    """
    Le test qui manquait : si cette assertion tombe, c'est qu'un modèle a été
    modifié sans migration. La correction n'est jamais de modifier ce test —
    c'est `alembic revision --autogenerate -m "..."`, dans la même PR que le
    changement de modèle (cf. CLAUDE.md).
    """
    engine = create_engine(migrated_url)
    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)

    assert differences == [], (
        "Le schéma produit par les migrations ne correspond pas aux modèles.\n"
        "Écarts détectés :\n  "
        + "\n  ".join(repr(d) for d in differences)
        + "\n\nGénérer la migration manquante :\n"
        "  cd backend && alembic revision --autogenerate -m \"description\""
    )


def test_the_migration_history_has_a_single_head(migrated_url):
    """
    Deux têtes = deux branches de migrations, et `alembic upgrade head` échoue
    au démarrage du conteneur. Ça arrive dès que deux PR ajoutent chacune une
    migration sur le même parent — donc précisément quand le projet avance.
    """
    result = _run_alembic("heads", database_url=migrated_url)
    assert result.returncode == 0, result.stderr
    heads = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(heads) == 1, (
        "L'historique des migrations a plusieurs têtes — `alembic upgrade head` "
        f"échouera au démarrage :\n{result.stdout}\n"
        "Réconcilier avec `alembic merge`, ou rebaser la migration la plus récente."
    )


def test_every_migration_can_be_rolled_back(migrated_url):
    """
    Un `downgrade` cassé ne se voit que le jour où une migration doit être
    annulée en production — le pire moment pour le découvrir. On redescend
    jusqu'à la base vide, puis on remonte : les deux sens doivent tenir.
    """
    down = _run_alembic("downgrade", "base", database_url=migrated_url)
    assert down.returncode == 0, f"`alembic downgrade base` a échoué :\n{down.stderr}"

    up = _run_alembic("upgrade", "head", database_url=migrated_url)
    assert up.returncode == 0, f"remontée impossible après downgrade :\n{up.stderr}"
