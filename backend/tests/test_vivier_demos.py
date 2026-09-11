"""
Le vivier d'établissements de démonstration (ROADMAP_PRODUCTION.md §P2.6).

« Voir la démo » était la seule route publique du produit qui écrit en base, et
elle montait un restaurant complet **dans la requête** : 218 commandes et 604
lignes, 1,4 s mesurées sur 4 vCPU — donc bien plus sur les 0,5 CPU du plan
visé — en tenant une connexion du pool pendant tout ce temps. Aucun garde-fou
ne bornait sa concurrence.

Le vivier renverse le coût : les établissements sont montés d'avance, le clic
ne fait plus qu'un `UPDATE` pour en réclamer un. Ce fichier vérifie les quatre
propriétés dont dépend ce renversement :

- **réclamer donne un établissement immédiatement utilisable**, avec son équipe
  et sa table — sinon on a gagné de la latence en cassant la démo ;
- **l'expiration court à partir du clic**, pas de la pré-génération, sinon un
  visiteur hérite d'une démo déjà à moitié écoulée ;
- **une entrée périmée n'est pas servie** — l'historique est ancré sur
  « aujourd'hui », une entrée qui a dormi une nuit montrerait un tableau de
  bord vide pour la journée en cours ;
- **deux visiteurs simultanés repartent avec deux établissements distincts** —
  et celle-là ne peut se vérifier que sur Postgres (voir plus bas).
"""
import os
import threading
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.etat_partage import magasin
from app.core.markets import TUNISIA
from app.modules.demo import service
from app.modules.staff.models import StaffRole
from app.modules.tenants.models import Restaurant

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


@pytest.fixture(autouse=True)
def _verrou_propre():
    """
    Le verrou de réapprovisionnement vit dans `magasin`, un singleton de
    module : sans remise à zéro, le premier test qui le prend ferait échouer
    tous les suivants pour une raison sans rapport avec ce qu'ils mesurent.
    """
    magasin.reinitialiser()
    yield
    magasin.reinitialiser()


def _fabrique(db_session):
    """Une vraie `sessionmaker` sur le moteur des tests — `reapprovisionner_le_vivier`
    ouvre et ferme sa propre session, elle ne peut donc pas recevoir celle du test."""
    return sessionmaker(autocommit=False, autoflush=False, bind=db_session.get_bind())


def test_reclamer_du_vivier_rend_une_demo_utilisable(client, db_session):
    service.creer_demo(db_session, TUNISIA, en_vivier=True)

    reclamee = service.reclamer_du_vivier(db_session)

    assert reclamee is not None
    restaurant, comptes, table = reclamee
    assert restaurant.is_demo is True
    # L'équipe complète, pas seulement le manager : le routeur émet un jeton
    # par rôle pour ouvrir l'écran serveur et cuisine sur un autre appareil.
    assert set(comptes) == {StaffRole.MANAGER, StaffRole.WAITER, StaffRole.KITCHEN}
    assert table is not None and table.qr_token


def test_lexpiration_court_a_partir_du_clic_et_non_de_la_pregeneration(client, db_session):
    """
    Une entrée de vivier n'a pas d'expiration ; elle la reçoit en étant
    réclamée. Sans ça, un établissement monté il y a une heure donnerait au
    visiteur une démo d'une heure au lieu de deux.
    """
    en_vivier, _, _ = service.creer_demo(db_session, TUNISIA, en_vivier=True)
    assert en_vivier.demo_expires_at is None

    restaurant, _, _ = service.reclamer_du_vivier(db_session)

    # `expiration_restante` applique `as_utc` : SQLite rend des datetimes
    # naïfs là où Postgres rend des datetimes aware, et c'est l'helper que le
    # routeur utilise déjà pour cette raison.
    restant = service.expiration_restante(restaurant) - datetime.now(timezone.utc)
    assert restant > service.DUREE_DEMO - timedelta(minutes=1)


def test_une_entree_perimee_nest_pas_servie(client, db_session):
    """
    `historique.py` ancre les deux semaines de service sur « aujourd'hui ».
    Une entrée qui a dormi plus longtemps que `FRAICHEUR_VIVIER` montrerait un
    tableau de bord manager vide pour la journée en cours — précisément
    l'écran que la démo existe pour montrer. Mieux vaut repayer la création.
    """
    perimee, _, _ = service.creer_demo(db_session, TUNISIA, en_vivier=True)
    perimee.created_at = datetime.now(timezone.utc) - service.FRAICHEUR_VIVIER - timedelta(minutes=1)
    db_session.commit()

    assert service.taille_du_vivier(db_session) == 0
    assert service.reclamer_du_vivier(db_session) is None


