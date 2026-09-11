"""
Le magasin d'état partagé (ROADMAP_PRODUCTION.md §P2.1).

Cinq choses vivaient dans des dicts de module — panier de table, roster des
convives, mode de répartition, limiteur de débit, diffusion temps réel — et
c'est ce qui rendait **une deuxième instance backend impossible**.

Ce fichier vérifie le **contrat** du magasin, sur les deux implémentations
avec exactement les mêmes assertions (`magasins` paramétré). C'est le cœur du
sujet : si les deux ne se comportent pas pareil, alors la suite entière, qui
tourne en mémoire, ne prouve plus rien sur la production, qui tournera sur
Redis. Le mode Redis se saute de lui-même sans `TEST_REDIS_URL` — même parti
pris que les tests PostgreSQL de P1.

Ce qui est testé porte sur des risques réels, pas sur l'API pour l'API :

- **l'ordre d'insertion** — le roster diffuse les convives « dans l'ordre où
  chacun a rejoint » ; un dict Python le fait gratuitement, un hash Redis non ;
- **l'atomicité du vider-et-lire** — c'est elle qui empêche deux appareils qui
  valident au même instant de transformer le même panier en deux commandes ;
- **l'écriture par champ** — deux téléphones qui ajoutent un plat au même
  instant ne doivent pas s'écraser l'un l'autre ;
- **la fenêtre du limiteur**, et la fuite S-6 qu'un balayage ferme.
"""
import os

import pytest

from app.core.etat_partage import MagasinMemoire, MagasinRedis

TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL")


@pytest.fixture(params=["memoire", "redis"])
def magasin(request):
    if request.param == "memoire":
        yield MagasinMemoire()
        return
    if not TEST_REDIS_URL:
        pytest.skip("TEST_REDIS_URL non posée — contrat Redis non vérifié (voir docstring)")
    m = MagasinRedis(TEST_REDIS_URL)
    m.reinitialiser()
    yield m
    m.reinitialiser()


def test_lire_rend_les_champs_dans_lordre_dinsertion(magasin):
    """
    Le roster affiche les convives dans l'ordre où chacun a rejoint. Un hash
    Redis est non ordonné : sans le rang que `MagasinRedis` range devant chaque
    valeur, la tablée se réordonnerait à chaque rafraîchissement.
    """
    for champ, valeur in [("c", "Sami"), ("a", "Amine"), ("b", "Yassine")]:
        magasin.ecrire("roster:1", champ, valeur)

    assert list(magasin.lire("roster:1").items()) == [("c", "Sami"), ("a", "Amine"), ("b", "Yassine")]


def test_reecrire_un_champ_ne_le_renvoie_pas_en_fin_de_liste(magasin):
    """Un convive qui corrige son prénom reste à sa place à table."""
    for champ, valeur in [("a", "Amine"), ("b", "Sami"), ("c", "Yassine")]:
        magasin.ecrire("roster:1", champ, valeur)

    magasin.ecrire("roster:1", "a", "Amine B.")

    assert list(magasin.lire("roster:1").items()) == [("a", "Amine B."), ("b", "Sami"), ("c", "Yassine")]


def test_deux_ecritures_de_champs_differents_ne_secrasent_pas(magasin):
    """
    Deux téléphones de la même table ajoutent chacun un plat. Avec un blob
    JSON relu-réécrit, le second écrasait le premier et un plat disparaissait
    de la commande ; avec un champ par ligne, les deux tiennent.
    """
    magasin.ecrire("panier:7", "12|sami", "couscous")
    magasin.ecrire("panier:7", "34|amine", "brik")

    assert magasin.lire("panier:7") == {"12|sami": "couscous", "34|amine": "brik"}
    assert magasin.compter("panier:7") == 2


def test_retirer_un_champ_laisse_les_autres(magasin):
    magasin.ecrire("panier:7", "a", "1")
    magasin.ecrire("panier:7", "b", "2")

    magasin.retirer("panier:7", "a")

    assert magasin.lire("panier:7") == {"b": "2"}


def test_vider_et_lire_rend_le_contenu_puis_laisse_la_cle_vide(magasin):
    """
    **Le test qui compte.** Deux appareils qui valident le panier au même
    instant : le premier repart avec les lignes, le second DOIT tomber sur un
    panier vide, sinon la table est facturée deux fois.
    """
    magasin.ecrire("panier:7", "a", "couscous")
    magasin.ecrire("panier:7", "b", "brik")

    premier = magasin.vider_et_lire("panier:7")
    second = magasin.vider_et_lire("panier:7")

    assert list(premier.items()) == [("a", "couscous"), ("b", "brik")]
    assert second == {}
    assert magasin.lire("panier:7") == {}


def test_vider_remet_aussi_lordre_a_zero(magasin):
    """
    Une table libérée puis réoccupée repart de zéro, rang compris — sinon le
    compteur de rang de `MagasinRedis` survivrait à la table et grossirait
    indéfiniment.
    """
    magasin.ecrire("roster:1", "a", "Amine")
    magasin.vider("roster:1")

    magasin.ecrire("roster:1", "z", "Sami")
    magasin.ecrire("roster:1", "y", "Karim")

    assert list(magasin.lire("roster:1").items()) == [("z", "Sami"), ("y", "Karim")]


