"""
Couche marché (F3, MARCHE_FRANCE.md §4) — configuration par marché,
formateur monétaire.

Le comportement par défaut (MARKET non posé dans l'environnement de test, donc
"tn") doit rester identique à ce que le produit faisait avant l'existence de
ce module : c'est ce que ces tests protègent en premier.
"""
from app.core.config import settings
from app.core.markets import MARKETS, current_market, format_amount


def test_tunisie_est_le_marche_par_defaut():
    assert current_market().code == "tn"
    assert current_market().currency.code == "TND"
    assert current_market().currency.decimals == 3


def test_market_inconnue_retombe_sur_la_tunisie(monkeypatch):
    monkeypatch.setattr(settings, "market", "xx")
    assert current_market().code == "tn"


def test_bascule_vers_la_france(monkeypatch):
    monkeypatch.setattr(settings, "market", "fr")
    market = current_market()
    assert market.code == "fr"
    assert market.currency.code == "EUR"
    assert market.currency.decimals == 2
    assert market.languages == ("fr", "en")


def test_format_amount_tunisie_par_defaut():
    assert format_amount(12.5) == "12.500 DT"


def test_format_amount_france(monkeypatch):
    monkeypatch.setattr(settings, "market", "fr")
    assert format_amount(12.5) == "12.50 €"


def test_format_amount_decimals_override_sert_aux_prix_de_palier():
    """Un prix de palier d'abonnement s'affiche toujours en entier,
    indépendamment de la précision réelle de la devise (`decimals=3` pour le
    TND) — voir frontend/lib/market.ts::formatAmount, même paramètre."""
    assert format_amount(50, decimals=0) == "50 DT"


def test_format_amount_use_iso_code_pour_les_factures_pdf():
    """`core/invoice.py` DOIT passer par ce mode : les polices core de fpdf2
    n'ont pas le glyphe "€" et lèvent une exception à la génération — vérifié
    manuellement (FPDFUnicodeEncodingException)."""
    assert format_amount(12.5, use_iso_code=True) == "12.500 TND"
    settings.market = "fr"
    try:
        assert format_amount(12.5, use_iso_code=True) == "12.50 EUR"
    finally:
        settings.market = "tn"


def test_les_deux_marches_ont_exactement_deux_langues():
    """`useLocale` (frontend) suppose exactement deux langues par marché — un
    simple bouton de bascule, pas un sélecteur. Si ça cesse d'être vrai un
    jour, c'est ce test qui doit le dire en premier."""
    for market in MARKETS.values():
        assert len(market.languages) == 2
        assert "fr" in market.languages
