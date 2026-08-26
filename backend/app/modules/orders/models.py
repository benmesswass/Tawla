import enum
import secrets
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def generate_order_token() -> str:
    """
    Preuve que ce navigateur-ci est bien celui qui a passé cette commande-ci.

    Même raison d'être que `Table.qr_token` : l'id d'une commande est
    séquentiel, donc devinable. Sans ce token, `GET /orders/3` laissait lire
    la commande du voisin — et celle d'un autre restaurant — numéro de
    téléphone du client compris (constat 1 de la revue du 2026-08-13).
    Le parcours client reste sans compte : ce token ne remplace pas une
    authentification, il rattache juste chaque appel à une commande réelle.
    """
    return secrets.token_urlsafe(32)


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
    CARD = "card"  # en ligne (Konnect ou démo) — le client paie depuis son téléphone
    # Carte physique, terminal apporté par un serveur — même mécanique que CASH
    # (demande -> encaissement confirmé par un serveur), distincte pour que les
    # stats de moyen de paiement ne mélangent pas espèces et carte en salle.
    CARD_TERMINAL = "card_terminal"
    CASH = "cash"


class PaymentStatus(str, enum.Enum):
    UNPAID = "unpaid"
    PENDING = "pending"  # cash/carte physique : en attente que le serveur encaisse
    PAID = "paid"


class Order(Base):
    __tablename__ = "orders"
    # Unicité portée par la table, pas globale : l'identifiant est fabriqué par
    # le navigateur du client, donc rien ne garantit sa forme. Global, un
    # client envoyant `client_order_id: "1"` récupérerait la commande — et le
    # `public_token` — d'un inconnu qui aurait envoyé la même valeur ailleurs.
    # Ramené à la table, le pire cas se limite à des convives déjà attablés
    # ensemble, qui partagent de toute façon le `qr_token`.
    __table_args__ = (UniqueConstraint("table_id", "client_order_id", name="uq_orders_table_client_order"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), nullable=False, index=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("tables.id"), nullable=False, index=True)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING_CONFIRMATION)

    # Renvoyé une seule fois, à la création, et exigé ensuite sur toutes les
    # routes client de cette commande (suivi, paiement, abonnement push).
    public_token: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=generate_order_token
    )

    # Identifiant du panier, fabriqué par le navigateur au moment où le client
    # compose sa commande, et conservé tel quel dans la charge utile mise en
    # file hors ligne. C'est ce qui rend la création idempotente : une réponse
    # perdue en plein service, puis rejouée, retombe sur la même commande au
    # lieu d'en créer une seconde — et de faire préparer deux fois le plat.
    # Nullable : un navigateur resté sur une version antérieure de la page
    # continue de commander, sans le filet.
    client_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_to_kitchen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Moment où la cuisine s'est saisie du plat. Sans lui, l'écran cuisine ne
    # pouvait afficher qu'un temps depuis l'envoi : une commande prise en main
    # tout de suite et une autre oubliée dix minutes s'y ressemblaient.
    preparation_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    # Saisi par le client au moment de payer (facultatif, quel que soit le
    # moyen) — sert UNIQUEMENT à envoyer la confirmation + facture PDF une
    # fois payée (voir orders/service.py::_send_payment_confirmation).
    # Jamais demandé à la commande : un client qui ne veut pas la laisser doit
    # pouvoir commander et payer sans, comme aujourd'hui.
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

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
    table: Mapped["Table"] = relationship()

    @property
    def taken_by_staff_name(self) -> str | None:
        return self.taken_by.name if self.taken_by else None

    @property
    def table_label(self) -> str:
        """
        Le nom que le restaurant a donné à la table, et que le client voit sur
        son téléphone. Les écrans serveur et cuisine affichaient `table_id` :
        les deux coïncident tant que les tables s'appellent « Table 1, 2, 3… »
        et ont été créées dans cet ordre, donc jamais dans un vrai
        établissement. Le plat partait à la mauvaise table.
        """
        return self.table.label

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

    # Entre quels convives le plat est partagé, en numéros de place séparés par
    # une virgule (« 1,2 »). Vide = partagé par toute la table, ce qui reste le
    # cas courant. Saisi par le client au moment de composer son panier : sans
    # ça, le calculateur d'addition repartait de zéro et lui redemandait ce
    # qu'il venait de dire (retour du premier service).
    #
    # Une chaîne plutôt qu'une table de liaison : la donnée ne sert qu'à
    # pré-remplir un calcul indicatif, jamais à une requête ni à une jointure.
    shared_with: Mapped[str | None] = mapped_column(String(60), nullable=True)

    # Ligne ajoutée depuis une suggestion « avec ce plat » plutôt que depuis la
    # carte. Sans ce drapeau, l'effet de la vente incitative est invérifiable :
    # on ne saurait dire si un panier plus élevé vient des suggestions ou d'une
    # table plus nombreuse. C'est ce qui transforme la fonctionnalité en
    # argument chiffré (Phase 14.1).
    from_suggestion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")
    options: Mapped[list["OrderItemOption"]] = relationship(back_populates="order_item", cascade="all, delete-orphan")


class OrderItemOption(Base):
    """
    Choix figé d'un groupe d'options au moment de la commande (« Cuisson : à
    point ») — France, phase F5/A2. Même principe que `menu_item_name`/
    `unit_price` sur `OrderItem` : le nom du groupe, le nom de l'option et son
    supplément de prix sont copiés ici tels quels, jamais relus depuis
    `MenuItemOptionGroup`/`MenuItemOption`, qui peuvent changer ou disparaître
    après coup sans que ça n'altère une commande déjà passée. Le supplément est
    en outre déjà comptabilisé dans `OrderItem.unit_price` — cette ligne ne sert
    qu'à l'affichage (cuisine, suivi client, facture), jamais à un recalcul.
    """

    __tablename__ = "order_item_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id"), nullable=False, index=True)
    group_name: Mapped[str] = mapped_column(String(60), nullable=False)
    option_name: Mapped[str] = mapped_column(String(60), nullable=False)
    price_delta: Mapped[float] = mapped_column(Numeric(10, 2), default=0)

    order_item: Mapped["OrderItem"] = relationship(back_populates="options")
