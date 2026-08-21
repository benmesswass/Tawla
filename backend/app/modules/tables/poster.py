"""
Affiche QR d'une table, téléchargeable en PDF depuis le dashboard pour être
imprimée et collée en salle — pour les restaurants inscrits en self-service
via /signup, qui n'ont pas droit au chevalet noir et blanc que
`setup_restaurant.py` génère à l'installation (`qr_card.py`).

Mise en page « 2c », issue du handoff de design du 2026-08-20 (disque plein
pour le numéro de table, lisible de loin par un serveur ; QR et consigne pour
le client). Gabarit A5 portrait, cotes en millimètres, fidèles au handoff.

Contrairement à `qr_card.py` (noir sur blanc strict, pensé pour l'impression
de masse d'un pilote au photocopieur du coin), cette affiche porte la couleur
de marque : c'est le seul support physique que Tawla pose elle-même dans la
salle d'un client qui ne nous a jamais parlé. Le QR lui-même reste noir pur
sur blanc — seule zone où le contraste maximal compte pour la lecture par un
téléphone d'entrée de gamme.

Bilingue FR/AR : le texte arabe est façonné (lettres liées, RTL) via fpdf2 +
uharfbuzz — jamais de rendu non façonné, qui serait pire que pas d'arabe du
tout (même principe que la garde de `qr_card.py` sur l'absence d'arabe, qui
elle n'a pas cette dépendance et reste volontairement français seul).
"""
import re
from pathlib import Path

import qrcode
from fpdf import FPDF
from qrcode.constants import ERROR_CORRECT_Q

_HARISSA = (214, 64, 30)
_SEMOULE = (246, 239, 221)
_ENCRE = (42, 27, 18)
_ESPRESSO = (36, 24, 17)
_INK_SOFT = (107, 89, 71)
_LAITON = (184, 134, 46)
_LINE = (227, 215, 189)
_WHITE = (255, 255, 255)

_FONTS_DIR = Path(__file__).parent / "fonts"

_PAGE_W = 148.0
_PAGE_H = 210.0
_MARGIN_X = 11.6

_PT_TO_MM = 0.352778

_LAST_DIGIT_GROUP = re.compile(r"(\d+)(?!.*\d)")


def _blend(fg: tuple[int, int, int], bg: tuple[int, int, int], alpha: float) -> tuple[int, int, int]:
    """Mélange à plat `fg` à `alpha` sur `bg`, tous deux opaques — équivalent
    exact d'une vraie transparence quand le fond est un aplat uni, sans avoir
    besoin de l'API de calques de fpdf2 pour un simple filet décoratif."""
    return tuple(round(alpha * f + (1 - alpha) * b) for f, b in zip(fg, bg))


def _split_table_label(label: str) -> tuple[str | None, str]:
    """
    « Table 7 » -> (« Table », « 7 ») ; « Terrasse 12 » -> (« Terrasse », « 12 »).
    « Comptoir » (aucun chiffre) -> (None, « Comptoir ») : pas de disque à deux
    étages, le libellé entier se dessine dans le disque à la place.
    """
    match = _LAST_DIGIT_GROUP.search(label)
    if not match:
        return None, label.strip()
    digits = match.group(1)
    rest = re.sub(r"\s+", " ", label[: match.start()] + label[match.end() :]).strip()
    return (rest or "Table"), digits


def _digit_font_size(digits: str) -> float:
    """Trois chiffres ou plus ne tiennent pas dans le disque à 55,5 pt."""
    return 40 if len(digits) >= 3 else 55.5


def _fonts(pdf: FPDF) -> None:
    pdf.add_font("Lalezar", "", _FONTS_DIR / "Lalezar-Regular.ttf")
    pdf.add_font("Hanken", "", _FONTS_DIR / "HankenGrotesk-Regular.ttf")
    pdf.add_font("Hanken", "B", _FONTS_DIR / "HankenGrotesk-SemiBold.ttf")
    pdf.add_font("Kufi", "", _FONTS_DIR / "NotoKufiArabic-Regular.ttf")


def _latin(pdf: FPDF) -> None:
    pdf.set_text_shaping(False)


def _arabic(pdf: FPDF) -> None:
    pdf.set_text_shaping(True, direction="rtl", script="Arab", language="ar")


