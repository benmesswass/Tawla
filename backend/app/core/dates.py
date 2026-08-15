from datetime import datetime, timedelta, timezone

# La Tunisie n'applique plus l'heure d'été depuis 2009 : un décalage fixe est
# exact toute l'année, et évite de dépendre de la base de fuseaux du système,
# absente de certaines images conteneur minimales.
TUNIS = timezone(timedelta(hours=1))

# Heure à laquelle une journée de service laisse la place à la suivante.
#
# 5 h du matin est une proposition, pas une vérité — à confronter au premier
# pilote, exactement comme `ABANDONED_PENDING_AFTER` (orders/service.py) :
# assez tard pour ne jamais couper un service de nuit en cours, assez tôt pour
# qu'un écran serveur ouvert au service de midi ne traîne plus les oubliés de
# la veille. C'est le défaut que le plan de salle a rendu visible : des tables
# restaient rouges le lendemain, avec « +1 h ».
SERVICE_DAY_START_HOUR = 5


def service_day_start(now: datetime | None = None) -> datetime:
    """
    Début, en UTC, de la journée de service en cours.

    Sert à cesser d'**afficher** les commandes de la veille sur les écrans de
    service — jamais à changer leur statut : elles restent « perdues » pour
    `stats/service.py::_lost_orders`, et c'est ce chiffre qui porte l'argument
    de vente. On arrête de les montrer, on ne les efface pas.
    """
    local = (now or datetime.now(timezone.utc)).astimezone(TUNIS)
    start = local.replace(hour=SERVICE_DAY_START_HOUR, minute=0, second=0, microsecond=0)
    if local < start:
        start -= timedelta(days=1)
    return start.astimezone(timezone.utc)


def as_utc(value: datetime) -> datetime:
    """
    SQLite rend les datetime sans fuseau (Postgres les rend avec) : sans cette
    normalisation, toute comparaison à un seuil calculé en UTC lève un
    TypeError sur la base de test et passerait inaperçue jusqu'en production.
    """
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
