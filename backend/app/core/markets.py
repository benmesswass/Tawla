"""
Configuration par marché (`MARKET=tn|fr`) — France, roadmap MARCHE_FRANCE.md
§4. Un seul point d'entrée pour tout ce qui dépend du pays : devise, fuseau,
langues. Miroir de `frontend/lib/market.ts`.

Un seul marché actif par déploiement (`Settings.market`, jamais par requête) —
architecture retenue dans MARCHE_FRANCE.md §4 : un dépôt, une couche marché,
deux déploiements séparés, jamais une instance commune (résidence RGPD, panne
d'un marché qui n'affecte pas l'autre).

Plus jamais de "DT"/TND, de fuseau ou de devise en dur ailleurs — voir
CLAUDE.md.
"""
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from app.core.config import settings


@dataclass(frozen=True)
class Currency:
    code: str  # ISO 4217, ex: "TND", "EUR"
    symbol: str  # affiché au client, ex: "DT", "€"
    # Précision réelle de la devise : 3 pour le TND (millimes), 2 pour l'EUR
    # (centimes) — jamais supposée à 2 partout, c'est ce qui avait rendu
    # core/invoice.py incohérent avec le reste du produit (facture PDF en
    # `.2f` pendant que le reste de l'app affichait 3 décimales).
    decimals: int
    symbol_before: bool = False


@dataclass(frozen=True)
class Market:
    code: str  # "tn" | "fr"
    label: str
    currency: Currency
    timezone: ZoneInfo
    # Langues du parcours client, dans l'ordre d'affichage du sélecteur.
    languages: tuple[str, ...]


MARKETS: dict[str, Market] = {
    "tn": Market(
        code="tn",
        label="Tunisie",
        currency=Currency(code="TND", symbol="DT", decimals=3),
        # La Tunisie n'applique plus l'heure d'été depuis 2009 : Africa/Tunis
        # reste à UTC+1 toute l'année, exactement le comportement de l'ancien
        # décalage fixe `TUNIS = timezone(timedelta(hours=1))` (core/dates.py)
        # qu'il remplace.
        timezone=ZoneInfo("Africa/Tunis"),
        languages=("fr", "ar"),
    ),
    "fr": Market(
        code="fr",
        label="France",
        currency=Currency(code="EUR", symbol="€", decimals=2),
        # Contrairement à la Tunisie, la France applique l'heure d'été : un
        # décalage fixe serait faux 7 mois par an (voir MARCHE_FRANCE.md §3.3).
        timezone=ZoneInfo("Europe/Paris"),
        languages=("fr", "en"),
    ),
}

DEFAULT_MARKET_CODE = "tn"


def current_market() -> Market:
    """
    Le marché de CE déploiement, lu depuis `Settings.market` (variable
    d'environnement `MARKET`) — jamais depuis une requête. Absente ou
    inconnue → Tunisie, pour ne jamais casser un déploiement existant qui n'a
    pas encore posé la variable.
    """
    return MARKETS.get(settings.market, MARKETS[DEFAULT_MARKET_CODE])


def format_amount(
    amount: float, *, market: Market | None = None, decimals: int | None = None, use_iso_code: bool = False
) -> str:
    """
    Formatage canonique d'un montant pour l'affichage serveur (e-mails,
    logs) — pendant de `lib/market.ts::formatAmount` côté frontend.

    `decimals` ne sert qu'aux affichages qui ont leur propre convention
    indépendante de la devise (ex : un prix de palier d'abonnement toujours
    montré en entier) — sinon la précision réelle de la devise du marché
    s'applique.

    `use_iso_code=True` remplace le symbole ("€") par le code ISO 4217
    ("EUR") — **obligatoire** pour `core/invoice.py` : les polices core de
    fpdf2 (Helvetica, en Latin-1 strict) n'ont pas le glyphe "€" et lèvent
    `FPDFUnicodeEncodingException` à la génération (vérifié). Le code ISO est
    aussi la convention normale d'un document comptable formel.
    """
    m = market or current_market()
    value = f"{amount:.{decimals if decimals is not None else m.currency.decimals}f}"
    unit = m.currency.code if use_iso_code else m.currency.symbol
    return f"{unit} {value}" if m.currency.symbol_before else f"{value} {unit}"