def _left(pdf: FPDF, x: float, y: float, text: str, font: str, size: float, *, style="", color=_ESPRESSO) -> None:
    pdf.set_font(font, style, size)
    pdf.set_text_color(*color)
    pdf.set_xy(x, y)
    pdf.cell(text=text)


def _right(pdf: FPDF, right_x: float, y: float, text: str, font: str, size: float, *, style="", color=_ESPRESSO) -> None:
    pdf.set_font(font, style, size)
    pdf.set_text_color(*color)
    width = pdf.get_string_width(text)
    pdf.set_xy(right_x - width, y)
    pdf.cell(text=text)


def _centered_in(
    pdf: FPDF, x: float, w: float, y: float, text: str, font: str, size: float, *, style="", color=_ESPRESSO
) -> None:
    pdf.set_font(font, style, size)
    pdf.set_text_color(*color)
    pdf.set_xy(x, y)
    pdf.cell(w, None, text, align="C")


def _draw_tawla_mark(pdf: FPDF, x: float, y: float, size: float) -> None:
    """Reproduit `frontend/components/brand/TawlaMark.tsx` (viewBox 100x100)
    à l'échelle, en primitives fpdf — variante « sur fond clair » (harissa
    plein, trait crème), seule utilisée dans 2c."""
    s = size / 100
    pdf.set_fill_color(*_HARISSA)
    pdf.rect(x + 10 * s, y + 28 * s, 80 * s, 44 * s, style="F", round_corners=True, corner_radius=8 * s)
    pdf.set_draw_color(*_SEMOULE)  # --semoule, trait clair du pictogramme sur fond harissa
    pdf.set_line_width(4 * s)
    pdf.line(x + 62 * s, y + 28 * s, x + 62 * s, y + 72 * s)
    pdf.set_line_width(7 * s)
    pdf.polyline([(x + 68 * s, y + 50 * s), (x + 74 * s, y + 56 * s), (x + 86 * s, y + 40 * s)])


