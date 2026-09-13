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

Le retour arrière, lui, est vérifié **deux fois** : sur SQLite (partout) et sur
Postgres (en CI, voir `test_le_retour_arriere_tient_aussi_sur_postgres`). Ce
n'est pas de la redondance — les deux moteurs ne rendent pas les enums pareil,
et c'est précisément là que le retour arrière se casse sans qu'on le voie.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, text

from app.core import model_registry  # noqa: F401 — enregistre tous les modèles
from app.core.database import Base

BACKEND = Path(__file__).resolve().parent.parent

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

besoin_de_postgres = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL non posée — round-trip Postgres ignoré (voir docstring du module)",
)


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


@besoin_de_postgres
def test_le_retour_arriere_tient_aussi_sur_postgres():
    """
    Le même aller-retour, sur le moteur de la production (ROADMAP_PRODUCTION.md
    §P2.5).

    Le test ci-dessus tourne sur SQLite et passait au vert alors que la
    remontée était **cassée depuis la migration initiale** : sur Postgres,
    `DROP TABLE` ne supprime pas le type enum nommé créé pour la colonne, si
    bien que `downgrade base` laissait six types derrière lui et que le
    `upgrade` suivant mourait sur « type staffrole already exists ». SQLite
    n'a pas d'enum natif — il rend un VARCHAR + CHECK — donc le défaut y est
    structurellement invisible. Le piège avait déjà été rencontré deux fois et
    corrigé migration par migration (c2e7b41f8a90, 55a307a3bc86) sans jamais
    être gardé : c'est ce test qui le garde.

    L'enjeu n'est pas théorique. Le conteneur démarre sur
    `alembic upgrade head && uvicorn` : en instance unique, une migration qui
    échoue au démarrage est une indisponibilité totale, et le retour arrière
    est le seul filet. Un filet à sens unique n'en est pas un.

    Le schéma est remis à zéro d'abord : `TEST_DATABASE_URL` est une base de
    travail que les autres tests Postgres construisent avec `create_all()`, et
    un `downgrade` partant d'une base sans `alembic_version` ne prouverait
    rien.
    """
    engine = create_engine(TEST_DATABASE_URL, isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))

    monte = _run_alembic("upgrade", "head", database_url=TEST_DATABASE_URL)
    assert monte.returncode == 0, f"`alembic upgrade head` a échoué :\n{monte.stderr}"

    descend = _run_alembic("downgrade", "base", database_url=TEST_DATABASE_URL)
    assert descend.returncode == 0, f"`alembic downgrade base` a échoué :\n{descend.stderr}"

    # Assertion volontairement plus précise que « la remontée repasse » : elle
    # nomme le coupable. Sans elle, une migration qui oublie son type enum se
    # signale par un « already exists » à des dizaines de révisions de là.
    with engine.connect() as connection:
        survivants = sorted(
            ligne[0]
            for ligne in connection.execute(
                text("SELECT typname FROM pg_type WHERE typtype = 'e'")
            )
        )

    assert survivants == [], (
        "Des types enum Postgres survivent à `downgrade base` : "
        + ", ".join(survivants)
        + ".\nLa migration qui crée chacun doit le supprimer dans son "
        "`downgrade()` :\n"
        '  postgresql.ENUM(name="<type>").drop(op.get_bind(), checkfirst=True)'
    )

    remonte = _run_alembic("upgrade", "head", database_url=TEST_DATABASE_URL)
    assert remonte.returncode == 0, f"remontée impossible après downgrade :\n{remonte.stderr}"

    engine.dispose()
