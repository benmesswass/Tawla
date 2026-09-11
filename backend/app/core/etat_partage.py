"""
L'état partagé entre instances backend (ROADMAP_PRODUCTION.md §P2.1).

Cinq choses vivaient dans des dicts de module : le panier de table, le roster
des convives, le mode de répartition, le limiteur de débit, et la diffusion
temps réel. Tant qu'il n'y a qu'un processus, un dict est le bon choix — c'est
ce que disaient déjà les docstrings de chacun de ces modules, et ils avaient
raison. Mais c'est aussi ce qui rend **une deuxième instance impossible** : une
commande passée sur l'instance A n'apparaîtrait jamais sur l'écran cuisine
connecté à l'instance B, et deux téléphones de la même table pourraient tomber
sur deux paniers différents.

**Le mode mémoire reste le défaut, et il est identique à aujourd'hui.** Sans
`REDIS_URL`, rien ne change : pas de dépendance, pas de service à payer, pas de
Redis à lancer pour `pytest`. Le mode Redis s'active par la seule présence de
la variable — même aiguillage que les autres intégrations optionnelles du
projet. Un pilote à un restaurant n'a aucune raison de payer un Redis ; P2
existe pour le jour où il y en a vingt.

**Pourquoi des champs nommés et pas un blob JSON par table.** Un panier est un
dict `{clé de ligne: ligne}`, et deux téléphones qui ajoutent un plat au même
instant écrivent deux clés différentes. Avec un blob, le second `lire →
modifier → écrire` écrase le premier et un plat disparaît de la commande. Avec
`HSET`, chaque champ est écrit indépendamment et atomiquement : la propriété
qu'un dict Python donnait gratuitement en mono-instance est conservée telle
quelle.

**L'ordre d'insertion est une garantie, pas un détail.** Le roster diffuse les
convives « dans l'ordre où chacun a rejoint » (`tables/roster.py`), ce qu'un
dict Python fait de lui-même et qu'un hash Redis ne fait pas. `MagasinRedis`
range donc un rang devant chaque valeur et trie à la lecture ; c'est interne au
magasin, les appelants ne le voient jamais.
"""
import json
import threading
import time
from uuid import uuid4
from abc import ABC, abstractmethod

from app.core.config import settings
from app.core.logging import get_logger, log_event

logger = get_logger("etat_partage")

SEPARATEUR_DE_RANG = "\x00"

# Durée de vie des clés de table côté Redis. Un panier abandonné (table qui se
# lève sans commander, téléphone qui ferme l'onglet) n'a aucune raison de
# survivre au service. Le mode mémoire, lui, ne l'a jamais fait non plus — il
# perdait tout au redémarrage, ce qui jouait le même rôle par accident.
TTL_TABLE_SECONDES = 12 * 3600


class MagasinPartage(ABC):
    """
    Le contrat minimal dont les cinq usages ont besoin. Volontairement petit :
    tout ce qu'on ajoute ici devra être écrit deux fois et testé deux fois.
    """

    @abstractmethod
    def lire(self, cle: str) -> dict[str, str]:
        """Tous les champs de `cle`, dans l'ordre où ils ont été créés."""

    @abstractmethod
    def ecrire(self, cle: str, champ: str, valeur: str) -> None:
        """Écrit un champ sans toucher aux autres. Réécrire un champ existant
        conserve sa place dans l'ordre."""

    @abstractmethod
    def retirer(self, cle: str, champ: str) -> None: ...

    @abstractmethod
    def compter(self, cle: str) -> int: ...

    @abstractmethod
    def vider(self, cle: str) -> None: ...

    @abstractmethod
    def vider_et_lire(self, cle: str) -> dict[str, str]:
        """
        Lit et supprime **en une seule opération atomique**. C'est ce qui
        garantit que deux appareils qui valident le panier au même instant ne
        transforment jamais le même panier en deux commandes : l'un des deux
        tombe forcément sur un panier déjà vide.
        """

    @abstractmethod
    def incrementer(self, cle: str, fenetre_secondes: int) -> int:
        """Compteur à fenêtre glissante (limiteur de débit) : rend le nombre
        de coups enregistrés dans la fenêtre, celui-ci compris."""

    @abstractmethod
    def publier(self, canal: str, charge: str) -> None: ...

    @property
    @abstractmethod
    def diffuse_entre_instances(self) -> bool:
        """
        `False` en mémoire : la diffusion se fait alors directement sur les
        WebSockets locales. `True` avec Redis : `broadcast` publie, et c'est
        l'écoute de fond qui livre — sur CHAQUE instance, y compris celle qui
        a publié. Sans cette distinction, le mode Redis livrerait deux fois le
        même message aux clients de l'instance émettrice.
        """

    def reinitialiser(self) -> None:
        """Vide tout. Réservé aux tests — jamais appelé par le produit."""


