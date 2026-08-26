"""
Formateur monétaire unique — France, MARCHE_FRANCE.md phase F3 étape 2.

Règle durable (à partir de maintenant, voir CLAUDE.md) : plus jamais de
symbole ("DT"/"€"), de nombre de décimales ni de séparateur décimal en dur
ailleurs dans le code. Piloté par `current_market` (app/core/markets.py) :
change de comportement seul quand `MARKET` change, sans toucher aux appelants.
"""
from app.core.markets import Market, current_market


def format_money(amount: float, market: Market = current_market) -> str:
    """« 22.000 DT » en Tunisie, « 12,50 € » en France — décimales, séparateur
    et symbole viennent tous du marché, jamais de l'appelant. Espace
    insécable avant le symbole dans les deux cas (typographie correcte,
    identique à l'œil à l'espace simple utilisé jusqu'ici)."""
    formatted = f"{amount:.{market.currency.decimals}f}"
    if market.currency.decimal_separator != ".":
        formatted = formatted.replace(".", market.currency.decimal_separator)
    return f"{formatted}\u00a0{market.currency.symbol}"
