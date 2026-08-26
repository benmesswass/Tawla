from datetime import date, datetime, time, timedelta, timezone
from typing import TYPE_CHECKING, Annotated

from pydantic import BeforeValidator

if TYPE_CHECKING:
    from app.core.markets import Market

# Import différé (pas en tête de fichier) : `app.core.markets` importe
# `app.modules.tenants.models`, qui importe `as_utc` d'ici — un import en
# tête de fichier romprait au démarrage de l'appli entière (`ImportError:
# cannot import name 'as_utc' from partially initialized module`), vérifié.
def _resolve_market(market: "Market | None") -> "Market":
    from app.core.markets import current_market

    return market or current_market


# Heure à laquelle une journée de service laisse la place à la suivante.
#
# 5 h du matin est une proposition, pas une vérité — à confronter au premier
# pilote, exactement comme `ABANDONED_PENDING_AFTER` (orders/service.py) :
# assez tard pour ne jamais couper un service de nuit en cours, assez tôt pour
# qu'un écran serveur ouvert au service de midi ne traîne plus les oubliés de
# la veille. C'est le défaut que le plan de salle a rendu visible : des tables
# restaient rouges le lendemain, avec « +1 h ».
SERVICE_DAY_START_HOUR = 5


def service_day_start(now: datetime | None = None, market: "Market | None" = None) -> datetime:
    """
    Début, en UTC, de la journée de service en cours, dans le fuseau du
    marché — `zoneinfo`, conscient de l'heure d'été (`market=None` lit
    `current_market` ; la Tunisie n'en observe plus depuis 2009, la France
    si, d'où `zoneinfo` plutôt qu'un décalage fixe, qui serait faux sept mois
    par an en France).

    Sert à cesser d'**afficher** les commandes de la veille sur les écrans de
    service — jamais à changer leur statut : elles restent « perdues » pour
    `stats/service.py::lost_orders`, et c'est ce chiffre qui porte l'argument
    de vente. On arrête de les montrer, on ne les efface pas.
    """
    resolved_market = _resolve_market(market)
    local = (now or datetime.now(timezone.utc)).astimezone(resolved_market.timezone)
    start = local.replace(hour=SERVICE_DAY_START_HOUR, minute=0, second=0, microsecond=0)
    if local < start:
        start -= timedelta(days=1)
    return start.astimezone(timezone.utc)


def service_day_bounds(day: date, market: "Market | None" = None) -> tuple[datetime, datetime]:
    """
    Début et fin, en UTC, de la journée de service correspondant à un jour
    calendaire donné.

    F-3 (audit de pré-lancement) : les stats (`stats/service.py`) bornaient
    leurs journées à minuit UTC, pendant que les écrans de service (Phase
    19.5) coupent à 5 h Tunis — deux définitions différentes, l'une des
    conséquences étant qu'une commande passée entre minuit et 5 h Tunis
    (l'iftar et le sohour d'une même soirée, pendant le Ramadan) apparaissait
    sous un jour dans les stats et sous un autre sur les écrans de service.

    Midi UTC comme instant de référence : reste dans le même jour calendaire
    côté marché que `day` pour n'importe quel fuseau à quelques heures de
    UTC (Tunis comme Paris, hiver comme été), donc `service_day_start` en
    déduit sans ambiguïté le début de la bonne journée de service.
    """
    resolved_market = _resolve_market(market)
    start = service_day_start(datetime.combine(day, time(hour=12), tzinfo=timezone.utc), market=resolved_market)
    return start, start + timedelta(days=1)


def _marquer_utc(value: object) -> object:
    """Attache UTC à un horodatage qui n'a pas de fuseau, sans rien décaler."""
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


# Type à utiliser pour **tout** horodatage sortant de l'API.
#
# SQLite rend les datetime sans fuseau (Postgres les rend avec). Sérialisés
# tels quels, ils arrivent au navigateur sous la forme « 2026-08-16T15:33:28 »,
# que JavaScript interprète comme une heure *locale* : sur un Mac réglé à
# UTC+1, une commande passée à l'instant s'affichait « en attente depuis
# 1 h 00 ». L'écart valait exactement le décalage horaire, et il aurait fait
# passer pour perdue chaque commande d'un vrai service.
UtcDatetime = Annotated[datetime, BeforeValidator(_marquer_utc)]


def as_utc(value: datetime) -> datetime:
    """
    SQLite rend les datetime sans fuseau (Postgres les rend avec) : sans cette
    normalisation, toute comparaison à un seuil calculé en UTC lève un
    TypeError sur la base de test et passerait inaperçue jusqu'en production.
    """
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