class MagasinMemoire(MagasinPartage):
    """
    Le comportement d'avant P2.1, à l'identique : des dicts, dans le seul
    processus qui tourne. C'est le défaut, et c'est ce que la suite de tests
    exerce de bout en bout.

    Verrouillé (`threading.Lock`) parce que les handlers `def` de FastAPI
    tournent dans un pool de threads depuis P1.1 : deux requêtes peuvent muter
    le même panier réellement en parallèle, ce qui n'était pas vrai quand tout
    passait par la boucle d'événements.
    """

    def __init__(self) -> None:
        self._champs: dict[str, dict[str, str]] = {}
        self._coups: dict[str, list[float]] = {}
        self._verrou = threading.Lock()
        self._dernier_balayage = time.monotonic()

    def lire(self, cle: str) -> dict[str, str]:
        with self._verrou:
            return dict(self._champs.get(cle, {}))

    def ecrire(self, cle: str, champ: str, valeur: str) -> None:
        with self._verrou:
            self._champs.setdefault(cle, {})[champ] = valeur

    def retirer(self, cle: str, champ: str) -> None:
        with self._verrou:
            self._champs.get(cle, {}).pop(champ, None)

    def compter(self, cle: str) -> int:
        with self._verrou:
            return len(self._champs.get(cle, {}))

    def vider(self, cle: str) -> None:
        with self._verrou:
            self._champs.pop(cle, None)

    def vider_et_lire(self, cle: str) -> dict[str, str]:
        with self._verrou:
            return dict(self._champs.pop(cle, {}))

    def incrementer(self, cle: str, fenetre_secondes: int) -> int:
        maintenant = time.monotonic()
        with self._verrou:
            self._balayer(maintenant, fenetre_secondes)
            coups = self._coups.setdefault(cle, [])
            while coups and maintenant - coups[0] > fenetre_secondes:
                coups.pop(0)
            coups.append(maintenant)
            return len(coups)

    def _balayer(self, maintenant: float, fenetre_secondes: int) -> None:
        """
        Balayage global périodique des clés devenues inactives (S-6, audit du
        2026-08-18, conservé tel quel au passage à P2.1) : le trim ci-dessus ne
        purge que la clé de la requête en cours — une IP qui ne revient jamais
        (client mobile, IP publique qui tourne) laisserait la sienne en mémoire
        pour toujours. Fuite lente mais réelle. Le mode Redis, lui, n'en a pas
        besoin : chaque clé y porte son propre `EXPIRE`.

        Appelé sous `self._verrou`.
        """
        if maintenant - self._dernier_balayage < fenetre_secondes:
            return
        self._dernier_balayage = maintenant
        expirees = [
            cle for cle, coups in self._coups.items()
            if not coups or maintenant - coups[-1] > fenetre_secondes
        ]
        for cle in expirees:
            del self._coups[cle]

    def publier(self, canal: str, charge: str) -> None:
        # Rien à faire : en mono-instance, `broadcast` écrit directement sur
        # les WebSockets locales.
        return None

    @property
    def diffuse_entre_instances(self) -> bool:
        return False

    def reinitialiser(self) -> None:
        with self._verrou:
            self._champs.clear()
            self._coups.clear()
            self._dernier_balayage = time.monotonic()


