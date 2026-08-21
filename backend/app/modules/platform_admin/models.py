from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PlatformAdmin(Base):
    """
    Compte de l'opérateur de la plateforme (Wassim) — distinct de `Staff` : un
    `Staff` est structurellement lié à un seul restaurant (`restaurant_id`
    NOT NULL), un `PlatformAdmin` ne l'est à aucun.

    Créé uniquement par `scripts/create_platform_admin.py`, jamais par une
    route d'inscription publique.
    """

    __tablename__ = "platform_admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(180), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
