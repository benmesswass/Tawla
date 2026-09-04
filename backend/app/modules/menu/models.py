from sqlalchemy import Boolean, Column, ForeignKey, Integer, LargeBinary, Numeric, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# Association pure (aucune donnée propre à la ligne) : un article porte 0..N
# régimes du vocabulaire de son restaurant. `ondelete="CASCADE"` des deux
# côtés — la leçon du bulk-delete sur MenuItemOptionGroup (voir menu/options.py) :
# une suppression brute de MenuRegime ou de MenuItem doit être nettoyée par
# Postgres lui-même, jamais supposée passer par un cascade ORM qu'une requête
# de remplacement en bloc pourrait contourner.
menu_item_regimes = Table(
    "menu_item_regimes",
    Base.metadata,
    Column("menu_item_id", ForeignKey("menu_items.id", ondelete="CASCADE"), primary_key=True),
    Column("regime_id", ForeignKey("menu_regimes.id", ondelete="CASCADE"), primary_key=True),
)


class MenuSuggestion(Base):
    """
    « Avec ce plat » : jusqu'à trois articles proposés au client au moment où il
    ajoute un plat à son panier.

    C'est la seule fonctionnalité du produit qui produit un chiffre défendable
    en rendez-vous commercial (« +X % de panier moyen »), et donc la seule qui
    justifie un prix au-dessus de celui des concurrents (revue du 2026-08-13).

    Table de liaison plutôt qu'un champ texte : la suggestion doit rester un
    vrai article commandable en un geste, avec son prix et sa disponibilité à
    jour. Un texte libre obligerait le client à retourner chercher le plat dans
    la carte, ce qui annule l'intérêt.
    """

    __tablename__ = "menu_suggestions"
    __table_args__ = (
        UniqueConstraint("menu_item_id", "suggested_item_id", name="uq_menu_suggestion_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Porté aussi par la liaison, comme partout ailleurs : les requêtes de
    # lecture n'ont ainsi jamais besoin de remonter aux deux articles pour
    # vérifier qu'ils appartiennent bien au même établissement.
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), nullable=False, index=True)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"), nullable=False, index=True)
    suggested_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"), nullable=False)


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str] = mapped_column(String(60), default="Autre")
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    # Adresse de la photo affichée au client. Soit une URL externe saisie à la
    # main, soit le chemin de la photo déposée par le manager et servie par
    # `GET /api/v1/menu-items/{id}/image`.
    image_url: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # La photo elle-même, en base et non sur le disque du conteneur : chez
    # Railway comme chez Render le système de fichiers est éphémère, et toutes
    # les photos de la carte disparaîtraient au premier redéploiement — c'est
    # à dire un soir, en plein service, sans que personne comprenne pourquoi.
    #
    # Le volume reste dérisoire : une carte de quarante plats redimensionnés
    # par le navigateur avant envoi pèse quelques mégaoctets, sauvegardés avec
    # le reste. Le jour où une chaîne aura mille cartes, ce sera le moment de
    # passer à un stockage objet — pas avant (YAGNI).
    image_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    image_content_type: Mapped[str | None] = mapped_column(String(60), nullable=True)

    # 0 = pas épicé, 1-3 = léger/moyen/fort. Texte libre pour les allergènes
    # (comme `category`, saisi par le resto — pas de liste fermée qui
    # obligerait une migration à chaque nouvel allergène courant).
    spice_level: Mapped[int] = mapped_column(Integer, default=0)
    allergens: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # Par défaut à True : la quasi-totalité des restos tunisiens sont
    # halal — le champ sert surtout à signaler l'exception (établissement
    # touristique servant alcool/porc), pas la norme.
    is_halal: Mapped[bool] = mapped_column(Boolean, default=True)

    # Catégorie de taux de TVA (France, MARCHE_FRANCE.md F5/A4) — une CLÉ de
    # `Market.vat_rates` ("sur_place", "a_emporter", "alcool"), jamais le taux
    # lui-même : un taux en dur ici survivrait faux à tout changement légal, et
    # dupliquerait une donnée qui n'a qu'un seul endroit où vivre
    # (core/markets.py — « plus jamais de taux en dur », CLAUDE.md). Null =
    # "sur_place", le cas par défaut (voir core/invoice.py) — la quasi-totalité
    # de la carte, seule l'alcool s'en écarte en pratique aujourd'hui (Tawla
    # n'a qu'un parcours de commande, jamais de vente à emporter à distinguer).
    # Sans effet sur un marché sans TVA (Tunisie, `vat_rates=None`).
    vat_category: Mapped[str | None] = mapped_column(String(20), nullable=True)

    option_groups: Mapped[list["MenuItemOptionGroup"]] = relationship(
        back_populates="menu_item", cascade="all, delete-orphan", order_by="MenuItemOptionGroup.display_order"
    )
    # Régimes cochés pour cet article (« Halal », « Végétarien »...), choisis
    # parmi le vocabulaire du restaurant — voir MenuRegime. Coexiste avec
    # `is_halal` ci-dessus plutôt que de le remplacer : la Tunisie s'en sert
    # tel quel (case à cocher unique, réglage par défaut), ce vocabulaire
    # libre est la demande de Wassim pour le marché français, où « halal »
    # n'est qu'un régime parmi d'autres et pas la norme par défaut.
    regimes: Mapped[list["MenuRegime"]] = relationship(
        secondary=menu_item_regimes, order_by="MenuRegime.display_order"
    )


