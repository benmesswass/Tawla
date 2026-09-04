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

from app.core.currency import format_money
from app.core.markets import Market, current_market
from app.modules.orders.models import Order, PaymentMethod
from app.modules.tenants.models import Restaurant

_PAYMENT_LABELS: dict[PaymentMethod, str] = {
    PaymentMethod.CARD: "Carte (en ligne)",
    PaymentMethod.CARD_TERMINAL: "Carte (terminal)",
    PaymentMethod.CASH: "Espèces",
}


def _pdf_money(amount: float, market: Market = current_market) -> str:
    """`format_money()` rend "€" pour le marché France — la police Helvetica
    core de fpdf2 ne le sait pas afficher (`FPDFUnicodeEncodingException`,
    vérifié : même l'espace insécable seul passe, seul "€" casse) et lèverait
    sur CHAQUE facture France, pas seulement sur un cas rare comme le nom de
    plat arabe évoqué plus haut. Repli ASCII "EUR" pour ce rendu PDF
    uniquement — l'écran et l'e-mail gardent le vrai symbole. Paramètre
    `market` explicite (comme `format_money`) pour rester testable sans
    dépendre du marché du processus — voir tests/test_invoice.py."""
    return format_money(amount, market).replace("€", "EUR")


def _dashed_divider(pdf: FPDF) -> None:
    """Séparateur pointillé pleine largeur (inspiré du reçu Tabesto, retour
    utilisateur 2026-09-03) — casse la facture en sections claires au lieu
    d'un mur de lignes chiffrées difficile à scanner d'un coup d'œil.
    `dashed_line()` est dépréciée depuis fpdf2 2.4.6 au profit de
    `set_dash_pattern()` + `line()`, remis à zéro juste après (motif à trait
    plein partout ailleurs dans la facture)."""
    y = pdf.get_y() + 2
    pdf.set_dash_pattern(dash=1.5, gap=1.5)
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.set_dash_pattern()
    pdf.set_y(y + 4)


def _vat_rate_for(order_item, market: Market) -> float:
    """
    Taux applicable à cette ligne — `market.vat_rates` indexé par
    `order_item.vat_category` (copié depuis `MenuItem.vat_category` à la
    commande, voir orders/service.py). Null ou clé inconnue (article créé
    avant l'existence du champ, ou vocabulaire du marché qui aurait changé) :
    repli sur "sur_place", le taux par défaut de la carte — jamais une
    exception qui ferait échouer la génération de toute la facture pour une
    seule ligne mal classée.

    Limitation connue : les suppléments (`order_item.options`, ex. un verre
    de vin ajouté à un plat) n'ont pas leur propre `vat_category` — leur
    prix est plié dans `unit_price` et ventilé au taux de l'article parent.
    Un supplément dont le taux réel diffère (alcool à 20 % ajouté à un plat
    "sur_place" à 10 %) est donc ventilé au taux du plat, pas au sien. Coûteux
    à corriger (colonne + migration par option, service.py, ce module) pour
    un cas rare tant qu'aucun pilote France ne vend de suppléments alcool.
    """
    rates = market.vat_rates or {}
    return rates.get(order_item.vat_category or "sur_place", rates.get("sur_place", 0.0))


_SOCIAL_LINKS: list[tuple[str, str]] = [
    ("facebook_url", "Facebook"),
    ("instagram_url", "Instagram"),
    ("tiktok_url", "TikTok"),
    ("whatsapp_url", "WhatsApp"),
]


def _add_social_links(pdf: FPDF, restaurant: Restaurant | None) -> None:
    """Liens réseaux sociaux du restaurant (mêmes champs que l'en-tête du menu
    client, `Restaurant.facebook_url`/etc.) — en texte cliquable plutôt qu'en
    icônes : Helvetica core (fpdf2) ne sait dessiner aucune icône de marque,
    seul du texte Latin-1 (voir docstring du module)."""
    if not restaurant:
        return
    links = [(label, getattr(restaurant, field)) for field, label in _SOCIAL_LINKS if getattr(restaurant, field)]
    if not links:
        return

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(90, 90, 90)
    gap = 8
    widths = [pdf.get_string_width(label) for label, _ in links]
    x = (pdf.w - (sum(widths) + gap * (len(links) - 1))) / 2
    y = pdf.get_y()
    for (label, url), width in zip(links, widths):
        pdf.set_xy(x, y)
        pdf.cell(width, 6, label, link=url)
        x += width + gap
    pdf.ln(8)


