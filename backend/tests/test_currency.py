"""Formateur monétaire unique (France, MARCHE_FRANCE.md phase F3 étape 2)."""
import re
from pathlib import Path

from app.core.currency import format_money
from app.core.markets import FRANCE, TUNISIA


def test_tunisia_uses_three_decimals_and_a_period():
    assert format_money(22.0, TUNISIA) == "22.000 DT"
    assert format_money(6.5, TUNISIA) == "6.500 DT"


def test_france_uses_two_decimals_and_a_comma():
    assert format_money(1234.5, FRANCE) == "1234,50 €"
    assert format_money(25.0, FRANCE) == "25,00 €"


def test_defaults_to_the_current_market():
    """Sans argument, format_money lit current_market — ici la Tunisie, seul
    marché chargé par défaut (MARKET non posé)."""
    assert format_money(22.0) == format_money(22.0, TUNISIA)


_SYMBOL_AFTER_PLACEHOLDER = re.compile(r"\{[^{}\n]*\}[^\S\n]*(DT|€)\b")


def test_no_hardcoded_currency_symbol_in_backend_fstrings():
    """
    En construisant ce formateur (F3 étape 2), `orders/service.py::
    _send_payment_confirmation` interpolait encore `f"({total:.2f} DT)"`
    dans l'e-mail de confirmation de paiement — deux décimales et un
    symbole en dur, jamais adaptés au marché. Corrigé en passant par
    `format_money()`. Scanne `app/` (hors `core/currency.py`, seule source
    légitime du symbole) pour qu'un montant interpolé suivi d'un "DT"/"€"
    en dur ne revienne pas sans repasser par le formateur partagé.
    """
    app_dir = Path(__file__).resolve().parent.parent / "app"
    currency_py = app_dir / "core" / "currency.py"

    offenders = []
    for path in sorted(app_dir.rglob("*.py")):
        if path == currency_py:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if _SYMBOL_AFTER_PLACEHOLDER.search(line):
                offenders.append(f"{path.relative_to(app_dir.parent)}:{lineno}: {line.strip()}")

    assert not offenders, (
        "Montant interpolé suivi d'un symbole DT/€ en dur — passer par format_money() "
        "(app/core/currency.py) :\n  " + "\n  ".join(offenders)
    )


def test_no_hardcoded_currency_formatting_in_frontend():
    """
    Miroir côté frontend (lib/currency.ts) du garde-fou ci-dessus. La même
    campagne F3 étape 2 a trouvé des `.toFixed(2)`/`.toFixed(3)` et des
    `{prix} DT` en dur, éparpillés sur une vingtaine de fichiers (paliers
    d'abonnement, tickets cuisine, CSV export, carte de partage...).
    Scanne `app/`, `components/` et `lib/` (hors `lib/currency.ts`) pour
    qu'ils ne reviennent pas un par un au fil des prochaines fonctionnalités.
    """
    frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
    currency_ts = frontend_dir / "lib" / "currency.ts"
    to_fixed_2_or_3 = re.compile(r"\.toFixed\(\s*[23]\s*\)")

    offenders = []
    for sous_dossier in ("app", "components", "lib"):
        for path in sorted((frontend_dir / sous_dossier).rglob("*.ts")) + sorted(
            (frontend_dir / sous_dossier).rglob("*.tsx")
        ):
            if path == currency_ts:
                continue
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if to_fixed_2_or_3.search(line) or _SYMBOL_AFTER_PLACEHOLDER.search(line):
                    offenders.append(f"{path.relative_to(frontend_dir.parent)}:{lineno}: {line.strip()}")

    assert not offenders, (
        "Décimales ou symbole monétaire en dur — passer par formatAmount()/formatMoney() "
        "(frontend/lib/currency.ts) :\n  " + "\n  ".join(offenders)
    )


def test_rounds_to_the_market_decimals():
    assert format_money(22.0004, TUNISIA) == "22.000 DT"
    assert format_money(22.0009, TUNISIA) == "22.001 DT"
