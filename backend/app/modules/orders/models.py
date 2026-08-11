import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OrderStatus(str, enum.Enum):
    """
    États explicites du flux décrit : client commande -> serveur confirme
    avec la table -> validation -> cuisine. Chaque transition est tracée
    (utile pour litiges + analytics), pas juste un booléen "validé".
    """
    PENDING_CONFIRMATION = "pending_confirmation"  # envoyée par le client, en attente du serveur
    CONFIRMED = "confirmed"                        # serveur a confirmé avec la table
    SENT_TO_KITCHEN = "sent_to_kitchen"             # visible sur l'écran cuisine
    IN_PREPARATION = "in_preparation"
    READY = "ready"
    SERVED = "served"
    CANCELLED = "cancelled"


class PaymentMethod(str, enum.Enum):
    CARD = "card"
    CASH = "cash"


class PaymentStatus(str, enum.Enum):
    UNPAID = "unpaid"
    PENDING = "pending"  # cash : demandé par le client, en attente que le serveur encaisse
    PAID = "paid"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), nullable=False, index=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("tables.id"), nullable=False, index=True)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING_CONFIRMATION)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_to_kitchen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    served_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Pré-commande mode Ramadan : le client commande avant l'iftar, ce qui
    # permet à la cuisine de voir le volume à venir à l'avance ("anticipation
    # du pic de charge"). Null = commande normale, à traiter dès que possible.
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Prise en charge (« claim ») par un serveur depuis le pool partagé —
    # base des stats "commandes par serveur/jour" (dashboard manager).
    taken_by_staff_id: Mapped[int | None] = mapped_column(ForeignKey("staff.id"), nullable=True)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Paiement — couvre le prix total de la commande (pas juste des frais de
    # service). Mode simulé pour l'instant (pas de clé Konnect réelle tant
    # qu'un vrai pilote resto n'existe pas) : `payment_ref` reste vide mais
    # est déjà là pour accueillir la référence Konnect le jour où l'intégration
    # réelle est branchée, sans nouvelle migration.
    payment_method: Mapped[PaymentMethod | None] = mapped_column(Enum(PaymentMethod), nullable=True)
    payment_status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.UNPAID)
    tip_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    payment_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Carte de fidélité — facultatif, saisi par le client à la commande. Le
    # compteur ne bouge qu'au paiement confirmé (voir orders/service.py),
    # jamais à la création : une commande annulée ne doit rien faire gagner.
    loyalty_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Abonnement Web Push du navigateur qui suit CETTE commande (JSON brut
    # du PushSubscription, opt-in côté client) — pas une identité
    # persistante, juste "ce téléphone-ci veut être notifié pour cette
    # commande-ci". Utilisé pour prévenir le client quand elle passe "prête"
    # même s'il a quitté l'onglet (voir orders/service.py::transition_status).
    push_subscription: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    taken_by: Mapped["Staff | None"] = relationship()

    @property
    def taken_by_staff_name(self) -> str | None:
        return self.taken_by.name if self.taken_by else None

    @property
    def total_amount(self) -> float:
        return sum(float(i.unit_price) * i.quantity for i in self.items)


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"), nullable=False)
    # On fige le nom/prix au moment de la commande : si le resto change le
    # prix du menu après coup, ça ne doit JAMAIS modifier une commande passée.
    menu_item_name: Mapped[str] = mapped_column(String(120), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # Plat pensé pour toute la table (entrées communes type salade, mechouia...) —
    # affiché à la cuisine/au serveur, et pré-rempli comme "partagé" dans le
    # calculateur de split bill (Phase 4) plutôt que d'attribuer la ligne à
    # une personne. N'implique aucun panier synchronisé multi-appareils :
    # une seule personne compose et valide toujours la commande.
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)

    order: Mapped["Order"] = relationship(back_populates="items")