class MenuRegime(Base):
    """
    Vocabulaire de régimes alimentaires **propre à chaque restaurant** (pas une
    liste fermée) : le manager crée « Halal », « Végétarien », « Vegan », ou
    tout autre régime de son choix (« Sans porc », « Casher »...), puis coche
    ceux qui s'appliquent à chaque article. Demande de Wassim (2026-08-26) —
    remplace l'idée d'une liste figée de marqueurs (§A6 de MARCHE_FRANCE.md) :
    « halal » n'est pas central hors de Tunisie, la liste doit rester ouverte.
    """

    __tablename__ = "menu_regimes"
    __table_args__ = (UniqueConstraint("restaurant_id", "name", name="uq_menu_regime_restaurant_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0)


class MenuItemOptionGroup(Base):
    """
    Un groupe de choix sur un article (« Cuisson », « Sauce », « Accompagnement »)
    — France, phase F5/A2 : « un steak sans cuisson ne part pas en cuisine ».

    `min_select`/`max_select` couvrent les trois formes courantes sans avoir
    besoin d'un champ `is_required` séparé (redondant) : obligatoire à choix
    unique (1, 1), optionnel à choix unique (0, 1), optionnel à choix multiple
    borné (0, N).
    """

    __tablename__ = "menu_item_option_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Porté aussi par le groupe, comme `MenuSuggestion.restaurant_id` : les
    # routes manager n'ont ainsi jamais besoin de remonter à l'article pour
    # vérifier l'appartenance au bon restaurant.
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), nullable=False, index=True)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    min_select: Mapped[int] = mapped_column(Integer, default=0)
    max_select: Mapped[int] = mapped_column(Integer, default=1)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    menu_item: Mapped["MenuItem"] = relationship(back_populates="option_groups")
    options: Mapped[list["MenuItemOption"]] = relationship(
        back_populates="group", cascade="all, delete-orphan", order_by="MenuItemOption.display_order"
    )


class MenuItemOption(Base):
    """Un choix à l'intérieur d'un groupe (« À point », « Sans oignons »),
    avec son propre supplément de prix éventuel (« Frites +2 DT »)."""

    __tablename__ = "menu_item_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("menu_item_option_groups.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    price_delta: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    group: Mapped["MenuItemOptionGroup"] = relationship(back_populates="options")
