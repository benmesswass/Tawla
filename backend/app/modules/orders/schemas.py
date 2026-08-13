from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.orders.models import OrderStatus, PaymentMethod, PaymentStatus


class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int = 1
    notes: str | None = None
    is_shared: bool = False
    # Ajouté depuis une suggestion « avec ce plat » plutôt que depuis la carte.
    # Déclaratif côté client : ça ne sert qu'à mesurer l'effet de la vente
    # incitative, jamais à autoriser ou tarifer quoi que ce soit — un client qui
    # mentirait sur ce drapeau ne fausserait qu'une statistique de son propre
    # restaurant.
    from_suggestion: bool = False


class OrderCreate(BaseModel):
    # Le client prouve qu'il a scanné le QR de cette table : ni `table_id` ni
    # `restaurant_id` ne sont acceptés, ils sont déduits du token. Sans ça,
    # deviner deux entiers suffisait à injecter une commande dans un service
    # en cours (constat 3 de la revue du 2026-08-13) — de la nourriture
    # réellement préparée pour une table qui n'a rien demandé.
    qr_token: str
    items: list[OrderItemCreate]
    # Pré-commande mode Ramadan : optionnel, réglé côté client sur l'heure
    # d'iftar du resto quand il choisit "commander pour l'iftar".
    scheduled_for: datetime | None = None
    # Carte de fidélité — facultatif, le client peut commander sans jamais
    # le renseigner.
    loyalty_phone: str | None = None


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    menu_item_id: int
    menu_item_name: str
    unit_price: float
    quantity: int
    notes: str | None
    is_shared: bool
    from_suggestion: bool


class PayCardRequest(BaseModel):
    tip_amount: float = Field(default=0, ge=0)


class PushSubscriptionIn(BaseModel):
    endpoint: str
    keys: dict[str, str]


class OrderOut(BaseModel):
    """
    Vue **client** d'une commande : ce que renvoie le suivi lu depuis le
    téléphone. Ne porte aucune donnée personnelle — `loyalty_phone` en a été
    retiré en Phase 12.2 (constat 1 de la revue : un numéro de téléphone est
    une donnée personnelle au sens de la loi 2004-63, il n'a rien à faire dans
    une réponse lisible par un navigateur).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    restaurant_id: int
    table_id: int
    status: OrderStatus
    created_at: datetime
    confirmed_at: datetime | None
    sent_to_kitchen_at: datetime | None
    ready_at: datetime | None
    served_at: datetime | None
    taken_by_staff_id: int | None
    taken_by_staff_name: str | None
    scheduled_for: datetime | None
    payment_method: PaymentMethod | None
    payment_status: PaymentStatus
    tip_amount: float
    total_amount: float
    items: list[OrderItemOut]


class OrderCreatedOut(OrderOut):
    """
    Réponse de création uniquement : le `public_token` n'apparaît nulle part
    ailleurs. Le navigateur le garde et le renvoie ensuite en en-tête
    `X-Order-Token` pour suivre ou payer sa commande.
    """

    public_token: str


class OrderOutStaff(OrderOut):
    """
    Vue **staff** : ajoute le numéro de fidélité, dont le serveur a besoin
    pour vérifier une récompense annoncée par le client. Servie uniquement aux
    routes protégées par JWT.
    """

    loyalty_phone: str | None
