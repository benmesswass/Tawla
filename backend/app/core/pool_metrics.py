"""
Le signal avancé du pool de connexions (ROADMAP_PRODUCTION.md §P1.7).

Les cinq effondrements provoqués pendant l'audit du 2026-09-10 ont tous la
même signature, et elle est lisible **plusieurs secondes avant la panne** :
les connexions sorties du pool montent jusqu'au plafond et n'y reviennent
plus, pendant que `pg_stat_activity` se remplit de lignes
`idle in transaction`. Quand `/health` se met à répondre 503, il est déjà trop
tard — le processus ne récupère jamais, seul un redémarrage le sauve.

Deux chiffres suffisent à voir venir ça, et ce sont exactement ceux-là :

- `engine.pool.checkedout()` — combien de connexions sont sorties du pool.
  Lu en mémoire, gratuit, aucune requête.
- le nombre de connexions `idle in transaction` — une session qui garde sa
  transaction ouverte sans rien faire, c'est-à-dire précisément le défaut que
  P1.1 et P1.2 ont corrigé, et celui qu'un remaniement peut réintroduire sans
  qu'aucun test ne rougisse.

Ce module ne fait que **mesurer et journaliser**. Il n'a aucune destination
d'alerte à lui : l'événement `pool.sature` sort en WARNING dans les logs
structurés, et c'est le log drain (l'autre moitié de P1.7, côté hébergeur) qui
en fait un réveil. Un module qui appellerait lui-même un service d'alerte
serait un service payant de plus et une dépendance réseau dans le chemin de
`/health` — les deux sont exclus.
"""
import logging
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_event

logger = get_logger("pool")

# 70 % : le seuil de l'audit. Assez haut pour ne pas crier pendant un coup de
# feu normal, assez bas pour laisser le temps d'agir — les effondrements
# mesurés passaient de 70 % à saturation totale en quelques secondes.
SEUIL_ALERTE_POOL = 0.7

# PostgreSQL met en cache l'état des backends pour TOUTE la durée de la
# transaction en cours : deux lectures successives de `pg_stat_activity` dans
# la même transaction rendent le même chiffre, même si dix connexions se sont
# bloquées entre les deux. Vérifié : sans cette ligne, une session qui mesure
# deux fois voit toujours son premier résultat. En production la session de
# `/health` est neuve à chaque requête, donc le piège ne se voit pas — mais un
# appelant qui mesurerait en boucle serait silencieusement aveugle, et c'est
# précisément l'usage que cette métrique appelle.
_RAFRAICHIR_LE_SNAPSHOT = text("SELECT pg_stat_clear_snapshot()")

_COMPTER_IDLE_IN_TRANSACTION = text(
    "SELECT count(*) FROM pg_stat_activity "
    "WHERE datname = current_database() "
    "AND state = 'idle in transaction' "
    "AND pid <> pg_backend_pid()"
)


@dataclass(frozen=True)
class MesurePool:
    connexions_utilisees: int
    capacite: int
    # `None` quand la base n'a pas su répondre (elle n'est pas PostgreSQL, ou
    # elle est justement en train de tomber). Un `None` n'est pas un zéro : il
    # ne doit jamais rassurer.
    idle_in_transaction: int | None

    @property
    def taux_occupation(self) -> float:
        if self.capacite <= 0:
            return 0.0
        return self.connexions_utilisees / self.capacite


def mesurer_le_pool(db: Session) -> MesurePool | None:
    """
    Rend `None` quand le pool ne sait pas se décrire — c'est le cas du
    `StaticPool` de la suite de tests SQLite, une connexion unique partagée
    sans plafond, où la question n'a pas de sens. Rendre `None` plutôt que des
    zéros : un zéro se lit comme « tout va bien », pas comme « non mesuré ».

    La connexion de l'appelant est comptée dans `checkedout()`, puisqu'elle
    l'est réellement. C'est voulu : la mesure dit ce que le pool vit, pas ce
    qu'il vivrait sans l'observateur.
    """
    pool = db.get_bind().pool
    if not hasattr(pool, "checkedout") or not hasattr(pool, "size"):
        return None

    return MesurePool(
        connexions_utilisees=pool.checkedout(),
        capacite=pool.size() + max(getattr(pool, "_max_overflow", 0), 0),
        idle_in_transaction=_compter_idle_in_transaction(db),
    )


def _compter_idle_in_transaction(db: Session) -> int | None:
    try:
        db.execute(_RAFRAICHIR_LE_SNAPSHOT)
        return db.execute(_COMPTER_IDLE_IN_TRANSACTION).scalar_one()
    except Exception:
        # Volontairement muet : cette mesure est greffée sur `/health`, dont
        # le diagnostic de base est déjà fait juste avant. Elle ne doit jamais
        # être la raison pour laquelle la sonde échoue.
        db.rollback()
        return None


def journaliser_si_sature(mesure: MesurePool | None) -> bool:
    """
    Émet `pool.sature` en WARNING au-delà du seuil, et rend `True` quand elle
    l'a fait — pour qu'un test puisse vérifier le déclenchement sans lire les
    logs.
    """
    if mesure is None or mesure.taux_occupation < SEUIL_ALERTE_POOL:
        return False

    log_event(
        logger, "pool.sature",
        level=logging.WARNING,
        connexions_utilisees=mesure.connexions_utilisees,
        capacite=mesure.capacite,
        taux_occupation=round(mesure.taux_occupation, 3),
        idle_in_transaction=mesure.idle_in_transaction,
        seuil=SEUIL_ALERTE_POOL,
    )
    return True