def test_le_compteur_sarrete_bien_au_plafond_dans_la_fenetre(magasin):
    """
    Le limiteur de débit : le nᵉ appel rend n. C'est ce qui fait qu'un plafond
    de 20 laisse passer 20 appels et refuse le 21ᵉ.
    """
    valeurs = [magasin.incrementer("debit:41.226.0.1:/login", 60) for _ in range(21)]

    assert valeurs == list(range(1, 22))


def test_deux_cles_de_debit_sont_comptees_separement(magasin):
    """Le téléphone de la table d'à côté n'hérite pas du compteur du voisin."""
    magasin.incrementer("debit:a:/login", 60)
    magasin.incrementer("debit:a:/login", 60)

    assert magasin.incrementer("debit:b:/login", 60) == 1


def test_un_coup_sorti_de_la_fenetre_ne_compte_plus(magasin):
    """
    Fenêtre **glissante** et non seau fixe : un seau d'une minute laisse passer
    deux fois le plafond à cheval sur la frontière, ce qui est exactement le
    moment qu'un brute-force choisirait.
    """
    assert magasin.incrementer("debit:c:/login", 0) == 1
    assert magasin.incrementer("debit:c:/login", 0) == 1


def test_une_ip_qui_ne_revient_jamais_finit_par_etre_oubliee():
    """
    S-6 (audit du 2026-08-18), conservé au passage à P2.1 — le balayage a
    seulement changé de maison, il vivait dans `core/rate_limit.py`.

    Le trim par clé ne purge que la clé de la requête en cours : une IP qui ne
    revient jamais (client mobile, IP publique qui tourne) laisserait la sienne
    en mémoire pour toujours. Fuite lente mais réelle.

    Sans équivalent Redis à tester : là-bas chaque clé porte son propre
    `EXPIRE`, le noyau Redis s'en charge.
    """
    m = MagasinMemoire()
    m.incrementer("debit:41.226.0.99:/login", 60)
    assert "debit:41.226.0.99:/login" in m._coups

    # Force le balayage (normalement retardé d'une fenêtre) et simule le temps
    # écoulé depuis la seule requête de cette IP.
    m._dernier_balayage = 0.0
    m.incrementer("debit:autre:/login", 0)

    assert "debit:41.226.0.99:/login" not in m._coups


def test_le_mode_memoire_ne_diffuse_pas_entre_instances():
    """
    La distinction qui évite une double livraison : en mémoire, `broadcast`
    écrit directement sur les sockets locales et ne publie rien.
    """
    assert MagasinMemoire().diffuse_entre_instances is False


@pytest.mark.skipif(not TEST_REDIS_URL, reason="TEST_REDIS_URL non posée")
def test_le_mode_redis_diffuse_entre_instances():
    assert MagasinRedis(TEST_REDIS_URL).diffuse_entre_instances is True


@pytest.mark.skipif(not TEST_REDIS_URL, reason="TEST_REDIS_URL non posée")
def test_deux_marches_sur_la_meme_instance_redis_ne_se_voient_pas(monkeypatch):
    """
    Le cas que le palier gratuit de Render rend inévitable : **une seule
    instance Key Value par workspace**, donc deux marchés qui la partagent.

    Les clés sont construites sur un `table_id` (`roster:5`), qui est une clé
    primaire *par base*, et l'ADR-0003 impose une base par marché. Sans
    préfixe, la table 5 de Tunis et la table 5 de France écrivent la même clé :
    les rosters fusionnent, et deux clientèles se voient. Le défaut ne lève
    aucune erreur — il donne juste un résultat faux, ce qui est pire.
    """
    from app.core import etat_partage

    monkeypatch.setattr(etat_partage, "PREFIXE_MARCHE", "tn:")
    tunisie = MagasinRedis(TEST_REDIS_URL)
    monkeypatch.setattr(etat_partage, "PREFIXE_MARCHE", "fr:")
    france = MagasinRedis(TEST_REDIS_URL)

    tunisie.reinitialiser()
    france.reinitialiser()
    try:
        tunisie.ecrire("roster:5", "device-a", "Sami")
        france.ecrire("roster:5", "device-b", "Camille")

        assert tunisie.lire("roster:5") == {"device-a": "Sami"}
        assert france.lire("roster:5") == {"device-b": "Camille"}

        # `vider` d'un côté ne doit rien emporter de l'autre — c'est la fin de
        # service d'un restaurant tunisien, pas celle d'un restaurant français.
        tunisie.vider("roster:5")
        assert tunisie.lire("roster:5") == {}
        assert france.lire("roster:5") == {"device-b": "Camille"}

        # Et `reinitialiser` ne doit plus être un `FLUSHDB` : il emporterait
        # l'état de l'autre marché.
        tunisie.reinitialiser()
        assert france.lire("roster:5") == {"device-b": "Camille"}
    finally:
        tunisie.reinitialiser()
        france.reinitialiser()
