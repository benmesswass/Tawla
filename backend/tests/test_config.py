from pathlib import Path

import pytest

from app.core.config import Settings


def test_refuses_dev_secret_in_production():
    with pytest.raises(ValueError):
        Settings(
            env="production", jwt_secret="dev-only-secret-change-in-production",
            admin_creation_secret="a-real-generated-secret",
        )


def test_refuses_dev_admin_creation_secret_in_production():
    with pytest.raises(ValueError):
        Settings(
            env="production", jwt_secret="a-real-generated-secret",
            admin_creation_secret="dev-only-admin-secret-change-in-production",
        )


def test_accepts_real_secret_in_production():
    Settings(env="production", jwt_secret="a-real-generated-secret", admin_creation_secret="another-real-secret")


def test_dev_secret_allowed_outside_production():
    Settings(
        env="development", jwt_secret="dev-only-secret-change-in-production",
        admin_creation_secret="dev-only-admin-secret-change-in-production",
    )


def test_cors_origins_splits_and_strips_comma_separated_list():
    settings = Settings(frontend_origin="https://tawla.tn, https://www.tawla.tn ,")
    assert settings.cors_origins == ["https://tawla.tn", "https://www.tawla.tn"]


def test_cors_origins_defaults_to_local_frontend():
    settings = Settings(frontend_origin="http://localhost:3000")
    assert settings.cors_origins == ["http://localhost:3000"]


def test_every_setting_appears_in_env_example():
    """
    `.env.example` est la liste qui fait foi pour une mise en ligne — c'est
    elle que `terrain/MISE_EN_LIGNE.md` et la Phase 20 de la roadmap citent.
    Un réglage ajouté à `Settings` sans y être documenté est invisible pour
    celui qui déploie.

    Ce n'est pas théorique : le déploiement du 2026-08-23 a échoué parce que
    `ADMIN_CREATION_SECRET`, introduit deux jours plus tôt, n'était posé nulle
    part sur l'hébergeur. Le conteneur a refusé de démarrer — le garde-fou a
    bien fonctionné, c'est la documentation qui avait dérivé.

    Même esprit que `test_migrations.py` : la CI ne peut pas voir un écart
    entre le code et ce qui sera réellement configuré en production, sauf si
    on le lui fait comparer.
    """
    exemple = (Path(__file__).resolve().parent.parent / ".env.example").read_text(encoding="utf-8")
    documentees = {
        ligne.split("=", 1)[0].strip()
        for ligne in exemple.splitlines()
        if "=" in ligne and not ligne.lstrip().startswith("#")
    }
    manquantes = sorted(nom.upper() for nom in Settings.model_fields if nom.upper() not in documentees)

    assert not manquantes, (
        "Ces réglages existent dans Settings mais ne sont pas dans backend/.env.example :\n  "
        + "\n  ".join(manquantes)
        + "\n\nLes y ajouter, avec un commentaire disant à quoi ils servent et comment "
        "générer une valeur — sinon personne ne saura les poser au déploiement."
    )
