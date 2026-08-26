"""Facture PDF (app/core/invoice.py) — rendu par la police Helvetica core de
fpdf2, limitée au Latin-1/CP1252 simple (voir docstring du module)."""
from fpdf import FPDF

from app.core.invoice import _pdf_money
from app.core.markets import FRANCE, TUNISIA


def test_pdf_money_falls_back_to_eur_for_the_france_market():
    assert _pdf_money(12.5, FRANCE) == "12,50 EUR"


def test_pdf_money_keeps_the_tunisian_symbol_unchanged():
    assert _pdf_money(12.5, TUNISIA) == "12.500 DT"


def test_pdf_money_stays_renderable_by_the_core_helvetica_font():
    """
    Régression : en branchant `format_money()` dans la facture PDF (F3 étape
    2), le marché France faisait lever `FPDFUnicodeEncodingException` sur
    CHAQUE facture — la police Helvetica core de fpdf2 ne sait pas afficher
    "€" (vérifié : l'espace insécable seul passe, seul "€" casse). Route
    HTTP concernée : `GET /orders/{id}/invoice` (`orders/router.py`),
    ouverte sans filet directement dans le navigateur du client, pas
    seulement dans l'envoi d'e-mail "best-effort". `_pdf_money()` corrige en
    repliant sur "EUR" pour ce rendu — ce test rend réellement la chaîne à
    travers fpdf2 pour qu'une régression future (nouveau symbole, nouveau
    marché) échoue ici plutôt que sur la première facture d'un restaurateur.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "", 10)
    for market in (TUNISIA, FRANCE):
        pdf.cell(35, 8, _pdf_money(12.5, market), align="R")

    assert bytes(pdf.output())