def generate_table_poster_pdf(*, menu_url: str, table_label: str, restaurant_name: str, zone: str | None = None) -> bytes:
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_Q, box_size=10, border=2)
    qr.add_data(menu_url)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    pdf = FPDF(format="A5")
    pdf.set_auto_page_break(False)
    pdf.add_page()
    _fonts(pdf)

    # 1 — Fond de page.
    pdf.set_fill_color(*_SEMOULE)
    pdf.rect(0, 0, _PAGE_W, _PAGE_H, style="F")

    # 2 — Halo laiton, décoratif, coupé par le bord (aplat pré-mélangé à 12 %
    # sur semoule : le fond sous le halo est uni, donc le mélange à plat donne
    # un résultat identique à une vraie transparence, sans l'API de calques).
    pdf.set_fill_color(*_blend(_LAITON, _SEMOULE, 0.12))
    pdf.ellipse(161 - 58, 219 - 58, 116, 116, style="F")

    # 3-5 — En-tête : nom de l'établissement, pictogramme, mot « tawla ».
    name = restaurant_name.strip()[:34]
    name_size = 18 if len(name) > 22 else 22.5
    _left(pdf, _MARGIN_X, 13.3, name, "Lalezar", name_size, color=_ENCRE)
    _draw_tawla_mark(pdf, 105.4, 10.6, 13.8)
    _left(pdf, 121.3, 12.5, "tawla", "Lalezar", 18, color=_ENCRE)

    # 6-8 — Disque du numéro de table.
    disc_x, disc_y, disc_d = _MARGIN_X, 30.7, 34.9
    pdf.set_fill_color(*_HARISSA)
    pdf.ellipse(disc_x, disc_y, disc_d, disc_d, style="F")

    eyebrow, big = _split_table_label(table_label)
    if eyebrow is None:
        # Pas de chiffre dans le libellé (« Comptoir ») : pas de disque à deux
        # étages, ni de sur-titre — le libellé entier, sur deux lignes max.
        pdf.set_font("Lalezar", "", 22)
        pdf.set_text_color(*_WHITE)
        # Tient sur une ligne quand ça rentre (cas courant : « Comptoir »,
        # « Bar », « Accueil »...) ; sinon on retombe sur les deux lignes
        # maximum du gabarit, quitte à ce qu'un mot unique très long casse
        # au milieu — au-delà, ce n'est plus un libellé de table réaliste.
        one_line_w = pdf.get_string_width(big) + 2 * pdf.c_margin
        if one_line_w <= disc_d - 2:
            pdf.set_xy(disc_x, disc_y + 13)
            pdf.cell(disc_d, None, big, align="C")
        else:
            box_w = disc_d - 3
            pdf.set_xy(disc_x + (disc_d - box_w) / 2, disc_y + 8)
            pdf.multi_cell(box_w, 22 * _PT_TO_MM * 1.1, big, align="C")
    else:
        surtitre_size = 8.3
        char_spacing = 0.18 * surtitre_size * _PT_TO_MM
        pdf.set_char_spacing(char_spacing)
        _centered_in(
            pdf,
            disc_x,
            disc_d,
            37.4,
            eyebrow.upper(),
            "Hanken",
            surtitre_size,
            color=_blend(_WHITE, _HARISSA, 0.8),
        )
        pdf.set_char_spacing(0)
        _centered_in(pdf, disc_x, disc_d, 41.3, big, "Lalezar", _digit_font_size(big), color=_WHITE)

    # 9-11 — Colonne de droite : numéro en arabe, zone, note serveur.
    # Item 9 suppose un numéro (« طاولة {numéro} ») — sans chiffre dans le
    # libellé (« Comptoir »), il n'y a rien de vrai à écrire là : on ne
    # force pas le nom dans le gabarit arabe, même règle que « ne jamais
    # inventer un numéro ».
    right_x = 51.9
    if eyebrow is not None:
        _arabic(pdf)
        _left(pdf, right_x, 33.4, f"طاولة {big}", "Kufi", 15, color=_ENCRE)
        _latin(pdf)

    if zone and zone.strip().lower() not in table_label.lower():
        _left(pdf, right_x, 44.6, zone.strip()[:28], "Hanken", 11.3, color=_INK_SOFT)

    pdf.set_font("Hanken", "", 9.8)
    pdf.set_text_color(*_INK_SOFT)
    pdf.set_xy(right_x, 52.9)
    pdf.multi_cell(58.2, 9.8 * _PT_TO_MM * 1.45, "Donnez ce numéro au serveur si vous l'appelez.", align="L")

    # 12-13 — Carte blanche et image du QR (noir pur sur blanc — inchangé).
    pdf.set_fill_color(*_WHITE)
    pdf.rect(33.2, 71.4, 81.5, 81.5, style="F", round_corners=True, corner_radius=6.9)
    pdf.image(qr_image, x=38.5, y=76.7, w=70.9, h=70.9)

    # 14-15 — Consigne FR/AR, bloc ancré par le bas : la copie FR tient sur
    # deux lignes dans cette police/largeur, pas une — la position de la
    # ligne arabe part donc du bas réel du bloc FR (get_y() après le
    # multi_cell), jamais du 170,4 mm de la maquette, qui suppose une seule
    # ligne. Sans ça, les deux lignes se chevauchent (constaté au rendu).
    pdf.set_font("Lalezar", "", 21)
    pdf.set_text_color(*_ENCRE)
    pdf.set_xy(_MARGIN_X, 158.2)
    pdf.multi_cell(124.8, 21 * _PT_TO_MM * 1.15, "Scannez, commandez depuis votre table", align="L")

    _arabic(pdf)
    _left(pdf, _MARGIN_X, pdf.get_y() + 3, "امسح الرمز واطلب من طاولتك", "Kufi", 12, color=_INK_SOFT)
    _latin(pdf)

    # 16-18 — Filet et pied de page.
    pdf.set_fill_color(*_LINE)
    pdf.rect(_MARGIN_X, 193.9, 124.8, 0.3, style="F")
    _left(pdf, _MARGIN_X, 197.1, "Un serveur passe confirmer la commande.", "Hanken", 9, color=_INK_SOFT)
    _right(pdf, _PAGE_W - _MARGIN_X, 197.1, "Propulsé par Tawla · tawla.tn", "Hanken", 9, color=_INK_SOFT)

    return bytes(pdf.output())
