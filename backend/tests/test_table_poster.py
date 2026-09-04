"""
Affiche QR téléchargeable en PDF pour les tables ajoutées en self-service —
gabarit « 2c » du handoff de design du 2026-08-20, voir
`app/modules/tables/poster.py`.

Contrairement à `test_qr_card.py`, on ne vérifie pas le noir et blanc strict :
cette affiche porte volontairement la couleur de marque, seul le QR lui-même
doit rester lisible. On vérifie donc qu'un PDF valide sort, que la logique de
répartition du libellé de table (disque à deux étages vs libellé entier) est
correcte, et que la mise en page ne casse pas sur les cas limites.
"""
from datetime import datetime, timezone
from unittest.mock import patch

from app.modules.tables.poster import _digit_font_size, _split_table_label, generate_table_poster_pdf


def _poster(**overrides) -> bytes:
    kwargs = {
        "menu_url": "https://tawla.tn/menu/abc123",
        "table_label": "Table 5",
        "restaurant_name": "Chez Slah",
    }
    kwargs.update(overrides)
    return generate_table_poster_pdf(**kwargs)


def test_poster_is_a_valid_pdf():
    pdf_bytes = _poster()
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000


def test_zone_is_not_repeated_when_the_label_already_says_it():
    # Comparaison octet à octet de deux PDF générés séparément : fpdf2 capture
    # `datetime.now()` à la construction pour /CreationDate (et l'/ID en
    # dérive), donc geler l'horloge évite un faux négatif si les deux appels
    # tombent de part et d'autre d'une frontière de seconde.
    with patch("fpdf.fpdf.datetime") as frozen_datetime:
        frozen_datetime.now.return_value = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with_zone = _poster(table_label="Terrasse 1", zone="Terrasse")
        without_zone = _poster(table_label="Terrasse 1")
    assert with_zone == without_zone


def test_zone_is_shown_when_it_adds_information():
    plain = _poster(table_label="Table 5")
    with_zone = _poster(table_label="Table 5", zone="Terrasse")
    assert plain != with_zone


def test_long_names_and_labels_do_not_overflow_or_crash():
    """Un nom d'établissement ou un libellé de table à rallonge doit être
    tronqué/replié, pas faire planter la génération."""
    pdf_bytes = _poster(
        restaurant_name="Restaurant Chez Slah Spécialités Tunisiennes et Grillades du Port",
        table_label="Table du fond près de la fenêtre côté mer",
    )
    assert pdf_bytes.startswith(b"%PDF-")


def test_split_table_label_extracts_the_trailing_number():
    assert _split_table_label("Table 7") == ("Table", "7")


def test_split_table_label_extracts_the_zone_as_eyebrow():
    assert _split_table_label("Terrasse 12") == ("Terrasse", "12")


def test_split_table_label_never_invents_a_number():
    """« Comptoir » n'a pas de chiffre : pas de disque à deux étages, et on
    n'invente jamais un numéro de table."""
    assert _split_table_label("Comptoir") == (None, "Comptoir")


def test_split_table_label_finds_the_last_digit_group():
    assert _split_table_label("Table 7 VIP 2")[1] == "2"


def test_digit_font_size_shrinks_at_three_digits():
    assert _digit_font_size("12") == 55.5
    assert _digit_font_size("123") == 40


def test_poster_without_a_number_in_the_label_still_generates():
    """« Comptoir » : pas de disque à deux étages, pas de ligne arabe
    « طاولة {numéro} » puisqu'il n'y a pas de numéro — juste le libellé
    entier dans le disque."""
    pdf_bytes = _poster(table_label="Comptoir")
    assert pdf_bytes.startswith(b"%PDF-")
    assert pdf_bytes != _poster(table_label="Table 7")


def test_three_digit_table_number_does_not_crash():
    pdf_bytes = _poster(table_label="Table 123")
    assert pdf_bytes.startswith(b"%PDF-")