def test_le_vivier_vide_ne_casse_pas_la_demo(client):
    """
    Le repli synchrone : vivier vide, la route doit quand même rendre une démo
    complète. Le pire cas reste celui d'avant P2.6, jamais pire.
    """
    reponse = client.post("/api/v1/demo/sessions")

    assert reponse.status_code == 201
    assert reponse.json()["qr_token"]


def test_le_reapprovisionnement_remonte_le_vivier(client, db_session):
    cree = service.reapprovisionner_le_vivier(_fabrique(db_session), TUNISIA)

    assert cree == service.TAILLE_VIVIER
    assert service.taille_du_vivier(db_session) == service.TAILLE_VIVIER


def test_le_verrou_empeche_deux_reapprovisionnements_simultanes(client, db_session):
    """
    Sans lui, dix clics sur un vivier vide lanceraient dix reconstructions
    complètes en parallèle : le défaut de concurrence de P2.6 serait déplacé
    hors requête, pas fermé. Le verrou passe par `magasin`, donc il borne
    aussi les instances entre elles dès que Redis est branché.
    """
    premier = service.reapprovisionner_le_vivier(_fabrique(db_session), TUNISIA)
    second = service.reapprovisionner_le_vivier(_fabrique(db_session), TUNISIA)

    assert premier == service.TAILLE_VIVIER
    assert second == 0, "le second passage aurait dû trouver le verrou pris"


def test_le_reapprovisionnement_ne_depasse_pas_le_plafond(client, db_session, monkeypatch):
    monkeypatch.setattr(service, "PLAFOND_DEMOS", 1)

    cree = service.reapprovisionner_le_vivier(_fabrique(db_session), TUNISIA)

    assert cree == 1, "le plafond dur doit borner le vivier, pas seulement les démos réclamées"


# --- Concurrence : Postgres obligatoire ------------------------------------

besoin_de_postgres = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL non posée — concurrence du vivier non vérifiée (voir docstring)",
)


@besoin_de_postgres
def test_une_entree_deja_verrouillee_est_sautee_et_non_servie_deux_fois():
    """
    LE test de ce fichier, et le seul qui ne peut pas tourner en mémoire.

    `reclamer_du_vivier` s'appuie sur `SELECT ... FOR UPDATE SKIP LOCKED`.
    **SQLite ignore `FOR UPDATE` en silence** : la suite en mémoire passe au
    vert avec ou sans verrouillage, exactement comme les `downgrade` de
    migrations passaient au vert sur SQLite alors qu'ils étaient cassés sur
    Postgres (§P2.5, PR #216).

    ⚠️ Écrit d'abord avec deux fils lancés sur une barrière, ce test passait
    **aussi sans `SKIP LOCKED`** : les deux connexions se sérialisaient au
    lieu de se croiser, et il ne prouvait donc rien. La course est maintenant
    provoquée et non espérée — une transaction tient explicitement la ligne la
    plus récente pendant qu'on réclame depuis une autre session :

    - avec `SKIP LOCKED`, la ligne verrouillée est sautée, on reçoit l'autre ;
    - sans, on reçoit **la ligne déjà en cours de réclamation** — deux
      visiteurs, un seul établissement, et deux démonstrations qui se voient.
    """
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    Fabrique = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    preparation = Fabrique()
    service.creer_demo(preparation, TUNISIA, en_vivier=True)
    service.creer_demo(preparation, TUNISIA, en_vivier=True)
    assert service.taille_du_vivier(preparation) == 2
    preparation.close()

    # Un premier visiteur a commencé sa réclamation : sa transaction tient la
    # ligne la plus récente — celle que `reclamer_du_vivier` choisit en
    # priorité — et ne l'a pas encore validée.
    bloqueur = Fabrique()
    verrouillee = bloqueur.execute(
        select(Restaurant.id)
        .where(Restaurant.is_demo.is_(True), Restaurant.demo_expires_at.is_(None))
        .order_by(Restaurant.created_at.desc())
        .limit(1)
        .with_for_update()
    ).scalar_one()

    autre = Fabrique()
    try:
        # Sans `SKIP LOCKED`, la lecture passe mais c'est l'`UPDATE` de
        # réclamation qui attend le verrou de l'autre transaction : le test ne
        # tombe pas, il **pend** — et en CI il brûlerait le temps du job sans
        # rien dire. Ce `lock_timeout` transforme la régression en échec franc
        # en trois secondes. En production, c'est la requête du visiteur qui
        # pendrait, en tenant une connexion du pool.
        autre.execute(text("SET lock_timeout = '3s'"))

        resultat = service.reclamer_du_vivier(autre)

        assert resultat is not None, "le second visiteur doit être servi, pas bloqué"
        assert resultat[0].id != verrouillee, (
            "le second visiteur a reçu l'établissement déjà en cours de réclamation "
            "par le premier — `SKIP LOCKED` ne joue pas"
        )
    finally:
        autre.close()
        bloqueur.rollback()
        bloqueur.close()
        engine.dispose()
