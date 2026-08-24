"""
Facture PDF envoyée par email au client qui a laissé son adresse au moment de
payer (`Order.customer_email`), quel que soit le moyen de paiement — carte en
ligne, carte physique ou espèces (confirmations de paiement, 2026-08-19).

Générée à la volée depuis les données déjà en base, jamais stockée sur
disque : rien ne justifie de garder un fichier par commande pour un document
reconstructible en une fraction de seconde.

Police Helvetica core (latin-1) : couvre les accents français, mais pas les
tirets cadratins ni l'arabe — texte volontairement en ASCII étendu simple.
"""
from fpdf import FPDF

from app.core.markets import format_amount
from app.modules.orders.models import Order, PaymentMethod

_PAYMENT_LABELS: dict[PaymentMethod, str] = {
    PaymentMethod.CARD: "Carte (en ligne)",
    PaymentMethod.CARD_TERMINAL: "Carte (terminal)",
    PaymentMethod.CASH: "Espèces",
}


def generate_invoice_pdf(order: Order, restaurant_name: str) -> bytes:
    pdf = FPDF(format="A4")
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, restaurant_name, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 6, f"Facture, {order.table_label}, commande #{order.id}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, order.created_at.strftime("Le %d/%m/%Y à %H:%M"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(90, 8, "Article", border="B")
    pdf.cell(20, 8, "Qté", border="B", align="R")
    pdf.cell(35, 8, "Prix unit.", border="B", align="R")
    pdf.cell(35, 8, "Total", border="B", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    for item in order.items:
        line_total = float(item.unit_price) * item.quantity
        pdf.cell(90, 8, item.menu_item_name)
        pdf.cell(20, 8, str(item.quantity), align="R")
        pdf.cell(35, 8, format_amount(float(item.unit_price), use_iso_code=True), align="R")
        pdf.cell(35, 8, format_amount(line_total, use_iso_code=True), align="R", new_x="LMARGIN", new_y="NEXT")
        if item.selected_options:
            # F5-A2 : sans cette ligne, le prix unitaire (qui inclut déjà les
            # suppléments) paraît incohérent avec le prix affiché sur le menu.
            options_text = ", ".join(opt.choice_name for opt in item.selected_options)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(120, 120, 120)
            pdf.cell(180, 5, f"   {options_text}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", "", 10)

    pdf.ln(4)
    tip = float(order.tip_amount)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(145, 7, "Sous-total", align="R")
    pdf.cell(35, 7, format_amount(order.total_amount, use_iso_code=True), align="R", new_x="LMARGIN", new_y="NEXT")
    if tip > 0:
        pdf.cell(145, 7, "Pourboire", align="R")
        pdf.cell(35, 7, format_amount(tip, use_iso_code=True), align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(145, 9, "Total payé", align="R")
    pdf.cell(
        35, 9, format_amount(order.total_amount + tip, use_iso_code=True), align="R", new_x="LMARGIN", new_y="NEXT"
    )

    pdf.ln(6)
    pdf.set_font("Helvetica", "", 10)
    method_label = _PAYMENT_LABELS.get(order.payment_method) if order.payment_method else None
    pdf.cell(0, 6, f"Moyen de paiement : {method_label or '-'}", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.ln(10)
    pdf.cell(0, 5, "Généré automatiquement par Tawla, tawla.tn", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
