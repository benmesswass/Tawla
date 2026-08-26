import enum

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StaffRole(str, enum.Enum):
    WAITER = "waiter"
    MANAGER = "manager"
    KITCHEN = "kitchen"


class Staff(Base):
    __tablename__ = "staff"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    role: Mapped[StaffRole] = mapped_column(Enum(StaffRole), default=StaffRole.WAITER)
    email: Mapped[str] = mapped_column(String(180), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Désactivation plutôt que suppression : un compte supprimé emporterait
    # l'historique des commandes qu'il a prises en charge (Order.taken_by_staff_id
    # -> stats par serveur). Un serveur qui quitte l'établissement est donc
    # désactivé, et son historique reste intact.
    # Vérifié dans get_current_staff, pas seulement au login : sinon un JWT
    # déjà émis resterait valide jusqu'à 12h après le départ du salarié.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Abonnement Web Push du navigateur de CE membre du personnel (JSON brut
    # du PushSubscription, opt-in explicite depuis l'écran serveur) — même
    # forme que Order.push_subscription, mais lié à la personne plutôt qu'à
    # une commande : sert à alerter même écran éteint/onglet en arrière-plan
    # pour une nouvelle commande à prendre en charge ou un appel serveur
    # (demande de Wassim, 2026-08-26 — voir staff/service.py::notify_restaurant_staff).
    push_subscription: Mapped[str | None] = mapped_column(String(2000), nullable=True)
