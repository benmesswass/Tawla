from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, UniqueConstraint
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
    image_url: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # 0 = pas épicé, 1-3 = léger/moyen/fort. Texte libre pour les allergènes
    # (comme `category`, saisi par le resto — pas de liste fermée qui
    # obligerait une migration à chaque nouvel allergène courant).
    spice_level: Mapped[int] = mapped_column(Integer, default=0)
    allergens: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # Par défaut à True : la quasi-totalité des restos tunisiens sont
    # halal — le champ sert surtout à signaler l'exception (établissement
    # touristique servant alcool/porc), pas la norme.
    is_halal: Mapped[bool] = mapped_column(Boolean, default=True)
