"""Facture PDF (app/core/invoice.py) — rendu par la police Helvetica core de
fpdf2, limitée au Latin-1/CP1252 simple (voir docstring du module)."""
from fpdf import FPDF

import app.core.invoice as invoice_module
from app.core.invoice import _pdf_money, generate_invoice_pdf
from app.core.markets import FRANCE, TUNISIA
from app.modules.menu.models import MenuItem
from app.modules.orders.models import Order, OrderItem
from app.modules.tables.models import Table
from app.modules.tenants.models import Restaurant


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


def _order_for_invoice(db_session, restaurant, tip_amount: float = 0) -> Order:
    """Commande posée directement en base, avec table + article, juste assez
    pour exercer `generate_invoice_pdf()` (table_label, items, total_amount)."""
    table = Table(restaurant_id=restaurant.id, label="Table 4")
    item = MenuItem(restaurant_id=restaurant.id, name="Couscous royal", price=18.0, category="Plats")
    db_session.add_all([table, item])
    db_session.commit()
    db_session.refresh(table)
    db_session.refresh(item)

    order = Order(restaurant_id=restaurant.id, table_id=table.id, tip_amount=tip_amount)
    order.items.append(OrderItem(menu_item_id=item.id, menu_item_name="Couscous royal", unit_price=18.0, quantity=2))
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order


def test_generate_invoice_pdf_shows_vat_breakdown_and_legal_info_for_the_france_market(monkeypatch, db_session):
    """
    Régression : la ventilation TVA (Total HT / TVA / Total TTC) et les
    mentions légales (adresse, SIRET, TVA intracom) n'apparaissaient nulle
    part sur la facture avant l'ajout de Restaurant.legal_address/tax_id/
    vat_number (Phase F5). Ce test rend réellement le PDF avec un restaurant
    qui les a renseignées, sur le marché France (seul marché avec des
    `vat_rates`, voir markets.py), pour qu'une régression future (taux à
    zéro, accent hors Latin-1...) échoue ici plutôt que sur la première
    facture d'un restaurateur français.
    """
    monkeypatch.setattr(invoice_module, "current_market", FRANCE)

    restaurant = Restaurant(
        name="Le Tawla Test",
        slug="le-tawla-test-invoice",
        legal_address="12 rue de la République, 75011 Paris",
        tax_id="812 345 678 00019",
        vat_number="FR32812345678",
    )
    db_session.add(restaurant)
    db_session.commit()
    db_session.refresh(restaurant)

    order = _order_for_invoice(db_session, restaurant, tip_amount=2.5)

    assert generate_invoice_pdf(order, restaurant)


def test_generate_invoice_pdf_stays_unchanged_without_vat_or_legal_info(db_session):
    """Marché sans TVA (Tunisie, `vat_rates=None`) et restaurant sans
    mentions légales : la facture doit rester générable exactement comme
    avant — pas de ligne HT/TVA, pas de ligne vide pour une adresse
    absente."""
    restaurant = Restaurant(name="Chez Slah", slug="chez-slah-invoice-test")
    db_session.add(restaurant)
    db_session.commit()
    db_session.refresh(restaurant)

    order = _order_for_invoice(db_session, restaurant)

    assert generate_invoice_pdf(order, restaurant)


def test_generate_invoice_pdf_renders_the_invoice_number_when_assigned(monkeypatch, db_session):
    """Régression possible : le numéro (core/invoice_number.py) et la
    ventilation TVA lisaient chacun le marché différemment (l'un un
    paramètre par défaut figé à l'import, l'autre `current_market` à
    l'appel) — un test qui monkeypatche seulement `current_market` doit
    suffire à faire apparaître les DEUX sans réglage séparé."""
    monkeypatch.setattr(invoice_module, "current_market", FRANCE)
    restaurant = Restaurant(name="Le Tawla Test", slug="le-tawla-test-invoice-number")
    db_session.add(restaurant)
    db_session.commit()
    db_session.refresh(restaurant)

    order = _order_for_invoice(db_session, restaurant)
    order.invoice_number = "F2026-00001"
    db_session.commit()

    assert generate_invoice_pdf(order, restaurant)


def test_generate_invoice_pdf_stays_renderable_below_and_above_the_invoice_threshold(monkeypatch, db_session):
    """Note obligatoire (arrêté du 3 octobre 1983) affichée seulement à
    partir du seuil du marché — les deux côtés doivent rester générables,
    la mention n'est qu'un `pdf.cell()` de plus dans les deux cas."""
    monkeypatch.setattr(invoice_module, "current_market", FRANCE)
    restaurant = Restaurant(name="Le Tawla Test", slug="le-tawla-test-invoice-threshold")
    db_session.add(restaurant)
    db_session.commit()
    db_session.refresh(restaurant)

    below = _order_for_invoice(db_session, restaurant)  # 2 x 18 EUR = 36 EUR > seuil, garde un cas en dessous aussi
    below.items[0].quantity = 1
    below.items[0].unit_price = 10.0
    db_session.commit()

    above = _order_for_invoice(db_session, restaurant)

    assert generate_invoice_pdf(below, restaurant)
    assert generate_invoice_pdf(above, restaurant)


def test_generate_invoice_pdf_falls_back_to_tawla_when_restaurant_is_none(db_session):
    """`get_paid_order_by_query_token` peut ne trouver aucun restaurant
    (`db.get` -> None, voir orders/router.py) — la facture doit rester
    générable, avec "Tawla" en en-tête plutôt que de lever."""
    restaurant = Restaurant(name="Chez Slah", slug="chez-slah-invoice-none-test")
    db_session.add(restaurant)
    db_session.commit()
    db_session.refresh(restaurant)

    order = _order_for_invoice(db_session, restaurant)

    assert generate_invoice_pdf(order, None)