class MagasinRedis(MagasinPartage):
    """
    Le même contrat, partagé par toutes les instances.

    Un `HSET` par écriture de champ plutôt qu'un blob relu-réécrit : c'est ce
    qui conserve l'atomicité par ligne que le dict Python donnait. Le rang
    préfixé conserve l'ordre d'insertion, qu'un hash Redis ne garantit pas.
    """

    def __init__(self, url: str) -> None:
        import redis  # importé ici : le paquet n'est requis qu'en mode Redis

        self._r = redis.Redis.from_url(url, decode_responses=True)
        self._url = url

    # --- champs ---------------------------------------------------------

    def lire(self, cle: str) -> dict[str, str]:
        brut = self._r.hgetall(cle)
        ordonnes = sorted(brut.items(), key=lambda paire: _rang_de(paire[1]))
        return {champ: _valeur_de(valeur) for champ, valeur in ordonnes}

    def ecrire(self, cle: str, champ: str, valeur: str) -> None:
        existant = self._r.hget(cle, champ)
        # Réécrire un champ existant (un convive qui corrige son prénom, une
        # quantité qui change) ne doit PAS le renvoyer en fin de liste.
        rang = _rang_de(existant) if existant is not None else self._r.incr(f"{cle}:rang")
        self._r.hset(cle, champ, f"{rang}{SEPARATEUR_DE_RANG}{valeur}")
        self._prolonger(cle)

    def retirer(self, cle: str, champ: str) -> None:
        self._r.hdel(cle, champ)

    def compter(self, cle: str) -> int:
        return self._r.hlen(cle)

    def vider(self, cle: str) -> None:
        self._r.delete(cle, f"{cle}:rang")

    def vider_et_lire(self, cle: str) -> dict[str, str]:
        # MULTI/EXEC : le HGETALL et le DEL partent ensemble, aucune autre
        # instance ne peut lire entre les deux.
        pipe = self._r.pipeline(transaction=True)
        pipe.hgetall(cle)
        pipe.delete(cle, f"{cle}:rang")
        brut, _ = pipe.execute()
        ordonnes = sorted(brut.items(), key=lambda paire: _rang_de(paire[1]))
        return {champ: _valeur_de(valeur) for champ, valeur in ordonnes}

    def _prolonger(self, cle: str) -> None:
        self._r.expire(cle, TTL_TABLE_SECONDES)
        self._r.expire(f"{cle}:rang", TTL_TABLE_SECONDES)

    # --- compteur -------------------------------------------------------

    def incrementer(self, cle: str, fenetre_secondes: int) -> int:
        """
        Fenêtre glissante par `ZSET` horodaté, et non un simple `INCR` sur un
        seau d'une minute : un seau fixe laisse passer deux fois le plafond à
        cheval sur la frontière, ce qui est exactement le moment qu'un
        brute-force choisirait. Même sémantique qu'en mémoire, donc.
        """
        maintenant = time.time()
        pipe = self._r.pipeline(transaction=True)
        pipe.zremrangebyscore(cle, 0, maintenant - fenetre_secondes)
        # Membre unique : deux requêtes dans la même milliseconde, sur la même
        # instance ou sur deux, ne doivent jamais compter pour une seule.
        pipe.zadd(cle, {uuid4().hex: maintenant})
        pipe.zcard(cle)
        pipe.expire(cle, fenetre_secondes + 1)
        _, _, total, _ = pipe.execute()
        return total

    # --- diffusion ------------------------------------------------------

    def publier(self, canal: str, charge: str) -> None:
        self._r.publish(canal, charge)

    @property
    def diffuse_entre_instances(self) -> bool:
        return True

    def reinitialiser(self) -> None:
        self._r.flushdb()


def _rang_de(valeur_stockee: str) -> int:
    rang, _, _ = valeur_stockee.partition(SEPARATEUR_DE_RANG)
    try:
        return int(rang)
    except ValueError:
        return 0


def _valeur_de(valeur_stockee: str) -> str:
    _, _, valeur = valeur_stockee.partition(SEPARATEUR_DE_RANG)
    return valeur


def _construire() -> MagasinPartage:
    if not settings.redis_url:
        return MagasinMemoire()
    magasin = MagasinRedis(settings.redis_url)
    log_event(logger, "etat_partage.redis_actif")
    return magasin


magasin: MagasinPartage = _construire()


def encoder(valeur) -> str:
    return json.dumps(valeur, ensure_ascii=False)


def decoder(texte: str):
    return json.loads(texte)
