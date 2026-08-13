"""
Génère le chevalet de table à imprimer : le QR code entouré de ce dont un
client a besoin pour comprendre quoi faire, et de ce dont un serveur a besoin
pour savoir de quelle table il s'agit.

Un PNG de QR nu ne suffit pas sur le terrain (Phase 13.2) : personne ne sait
quelle table c'est une fois découpé, et le client ne sait pas qu'il faut le
scanner. Choix d'impression assumés :

- **Noir sur blanc uniquement.** Un pilote imprime chez lui ou au photocopieur
  du coin ; la couleur coûte cher et ne rend pas mieux. C'est aussi le contraste
  maximal, donc la meilleure lecture par un téléphone d'entrée de gamme dans une
  salle mal éclairée.
- **Correction d'erreur haute (Q, ~25 %).** Un chevalet de restaurant finit
  taché de harissa et corné. Le QR doit encore se lire avec un coin abîmé.
- **Texte en français seulement.** Pillow ne sait pas façonner l'arabe (lettres
  liées, sens droite-à-gauche) sans dépendance supplémentaire ; afficher de
  l'arabe cassé serait pire que ne rien afficher. L'application, elle, est bien
  bilingue une fois le QR scanné.
"""
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont
from qrcode.constants import ERROR_CORRECT_Q

# Format ~A6 à 240 dpi : imprimable 4 par page A4, lisible à 30 cm.
CARD_WIDTH = 1000
CARD_HEIGHT = 1400
MARGIN = 70

_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:\\Windows\\Fonts\\arialbd.ttf",
)


def _font(size: int) -> ImageFont.ImageFont:
    """
    Cherche une police système, et se rabat sur la police bitmap de Pillow si
    aucune n'existe : le script doit produire un fichier utilisable sur le poste
    de Wassim comme sur un serveur de CI, sans embarquer de fichier de police.
    """
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _centered(draw: ImageDraw.ImageDraw, y: int, text: str, font, fill="black") -> int:
    """Écrit `text` centré horizontalement et renvoie le bas du texte."""
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    draw.text(((CARD_WIDTH - (right - left)) / 2 - left, y - top), text, font=font, fill=fill)
    return y + (bottom - top)


def build_table_card(*, menu_url: str, table_label: str, restaurant_name: str, zone: str | None = None) -> Image.Image:
    card = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), "white")
    draw = ImageDraw.Draw(card)

    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_Q, box_size=10, border=2)
    qr.add_data(menu_url)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    qr_size = CARD_WIDTH - 2 * MARGIN
    qr_image = qr_image.resize((qr_size, qr_size), Image.NEAREST)

    y = MARGIN
    y = _centered(draw, y, restaurant_name[:34], _font(46))
    y += 26

    card.paste(qr_image, (MARGIN, y))
    y += qr_size + 40

    y = _centered(draw, y, table_label[:24], _font(72))
    # La zone n'est rappelée que si le libellé ne la contient pas déjà :
    # « Terrasse 1 » suivi de « Terrasse » ne dit rien de plus et alourdit le
    # chevalet. Le cas arrive systématiquement avec les tables générées en
    # série par `setup_restaurant.py`, qui préfixe par la zone.
    if zone and zone.lower() not in table_label.lower():
        y += 16
        y = _centered(draw, y, zone[:28], _font(34), fill=(90, 90, 90))

    y += 46
    y = _centered(draw, y, "Scannez pour voir le menu", _font(38))
    y += 12
    _centered(draw, y, "et commander depuis votre table", _font(38))

    # Repère de découpe : un pilote imprime 4 chevalets par page A4.
    draw.rectangle([(6, 6), (CARD_WIDTH - 7, CARD_HEIGHT - 7)], outline=(210, 210, 210), width=2)
    return card


def save_table_card(output_path: Path, **kwargs) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    build_table_card(**kwargs).save(output_path, dpi=(240, 240))
    return output_path
