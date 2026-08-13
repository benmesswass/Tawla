"""
Chevalet de table à imprimer (Phase 13.2).

Le décodage réel du QR (photo de biais, faible luminosité, tache sur le motif) a
été vérifié séparément avec un lecteur OpenCV — 5 conditions sur 5, détail dans
la description de la PR. OpenCV n'est pas ajouté aux dépendances du projet pour
autant : ces tests couvrent ce qui peut casser en éditant le code, c'est-à-dire
la mise en page et la règle de rappel de zone.
"""
from app.modules.tables.qr_card import CARD_HEIGHT, CARD_WIDTH, build_table_card, save_table_card


def _card(**overrides):
    kwargs = {
        "menu_url": "https://tawla.tn/menu/abc123",
        "table_label": "Table 5",
        "restaurant_name": "Chez Slah",
    }
    kwargs.update(overrides)
    return build_table_card(**kwargs)


def test_card_has_the_print_format():
    card = _card()
    assert card.size == (CARD_WIDTH, CARD_HEIGHT)
    assert card.mode == "RGB"


def test_card_is_black_on_white():
    """Contraste maximal et impression noir et blanc : un pilote imprime au
    photocopieur du coin."""
    colors = {color for _count, color in _card().getcolors(maxcolors=100000)}
    for red, green, blue in colors:
        assert red == green == blue, f"couleur non neutre trouvée : {(red, green, blue)}"


def test_zone_is_not_repeated_when_the_label_already_says_it():
    """« Terrasse 1 » suivi de « Terrasse » n'apporte rien. Les tables générées
    en série par setup_restaurant.py sont toutes dans ce cas."""
    with_zone = _card(table_label="Terrasse 1", zone="Terrasse")
    without_zone = _card(table_label="Terrasse 1")
    assert with_zone.tobytes() == without_zone.tobytes()


def test_zone_is_shown_when_it_adds_information():
    plain = _card(table_label="Table 5")
    with_zone = _card(table_label="Table 5", zone="Terrasse")
    assert plain.tobytes() != with_zone.tobytes()


def test_long_names_do_not_overflow_the_card():
    """Un nom d'établissement à rallonge doit être tronqué, pas déborder."""
    card = _card(
        restaurant_name="Restaurant Chez Slah Spécialités Tunisiennes et Grillades du Port",
        table_label="Table du fond près de la fenêtre côté mer",
    )
    assert card.size == (CARD_WIDTH, CARD_HEIGHT)


def test_save_creates_parent_directories(tmp_path):
    target = tmp_path / "qr-chez-slah" / "table-5.png"
    assert save_table_card(target, menu_url="https://tawla.tn/menu/x", table_label="Table 5",
                           restaurant_name="Chez Slah") == target
    assert target.exists() and target.stat().st_size > 1000