def generate_invoice_pdf(order: Order, restaurant: Restaurant | None) -> bytes:
    # Marché résolu UNE FOIS, à l'appel, puis passé à chaque `_pdf_money()` :
    # son paramètre `market` a une valeur par défaut figée à l'import du
    # module, alors que la ventilation TVA plus bas lit `current_market` à
    # l'appel — les deux pouvaient donc décrire deux marchés différents dans
    # le MÊME document (montants en dinars sous un bloc de TVA française).
    market = current_market

    pdf = FPDF(format="A4")
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, restaurant.name if restaurant else "Tawla", new_x="LMARGIN", new_y="NEXT")

    # Mentions légales (adresse, SIRET/matricule fiscal, TVA intracom) —
    # facultatives, saisies par le manager dans son dashboard (Restaurant.
    # legal_address/tax_id/vat_number). Absentes tant qu'il ne les a pas
    # renseignées : la facture reste comme avant, jamais de ligne vide.
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(90, 90, 90)
    if restaurant and restaurant.legal_address:
        pdf.cell(0, 5, restaurant.legal_address, new_x="LMARGIN", new_y="NEXT")
    ids = [v for v in [restaurant.tax_id if restaurant else None, restaurant.vat_number if restaurant else None] if v]
    if ids:
        pdf.cell(0, 5, "  ·  ".join(ids), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90, 90, 90)
    # Numéro de facture (séquence continue par restaurant, voir
    # core/invoice_number.py) quand le marché l'exige — jamais `order.id`,
    # qui n'est pas une numérotation continue par émetteur. Absent sur un
    # marché sans obligation de note : l'en-tête reste celui d'avant.
    if order.invoice_number:
        pdf.cell(0, 6, f"Facture n° {order.invoice_number}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, f"{order.table_label}, commande #{order.id}", new_x="LMARGIN", new_y="NEXT")
    else:
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
        pdf.cell(35, 8, _pdf_money(float(item.unit_price), market), align="R")
        pdf.cell(35, 8, _pdf_money(line_total, market), align="R", new_x="LMARGIN", new_y="NEXT")
        # Options choisies (France, F5/A2) : déjà comptées dans unit_price,
        # affichées ici pour mémoire, jamais reprises dans le calcul du total.
        if item.options:
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(110, 110, 110)
            noms = ", ".join(o.option_name for o in item.options)
            pdf.cell(0, 5, f"   {noms}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(0, 0, 0)

    pdf.ln(4)
    _dashed_divider(pdf)
    tip = float(order.tip_amount)
    subtotal = order.total_amount

    # Ventilation TVA — uniquement pour un marché qui en gère une (France,
    # voir markets.py), PAR TAUX RÉELLEMENT PRÉSENT dans la commande (F5/A4) :
    # un article classé "alcool" (20 %) ne peut plus être ventilé au même
    # taux qu'un plat "sur_place" (10 %) ou "à emporter" (5,5 %) — voir
    # `_vat_rate_for`. Le prix affiché au client est déjà TTC (convention
    # française d'affichage), donc le HT se déduit du TTC de CHAQUE LIGNE,
    # jamais du sous-total global comme avant A4. Affichée APRÈS le total,
    # comme un détail complémentaire (mise en page inspirée du reçu Tabesto,
    # retour utilisateur 2026-09-03) plutôt qu'avant : ce n'est pas ce qu'un
    # client vérifie en premier.
    has_vat = bool(market.vat_rates)
    ttc_by_rate: dict[float, float] = {}
    if has_vat:
        for item in order.items:
            rate = _vat_rate_for(item, market)
            ttc_by_rate[rate] = ttc_by_rate.get(rate, 0.0) + float(item.unit_price) * item.quantity

    pdf.set_font("Helvetica", "", 10)
    if not has_vat:
        pdf.cell(145, 7, "Sous-total", align="R")
        pdf.cell(35, 7, _pdf_money(subtotal, market), align="R", new_x="LMARGIN", new_y="NEXT")
    if tip > 0:
        pdf.cell(145, 7, "Pourboire", align="R")
        pdf.cell(35, 7, _pdf_money(tip, market), align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Total mis en avant : un seul montant, centré et agrandi — c'est le
    # seul chiffre qu'un client vérifie systématiquement, il ne doit jamais
    # se confondre visuellement avec les lignes de détail (retour
    # utilisateur 2026-09-03 : la ligne "Total payé" alignée à droite passait
    # inaperçue, contrairement au "TOTAL" centré/agrandi d'un reçu Tabesto).
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_fill_color(235, 235, 235)
    pdf.cell(0, 14, f"TOTAL  {_pdf_money(subtotal + tip, market)}", align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    if ttc_by_rate:
        _dashed_divider(pdf)

        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Taxe détaillée", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(40, 7, "Taux")
        pdf.cell(45, 7, "HT", align="R")
        pdf.cell(45, 7, "TVA", align="R")
        pdf.cell(45, 7, "TTC", align="R", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 10)
        total_ht = 0.0
        total_vat_amount = 0.0
        # Le taux le plus élevé (alcool) en tête — c'est celui qu'un contrôle
        # fiscal vérifie en premier. Ordre déterministe : la clé (le taux
        # lui-même) trie sans ambiguïté, jamais l'ordre d'insertion.
        for rate in sorted(ttc_by_rate, reverse=True):
            ttc = ttc_by_rate[rate]
            ht = ttc / (1 + rate)
            vat_amount = ttc - ht
            total_ht += ht
            total_vat_amount += vat_amount
            pdf.cell(40, 7, f"{rate * 100:g} %")
            pdf.cell(45, 7, _pdf_money(ht, market), align="R")
            pdf.cell(45, 7, _pdf_money(vat_amount, market), align="R")
            pdf.cell(45, 7, _pdf_money(ttc, market), align="R", new_x="LMARGIN", new_y="NEXT")

        # Ligne "Total" seulement quand plus d'un taux est en jeu : avec un
        # seul taux, elle répéterait exactement la ligne du dessus.
        if len(ttc_by_rate) > 1:
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(40, 7, "Total")
            pdf.cell(45, 7, _pdf_money(total_ht, market), align="R")
            pdf.cell(45, 7, _pdf_money(total_vat_amount, market), align="R")
            pdf.cell(45, 7, _pdf_money(subtotal, market), align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    _dashed_divider(pdf)
    pdf.set_font("Helvetica", "", 10)
    method_label = _PAYMENT_LABELS.get(order.payment_method) if order.payment_method else None
    pdf.cell(0, 6, f"Moyen de paiement : {method_label or '-'}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    if has_vat:
        pdf.cell(0, 5, "Facture conforme à l'article 289 du CGI", align="C", new_x="LMARGIN", new_y="NEXT")
    # Note obligatoire au-delà du seuil du marché (25 EUR TTC en France,
    # arrêté du 3 octobre 1983) — la mention rappelle au client que ce
    # document EST la note qu'il est en droit d'exiger, et au restaurateur
    # qu'il n'a pas à en éditer une seconde à la main. Sous le seuil, la
    # remise du document reste facultative : rien n'est affiché.
    threshold = market.invoice_threshold
    if threshold is not None and (subtotal + tip) >= threshold:
        pdf.cell(
            0, 5,
            f"Note obligatoire (prestation supérieure à {_pdf_money(threshold, market)}) - arrêté du 3 octobre 1983",
            align="C", new_x="LMARGIN", new_y="NEXT",
        )
    pdf.cell(0, 5, "Généré automatiquement par Tawla", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    _add_social_links(pdf, restaurant)

    return bytes(pdf.output())
