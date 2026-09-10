"""
Le signal avancé du pool (ROADMAP_PRODUCTION.md §P1.7).

Les cinq effondrements provoqués pendant l'audit du 2026-09-10 avaient tous la
même signature — connexions sorties du pool jusqu'au plafond, `pg_stat_activity`
rempli de lignes `idle in transaction` — et elle était lisible plusieurs
secondes avant que `/health` ne réponde 503. Personne ne la regardait, parce que
personne ne l'exposait.

Ce que ces tests protègent, dans l'ordre d'importance :

1. la mesure **voit vraiment** monter l'occupation et compte vraiment les
   connexions `idle in transaction` — sinon l'alerte est un décor ;
2. `/health` garde son contrat au caractère près, quoi qu'il arrive à la
   mesure : un moniteur externe déclenche dessus, une régression ici réveille
   quelqu'un pour rien (ou pire, ne le réveille pas) ;
3. les chiffres du pool ne sortent que sous authentification — ils disent
   combien de requêtes concurrentes suffisent à saturer le service.

Les deux premiers tests exigent un vrai PostgreSQL : sur le `StaticPool` de la
suite SQLite (connexion unique partagée, sans plafond) la question n'a pas de
sens, et `pg_stat_activity` n'existe pas. Même parti pris que
`test_pool_connexions.py`.
"""
import logging
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.pool_metrics import (
    SEUIL_ALERTE_POOL,
    MesurePool,
    journaliser_si_sature,
    mesurer_le_pool,
)
from app.modules.platform_admin import security as admin_security
from app.modules.platform_admin.models import PlatformAdmin
from app.modules.staff.models import StaffRole
from app.modules.staff.security import create_access_token, hash_password
from tests.conftest import create_restaurant, create_staff

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

besoin_de_postgres = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL non posée — test de métrique de pool ignoré (voir docstring)",
)

POOL_SIZE = 2
MAX_OVERFLOW = 2
CAPACITE = POOL_SIZE + MAX_OVERFLOW


@pytest.fixture()
def pool_etroit():
    """Un pool de 4 connexions : l'occupation se lit à l'unité près."""
    engine = create_engine(
        TEST_DATABASE_URL, pool_size=POOL_SIZE, max_overflow=MAX_OVERFLOW, pool_timeout=2
    )
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    yield Session
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@besoin_de_postgres
def test_la_mesure_voit_loccupation_monter_puis_redescendre(pool_etroit):
    """
    Le test qui compte. Une mesure qui rendrait un chiffre constant serait
    verte partout et n'annoncerait jamais rien.
    """
    Session = pool_etroit
    observateur = Session()
    try:
        observateur.execute(text("SELECT 1"))  # sort sa propre connexion du pool
        au_repos = mesurer_le_pool(observateur)
        assert au_repos is not None
        assert au_repos.capacite == CAPACITE
        assert au_repos.connexions_utilisees == 1, "seule la session observatrice tient une connexion"

        # On retient tout le reste du pool.
        retenues = []
        for _ in range(CAPACITE - 1):
            s = Session()
            s.execute(text("SELECT 1"))
            retenues.append(s)

        sature = mesurer_le_pool(observateur)
        assert sature.connexions_utilisees == CAPACITE
        assert sature.taux_occupation == 1.0

        for s in retenues:
            s.close()

        apres = mesurer_le_pool(observateur)
        assert apres.connexions_utilisees == 1, (
            "les connexions rendues au pool doivent redescendre : une mesure qui "
            "ne redescend jamais alerterait en permanence, donc plus du tout"
        )
    finally:
        observateur.close()


