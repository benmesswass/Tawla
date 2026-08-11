from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Restaurant(Base):
    """
    Un resto/café client. MVP = un seul enregistrement en pratique,
    mais tout le reste du modèle référence restaurant_id dès le départ
    pour permettre d'onboarder un 2e client sans migration lourde.
    """
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Mode Ramadan — pas de calcul astronomique/API externe (zéro service
    # payant obligatoire, zéro dépendance réseau) : le manager saisit
    # lui-même l'heure du jour, comme il le ferait sur un tableau au mur.
    ramadan_mode_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    iftar_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Mode café simplifié : un établissement qui ne sert que des boissons
    # n'a pas besoin de la structure entrées/plats/desserts — le menu
    # client s'affiche alors en liste unique, sans en-têtes de catégorie.
    cafe_mode_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Retour sonore optionnel à l'arrivée d'une commande en cuisine — désactivé
    # par défaut (une cuisine bruyante peut ne pas vouloir d'un bip de plus),
    # activable par le manager depuis le dashboard.
    kitchen_sound_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
