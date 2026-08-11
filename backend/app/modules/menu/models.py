from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


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
