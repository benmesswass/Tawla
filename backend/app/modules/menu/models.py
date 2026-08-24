from sqlalchemy import Boolean, ForeignKey, Integer, LargeBinary, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


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
    # Par défaut à True EN TUNISIE (Settings.market) : la quasi-totalité des
    # restos tunisiens sont halal — le champ sert surtout à signaler
    # l'exception (établissement touristique servant alcool/porc), pas la
    # norme. Le défaut s'inverse en France (voir schemas.py, csv_import.py) :
    # la colonne elle-même n'a pas de défaut fixe, jamais market-dépendant au
    # niveau SQL (voir MARCHE_FRANCE.md F5-A6).
    is_halal: Mapped[bool] = mapped_column(Boolean, default=True)

    # F5-A6 (MARCHE_FRANCE.md) — allergènes des 14 catégories INCO
    # (règlement UE 1169/2011), obligatoires en France : codes séparés par une
    # virgule (ex. "gluten,oeufs,lait"), liste fermée côté client
    # (`frontend/lib/allergens.ts`) mais colonne libre côté base — même
    # convention que `category`, jamais de migration pour un nouvel allergène
    # si la réglementation change. Distinct du texte libre `allergens`
    # ci-dessus, conservé tel quel pour tout ce que la liste fermée ne couvre
    # pas ("cuisiné dans une friture commune aux fruits à coque"…).
    allergen_codes: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Marqueurs positifs, distincts du halal (qui exclut) — une carte
    # française en a besoin au même titre que les allergènes (MARCHE_FRANCE.md
    # §3.2). Faux par défaut dans les deux marchés : une affirmation "sans
    # gluten" ou "vegan" engage le restaurant, elle ne se déduit jamais.
    is_vegetarian: Mapped[bool] = mapped_column(Boolean, default=False)
    is_vegan: Mapped[bool] = mapped_column(Boolean, default=False)
    is_gluten_free: Mapped[bool] = mapped_column(Boolean, default=False)