@besoin_de_postgres
def test_une_transaction_laissee_ouverte_est_comptee_idle_in_transaction(pool_etroit):
    """
    `idle in transaction`, c'est EXACTEMENT le défaut fermé par P1.1/P1.2 : une
    session qui garde sa transaction ouverte sans rien faire. Un remaniement de
    l'authentification WebSocket peut le réintroduire sans qu'aucun autre test
    ne rougisse — celui-ci le verrait.
    """
    Session = pool_etroit
    observateur = Session()
    coupable = Session()
    try:
        observateur.execute(text("SELECT 1"))
        avant = mesurer_le_pool(observateur)
        assert avant.idle_in_transaction == 0

        # Une requête, puis plus rien : la transaction reste ouverte.
        coupable.execute(text("SELECT 1"))
        pendant = mesurer_le_pool(observateur)
        assert pendant.idle_in_transaction == 1, (
            "une transaction laissée ouverte doit être comptée — c'est le signal "
            "qui a précédé les cinq effondrements de l'audit"
        )

        coupable.rollback()
        coupable.close()
        apres = mesurer_le_pool(observateur)
        assert apres.idle_in_transaction == 0
    finally:
        observateur.close()
        coupable.close()


def test_lalerte_se_declenche_au_dela_du_seuil_et_pas_en_deca(caplog):
    """Sans base : c'est de l'arithmétique de seuil, pas du SQL."""
    sous_le_seuil = MesurePool(connexions_utilisees=20, capacite=30, idle_in_transaction=0)
    assert sous_le_seuil.taux_occupation < SEUIL_ALERTE_POOL
    assert journaliser_si_sature(sous_le_seuil) is False

    au_seuil = MesurePool(connexions_utilisees=21, capacite=30, idle_in_transaction=4)
    with caplog.at_level(logging.WARNING, logger="pool"):
        assert journaliser_si_sature(au_seuil) is True
    assert "pool.sature" in caplog.text
    # WARNING et non INFO : c'est ce niveau qui permet à un log drain de
    # filtrer ce qui doit réveiller quelqu'un.
    assert any(r.levelno == logging.WARNING for r in caplog.records)


def test_un_pool_qui_ne_sait_pas_se_decrire_ne_declenche_rien(db_session):
    """
    Le `StaticPool` de la suite SQLite n'a ni plafond ni compteur. La mesure
    doit rendre `None` — jamais des zéros, qui se liraient « tout va bien ».
    """
    assert mesurer_le_pool(db_session) is None
    assert journaliser_si_sature(None) is False


def test_health_garde_son_contrat_exact(client):
    """
    Un moniteur externe déclenche sur ce corps et ce code. La mesure greffée
    dessus ne doit rien y ajouter, ni faire échouer la sonde.
    """
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_health_repond_toujours_ok_meme_si_la_mesure_explose(client, monkeypatch):
    """
    La mesure est une commodité, la sonde est un contrat. Si la première casse,
    la seconde ne doit pas entraîner de fausse alerte de panne.
    """
    import app.main as main

    def _mesure_qui_tombe(_db):
        raise RuntimeError("pg_stat_activity indisponible")

    monkeypatch.setattr(main, "mesurer_le_pool", _mesure_qui_tombe)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_les_chiffres_du_pool_ne_sortent_pas_sans_authentification(client):
    """
    Capacité et connexions ouvertes disent combien de requêtes concurrentes
    suffisent à saturer le service. Jamais en public.
    """
    assert client.get("/api/v1/platform-admin/pool").status_code == 401


def test_un_token_staff_nouvre_pas_la_metrique_du_pool(client, db_session):
    """Même règle que /overview : le personnel d'un restaurant n'est pas l'opérateur."""
    restaurant = create_restaurant(name="Pool", slug="pool-staff")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    jeton = create_access_token(manager.id, restaurant.id, manager.role.value)
    res = client.get("/api/v1/platform-admin/pool", headers={"Authorization": f"Bearer {jeton}"})
    assert res.status_code == 401


def test_ladmin_plateforme_lit_la_metrique(client, db_session):
    admin = PlatformAdmin(
        email="op@tawla.tn", name="Wassim",
        password_hash=hash_password("un-mot-de-passe-fort-1234"), is_active=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    res = client.get(
        "/api/v1/platform-admin/pool",
        headers={"Authorization": f"Bearer {admin_security.create_access_token(admin.id)}"},
    )
    assert res.status_code == 200
    corps = res.json()
    # Sur SQLite la mesure n'est pas possible : la réponse doit le DIRE, pas
    # inventer des zéros.
    assert corps["mesurable"] is False
    assert corps["sature"] is False
    assert corps["seuil_alerte"] == SEUIL_ALERTE_POOL
