from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field

from app.core.dates import UtcDatetime
from app.modules.orders.models import Order, OrderStatus, PaymentMethod, PaymentStatus


def _convives(value: object) -> object:
    """
    Les numéros de convives voyagent en liste côté API et sont stockés en
    « 1,2 » côté base : la conversion se fait ici, dans les deux sens, pour que
    ni le client ni le modèle n'aient à connaître l'autre format.
    """
    if value is None:
        # Colonne vide : le plat est partagé par toute la table, pas par
        # personne — d'où la liste vide plutôt qu'un `null` qui obligerait
        # chaque appelant à distinguer les deux.
        return []
    if isinstance(value, str):
        return [int(part) for part in value.split(",") if part.strip().isdigit()]
    return value


class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int = 1
    notes: str | None = None
    is_shared: bool = False
    # Numéros de places entre lesquelles le plat est partagé. Vide = toute la
    # table, ce qui reste le cas courant d'un plat « à partager ».
    shared_with: list[int] = Field(default_factory=list)
    # Ajouté depuis une suggestion « avec ce plat » plutôt que depuis la carte.
    # Déclaratif côté client : ça ne sert qu'à mesurer l'effet de la vente
    # incitative, jamais à autoriser ou tarifer quoi que ce soit — un client qui
    # mentirait sur ce drapeau ne fausserait qu'une statistique de son propre
    # restaurant.
    from_suggestion: bool = False
    # Un id par choix (« à point », « sans oignons »...) — le client n'envoie
    # que des ids, jamais un nom ni un prix : c'est le serveur qui les relit
    # depuis MenuItemOption, vérifie qu'ils appartiennent bien à cet article et
    # respectent min/max par groupe, puis fige le tout (voir orders/service.py).
    selected_option_ids: list[int] = Field(default_factory=list)


class OrderCreate(BaseModel):
    # Le client prouve qu'il a scanné le QR de cette table : ni `table_id` ni
    # `restaurant_id` ne sont acceptés, ils sont déduits du token. Sans ça,
    # deviner deux entiers suffisait à injecter une commande dans un service
    # en cours (constat 3 de la revue du 2026-08-13) — de la nourriture
    # réellement préparée pour une table qui n'a rien demandé.
    qr_token: str
    items: list[OrderItemCreate]
    # Identifiant du panier, fabriqué par le navigateur au moment où le client
    # le compose — et surtout pas régénéré au rejeu, sinon il ne servirait à
    # rien. Facultatif : sans lui, la création reste possible, sans le filet.
    client_order_id: str | None = Field(default=None, max_length=64)
    # Pré-commande mode Ramadan : optionnel, réglé côté client sur l'heure
    # d'iftar du resto quand il choisit "commander pour l'iftar".
    scheduled_for: UtcDatetime | None = None
    # Carte de fidélité — facultatif, le client peut commander sans jamais
    # le renseigner.
    loyalty_phone: str | None = None
    # Date de naissance, pour le bandeau anniversaire. Elle voyage avec la
    # commande depuis la Phase 19.1 : c'est le seul moment où le client la
    # donne pour lui-même. La route de consultation, elle, n'écrit plus rien —
    # sinon elle permettait d'attacher une date au numéro de n'importe qui.
    loyalty_birth_date: date | None = None


class OrderItemOptionOut(BaseModel):
    """Choix figé au moment de la commande (« Cuisson : à point ») — le
    supplément est indicatif, il est déjà compté dans `unit_price`."""

    model_config = ConfigDict(from_attributes=True)

    group_name: str
    option_name: str
    price_delta: float


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    menu_item_id: int
    menu_item_name: str
    unit_price: float
    quantity: int
    notes: str | None
    is_shared: bool
    shared_with: Annotated[list[int], BeforeValidator(_convives)] = Field(default_factory=list)
    from_suggestion: bool
    options: list[OrderItemOptionOut] = Field(default_factory=list)


class PayCardRequest(BaseModel):
    tip_amount: float = Field(default=0, ge=0)
    # Facultatif : sert uniquement à envoyer la confirmation + facture PDF une
    # fois payée. Jamais requis, un client qui ne le laisse pas paie pareil.
    customer_email: EmailStr | None = None


class PayCashRequest(BaseModel):
    """
    Le pourboire vaut aussi pour les espèces. Il était purement perdu : le
    client le saisissait, le serveur venait encaisser le total sans lui, et
    personne ne s'apercevait de l'écart avant de compter la caisse.
    """

    tip_amount: float = Field(default=0, ge=0)
    customer_email: EmailStr | None = None


class PayCardTerminalRequest(BaseModel):
    """
    Carte physique : le client demande, un serveur apporte le terminal —
    même mécanique que PayCashRequest, moyen de paiement distinct (voir
    PaymentMethod.CARD_TERMINAL).
    """

    tip_amount: float = Field(default=0, ge=0)
    customer_email: EmailStr | None = None


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
    # Ce que le restaurant a écrit sur la table, et ce que le client lit sur son
    # téléphone. `table_id` seul envoyait le serveur à la mauvaise table.
    table_label: str
    status: OrderStatus
    created_at: UtcDatetime
    confirmed_at: UtcDatetime | None
    sent_to_kitchen_at: UtcDatetime | None
    preparation_started_at: UtcDatetime | None
    ready_at: UtcDatetime | None
    served_at: UtcDatetime | None
    taken_by_staff_id: int | None
    taken_by_staff_name: str | None
    scheduled_for: UtcDatetime | None
    payment_method: PaymentMethod | None
    payment_status: PaymentStatus
    paid_at: UtcDatetime | None
    tip_amount: float
    total_amount: float
    items: list[OrderItemOut]
    # Posé UNIQUEMENT par la réponse de `POST /pay/card` quand le restaurant a
    # connecté son propre Konnect (modèle direct, 2026-08-19) : le client doit
    # être redirigé pour régler, `payment_status` reste "pending" jusqu'au
    # règlement (webhook ou `/pay/card/check`). Absent partout ailleurs — ce
    # n'est pas une donnée de la commande, juste le résultat de l'initiation.
    pay_url: str | None = None


def serialize_order(order: Order, pay_url: str | None = None) -> OrderOut:
    """
    À utiliser quand une route veut renvoyer `pay_url` en plus des champs de
    la commande — `response_model` seul ne peut pas le lire depuis `Order`,
    qui n'a pas cette colonne (même principe que
    `tenants.schemas.serialize_restaurant`).
    """
    return OrderOut.model_validate(order).model_copy(update={"pay_url": pay_url})


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
    # Pour que le serveur sache si une confirmation + facture a été envoyée.
    customer_email: str | None
