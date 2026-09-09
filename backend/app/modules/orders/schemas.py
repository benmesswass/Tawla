from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field

from app.core.dates import UtcDatetime
from app.modules.orders.models import (
    ModificationLineStatus,
    ModificationRequestStatus,
    Order,
    OrderPaymentStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
)


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
    # Clé d'appareil (panier partagé de table, ROADMAP.md §Override —
    # identité de table) : identifie QUI a ajouté cette ligne, pour permettre
    # de n'en retirer que les siennes depuis le panier partagé. Purement
    # déclaratif comme le reste de ce modèle — jamais lu pour une règle
    # métier, jamais vérifié contre l'appareil qui envoie le message.
    added_by_key: str | None = None
    # Prénom affiché sous le plat dans le panier partagé, et figé sur la
    # commande une fois validée (voir `OrderItemOut`) — pour que l'addition
    # garde "Karim" plutôt que de redevenir "Personne 2" après coup.
    added_by_name: str | None = None


class OrderItemsUpdate(BaseModel):
    """
    Édition directe fenêtre 1 (`PUT /orders/{id}/items`) — le panier
    *souhaité* dans son ensemble, jamais un delta : le service compare aux
    `OrderItem` actuels lui-même. Même forme que `OrderCreate.items`, pour
    que l'écran d'édition réutilise telle quelle la logique panier du menu.
    """

    items: list[OrderItemCreate]


class ModificationRequestCreate(BaseModel):
    """
    Fenêtre 2 (`POST /orders/{id}/modification-requests`) — même principe que
    `OrderItemsUpdate` : le panier *souhaité* dans son ensemble. Le service
    compare aux `OrderItem` actuels pour ne garder que ce qui change.
    """

    items: list[OrderItemCreate]


class ModificationLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    menu_item_id: int
    menu_item_name: str
    unit_price: float
    previous_quantity: int
    requested_quantity: int
    notes: str | None
    is_shared: bool
    status: ModificationLineStatus


class ModificationRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    table_id: int
    table_label: str
    status: ModificationRequestStatus
    created_at: UtcDatetime
    resolved_at: UtcDatetime | None
    lines: list[ModificationLineOut]


class ModificationLineDecision(BaseModel):
    line_id: int
    accepted: bool


class ModificationRequestResolve(BaseModel):
    # Doit couvrir exactement les lignes encore `pending` de la demande — ni
    # plus ni moins (voir service.py::resolve_modification_request) : jamais
    # de résolution silencieusement partielle.
    decisions: list[ModificationLineDecision]


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
    added_by_name: str | None = None
    options: list[OrderItemOptionOut] = Field(default_factory=list)


class PayShareRequest(BaseModel):
    """
    Base commune aux trois moyens de paiement — chaque appareil paie SA
    PART, jamais l'addition entière (identité de table, ROADMAP.md §Override,
    extension paiement par personne). `payer_key`/`payer_name` identifient qui
    paie : le montant réellement facturé n'est JAMAIS lu ici, il est
    recalculé côté serveur à partir du roster de la table et des plats de la
    commande (voir orders/split.py) — un client ne peut donc jamais se
    facturer moins que sa part réelle.

    Facultatifs (chaîne vide par défaut) : sans identité déclarée (table qui
    n'a pas activé le scan-identité, ou appel d'un client plus ancien), le
    calcul de part retombe sur "ce qu'il reste à payer" — c'est-à-dire
    l'addition entière tant que personne n'a encore payé sa part, exactement
    le comportement d'avant ce chantier. Dégradation gracieuse, même principe
    que `NullProvider`.
    """

    payer_key: str = Field(default="", max_length=80)
    payer_name: str = Field(default="", max_length=40)
    tip_amount: float = Field(default=0, ge=0)
    # Facultatif : sert uniquement à envoyer la confirmation + facture PDF une
    # fois la commande entièrement payée. Jamais requis, un client qui ne le
    # laisse pas paie pareil.
    customer_email: EmailStr | None = None


class PayCardRequest(PayShareRequest):
    pass


class PayCashRequest(PayShareRequest):
    """
    Le pourboire vaut aussi pour les espèces. Il était purement perdu : le
    client le saisissait, le serveur venait encaisser le total sans lui, et
    personne ne s'apercevait de l'écart avant de compter la caisse.
    """


class PayCardTerminalRequest(PayShareRequest):
    """
    Carte physique : le client demande, un serveur apporte le terminal —
    même mécanique que PayCashRequest, moyen de paiement distinct (voir
    PaymentMethod.CARD_TERMINAL).
    """


class OrderPaymentOut(BaseModel):
    """Une part réglée (ou en cours de règlement) — voir `OrderPayment`.
    `payer_key` est exposé pour qu'UN appareil reconnaisse SA PROPRE ligne
    parmi celles des autres convives (comparé à son identité locale), jamais
    pour authentifier quoi que ce soit — même statut déclaratif que
    `OrderItem.added_by_name`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    payer_key: str
    payer_name: str
    amount: float
    tip_amount: float
    method: PaymentMethod
    status: OrderPaymentStatus
    paid_at: UtcDatetime | None


class PushSubscriptionIn(BaseModel):
    endpoint: str
    keys: dict[str, str]


class PendingSharePaymentOut(BaseModel):
    """Une part en attente d'encaissement en salle (espèces ou terminal),
    vue **staff** — une ligne par PERSONNE qui a demandé à régler (identité
    de table, ROADMAP.md §Override, extension paiement par personne), pas par
    commande : une même commande peut porter plusieurs demandes à la fois."""

    payment_id: int
    order_id: int
    table_id: int
    table_label: str
    payer_name: str
    amount: float
    tip_amount: float
    taken_by_staff_id: int | None
    loyalty_phone: str | None


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
    # Posé uniquement par une édition directe fenêtre 1 (jamais par une
    # transition de statut) — sert au client comme au serveur à savoir que le
    # contenu affiché a changé depuis l'envoi initial.
    items_updated_at: UtcDatetime | None
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
    # Paiement par personne (identité de table, ROADMAP.md §Override,
    # extension) — `payments` porte toutes les parts (payées ou en attente),
    # `amount_paid`/`amount_remaining` sont les agrégats qu'affiche l'écran de
    # paiement pour savoir qui a déjà réglé et ce qu'il reste à couvrir.
    payments: list[OrderPaymentOut] = Field(default_factory=list)
    amount_paid: float = 0
    amount_remaining: float = 0
    items: list[OrderItemOut]
    # Non-null tant qu'au moins une ligne de la dernière demande de
    # modification (fenêtre 2) attend une réponse — c'est ce qui permet à
    # l'écran de suivi de retrouver l'état "en attente" après un
    # rafraîchissement de page, sans dépendre uniquement du WebSocket.
    pending_modification_request: ModificationRequestOut | None = None
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
