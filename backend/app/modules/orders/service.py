from datetime import date, datetime, timezone
from typing import Literal

from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.currency import format_money
from app.core.dates import service_day_start
from app.core.email import is_email_enabled, send_email_with_attachment
from app.core.invoice import generate_invoice_pdf
from app.core.invoice_number import ensure_invoice_number
from app.core.logging import get_logger, log_event
from app.core.payment_provider import PaymentProviderError, get_payment_provider
from app.core.push import send_push_notification
from app.core.subscription import effective_tier, tier_includes, upgrade_required_error
from app.modules.loyalty import service as loyalty_service
from app.modules.menu.models import MenuItem
from app.modules.notifications.manager import manager, table_channel
from app.modules.orders import schemas, split
from app.modules.orders.menu_item_resolution import resolve_selected_options
from app.modules.orders.models import (
    ModificationLineStatus,
    ModificationRequestStatus,
    Order,
    OrderItem,
    OrderItemOption,
    OrderModificationLine,
    OrderModificationRequest,
    OrderPayment,
    OrderPaymentStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.modules.staff import service as staff_service
from app.modules.staff.models import Staff
from app.modules.tables import service as tables_service
from app.modules.tables.models import Table
from app.modules.tenants.models import Restaurant, SubscriptionTier

logger = get_logger("orders")

# États qu'un écran serveur/cuisine considère encore "en cours" : à recharger
# au montage de la page, en complément du push WebSocket (qui ne rattrape
# jamais ce qui s'est passé avant la connexion — cf. audit du 2026-08-10).
ACTIVE_STATUSES: set[OrderStatus] = {
    OrderStatus.PENDING_CONFIRMATION,
    OrderStatus.CONFIRMED,
    OrderStatus.SENT_TO_KITCHEN,
    OrderStatus.IN_PREPARATION,
    OrderStatus.READY,
}

# Une fois quittée l'IN_PREPARATION, la cuisine n'agit plus sur la commande —
# mais doit pouvoir en revoir le détail (onglet "Terminées") en cas de
# réclamation ou d'erreur signalée après coup. Allowlist explicite plutôt que
# "pas dans ACTIVE_STATUSES" : une commande ANNULÉE n'est pas non plus dans
# ACTIVE_STATUSES, alors que la cuisine n'y a rien préparé et ne doit pas la
# voir apparaître comme terminée.
KITCHEN_DONE_STATUSES: set[OrderStatus] = {OrderStatus.READY, OrderStatus.SERVED}

# Fenêtre 2 : une fois la commande confirmée, une modification ne s'applique
# plus directement (voir update_order_items) — elle passe par une demande.
# `READY`/`SERVED`/`CANCELLED` en sont volontairement exclus : rien à changer
# une fois le plat prêt ou la commande terminée.
MODIFICATION_REQUEST_STATUSES: set[OrderStatus] = {
    OrderStatus.CONFIRMED,
    OrderStatus.SENT_TO_KITCHEN,
    OrderStatus.IN_PREPARATION,
}

# Transitions autorisées : on refuse explicitement tout le reste plutôt
# que de laisser un état incohérent se produire silencieusement.
ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING_CONFIRMATION: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.SENT_TO_KITCHEN, OrderStatus.CANCELLED},
    OrderStatus.SENT_TO_KITCHEN: {OrderStatus.IN_PREPARATION, OrderStatus.CANCELLED},
    OrderStatus.IN_PREPARATION: {OrderStatus.READY},
    OrderStatus.READY: {OrderStatus.SERVED},
    OrderStatus.SERVED: set(),
    OrderStatus.CANCELLED: set(),
}

# États dont on ne sort plus — dérivés du dict ci-dessus pour qu'ils ne
# puissent pas diverger le jour où une transition est ajoutée.
TERMINAL_STATUSES = {status for status, allowed in ALLOWED_TRANSITIONS.items() if not allowed}


def _order_channel(order_id: int) -> str:
    """Canal WS dédié à une commande : c'est ce que le client scanne-QR écoute
    pour suivre sa commande en temps réel après validation (audit PO #1)."""
    return f"order-{order_id}"


async def list_active_orders(db: Session, restaurant_id: int) -> list[Order]:
    """
    Rechargement d'état au montage des écrans serveur/cuisine — sans ça, un
    écran ouvert/rafraîchi APRÈS qu'une commande soit passée ne la voit
    jamais (elle ne vit que dans le state React alimenté par le WebSocket).
    """
    return (
        db.query(Order)
        # `table` chargée en une fois : elle est lue pour chaque commande
        # (le libellé affiché au serveur), et cet écran se recharge en plein
        # service — une requête par commande n'y a pas sa place. Les options
        # choisies (France, F5/A2) suivent le même principe : la cuisine lit
        # chaque commande en entier, jamais une requête par article.
        .options(selectinload(Order.table), selectinload(Order.items).selectinload(OrderItem.options))
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.status.in_(ACTIVE_STATUSES),
            # Borne filtrée ici et non dans le composant : l'écran serveur, le
            # plan de salle et la cuisine lisent tous cette liste, et trois
            # filtres séparés finiraient par se contredire (Phase 19.5).
            Order.created_at >= service_day_start(),
        )
        .order_by(Order.created_at)
        .all()
    )


async def list_kitchen_done_orders_today(db: Session, restaurant_id: int) -> list[Order]:
    """
    Détail des commandes terminées par la cuisine aujourd'hui (onglet
    "Terminées" de l'écran cuisine) — jusqu'ici cet onglet n'affichait qu'un
    compteur (`stats/get_kitchen_today_count`), sans le détail des plats.

    Même borne de journée de service que `list_active_orders` : les onglets
    de l'écran cuisine doivent s'accorder sur ce qu'est "aujourd'hui".
    """
    return (
        db.query(Order)
        .options(selectinload(Order.table), selectinload(Order.items).selectinload(OrderItem.options))
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.status.in_(KITCHEN_DONE_STATUSES),
            Order.created_at >= service_day_start(),
        )
        .order_by(Order.ready_at.desc())
        .all()
    )


def _pending_share_payments(db: Session, restaurant_id: int, method: PaymentMethod) -> list[OrderPayment]:
    """
    Parts en attente d'encaissement en salle (espèces ou terminal) — une ligne
    par PERSONNE qui a demandé à régler, pas par commande (identité de table,
    ROADMAP.md §Override, extension paiement par personne) : une même
    commande peut porter plusieurs demandes en attente à la fois, un serveur
    doit pouvoir confirmer celle de Karim sans toucher à celle de Sami.
    Même borne de date que `list_active_orders` (Phase 19.5, F-4) : sans elle,
    une demande vieille de plusieurs jours resterait affichée indéfiniment.
    """
    return (
        db.query(OrderPayment)
        .join(Order, OrderPayment.order_id == Order.id)
        .options(selectinload(OrderPayment.order).selectinload(Order.table))
        .filter(
            Order.restaurant_id == restaurant_id,
            OrderPayment.method == method,
            OrderPayment.status == OrderPaymentStatus.PENDING,
            OrderPayment.created_at >= service_day_start(),
        )
        .order_by(OrderPayment.created_at)
        .all()
    )


async def list_pending_cash_payments(db: Session, restaurant_id: int) -> list[OrderPayment]:
    """Parts en attente de règlement en espèces — voir `_pending_share_payments`."""
    return _pending_share_payments(db, restaurant_id, PaymentMethod.CASH)


async def list_pending_card_terminal_payments(db: Session, restaurant_id: int) -> list[OrderPayment]:
    """Parts en attente de règlement au terminal — voir `_pending_share_payments`."""
    return _pending_share_payments(db, restaurant_id, PaymentMethod.CARD_TERMINAL)


def save_push_subscription(db: Session, order_id: int, subscription: schemas.PushSubscriptionIn) -> None:
    """
    Enregistre l'abonnement Web Push du navigateur qui suit cette commande
    — opt-in explicite côté client (voir menu/[qrToken]/page.tsx), jamais
    déclenché automatiquement.
    """
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "order not found"})

    order.push_subscription = subscription.model_dump_json()
    db.commit()


def purge_terminal_push_subscriptions(db: Session, dry_run: bool = False) -> int:
    """
    Efface les abonnements push restés sur des commandes déjà terminées
    (Phase 16). Depuis `transition_status` la purge est immédiate ; cette
    fonction rattrape les commandes servies avant cette règle, et sert de
    filet si un jour un chemin d'écriture l'oublie.
    """
    stale = (
        db.query(Order)
        .filter(Order.status.in_(TERMINAL_STATUSES), Order.push_subscription.isnot(None))
        .all()
    )
    if dry_run:
        return len(stale)

    for order in stale:
        order.push_subscription = None
    db.commit()
    if stale:
        log_event(logger, "order.push_subscriptions_purged", count=len(stale))
    return len(stale)


def _build_order_items(
    db: Session, restaurant_id: int, items: list[schemas.OrderItemCreate]
) -> list[OrderItem]:
    """
    Valide et construit des `OrderItem` à partir d'un panier envoyé par le
    client — commun à `create_order` et `update_order_items` (fenêtre 1) :
    même règles de disponibilité, de rattachement au restaurant et de prix
    figé des deux côtés, pour ne jamais les faire diverger.
    """
    built: list[OrderItem] = []
    for line in items:
        menu_item = db.get(MenuItem, line.menu_item_id)
        if not menu_item or menu_item.restaurant_id != restaurant_id:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "ITEM_NOT_FOUND",
                    "message": f"menu item {line.menu_item_id} not found",
                    "menu_item_id": line.menu_item_id,
                },
            )
        if not menu_item.is_available:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "ITEM_UNAVAILABLE",
                    "message": f"'{menu_item.name}' is no longer available",
                    "item_name": menu_item.name,
                    "menu_item_id": menu_item.id,
                },
            )

        selected_options = resolve_selected_options(menu_item, line.selected_option_ids)

        # Prix figé au moment T : voir commentaire dans models.py. Le
        # supplément des options choisies (France, F5/A2) est ajouté une
        # fois pour toutes ici — total_amount, la facture et le contrôle de
        # montant Konnect n'ont ensuite jamais besoin de connaître les options,
        # ils lisent unit_price comme avant.
        options_total = sum(float(opt.price_delta) for opt in selected_options)
        built.append(
            OrderItem(
                menu_item_id=menu_item.id,
                menu_item_name=menu_item.name,
                unit_price=float(menu_item.price) + options_total,
                vat_category=menu_item.vat_category,
                quantity=line.quantity,
                notes=line.notes,
                is_shared=line.is_shared,
                shared_with=",".join(str(p) for p in line.shared_with) or None,
                from_suggestion=line.from_suggestion,
                added_by_name=line.added_by_name,
                options=[
                    OrderItemOption(
                        group_name=opt.group.name, option_name=opt.name, price_delta=opt.price_delta
                    )
                    for opt in selected_options
                ],
            )
        )
    return built


async def create_order(db: Session, payload: schemas.OrderCreate) -> Order:
    # La table est retrouvée par son token de QR code, et le restaurant en est
    # déduit : aucun identifiant numérique n'est accepté du client, donc rien
    # n'est devinable (Phase 12.2).
    table = tables_service.get_table_by_qr_token(db, payload.qr_token)

    # Rejeu du même panier : on rend la commande d'origine, avec son
    # `public_token` — le téléphone du client doit retomber sur SA commande,
    # pas sur une qu'il ne pourrait plus suivre. Retour avant toute écriture,
    # donc sans second broadcast : sinon la commande réapparaît sur l'écran
    # serveur alors qu'elle est déjà prise en charge.
    if payload.client_order_id:
        replayed = (
            db.query(Order)
            .filter(Order.table_id == table.id, Order.client_order_id == payload.client_order_id)
            .first()
        )
        if replayed:
            log_event(
                logger, "order.create_replayed",
                restaurant_id=replayed.restaurant_id, order_id=replayed.id, table_id=replayed.table_id,
            )
            return replayed

    if not payload.items:
        raise HTTPException(
            status_code=422,
            detail={"code": "EMPTY_ORDER", "message": "order must contain at least one item"},
        )

    restaurant_id = table.restaurant_id
    restaurant = db.get(Restaurant, restaurant_id)
    # Fidélité réservée à Pro et Business (offre à trois paliers, 2026-08-18) :
    # en Essentiel, le numéro n'est jamais retenu, donc aucune fiche n'est
    # créée plus bas — silencieux plutôt qu'une erreur, le client ne doit
    # jamais voir sa commande bloquée pour un champ facultatif.
    loyalty_phone = (
        payload.loyalty_phone
        if restaurant and tier_includes(effective_tier(restaurant), SubscriptionTier.PRO)
        else None
    )
    return await _finalize_order(
        db, table, _build_order_items(db, restaurant_id, payload.items),
        client_order_id=payload.client_order_id,
        scheduled_for=payload.scheduled_for,
        loyalty_phone=loyalty_phone,
        loyalty_birth_date=payload.loyalty_birth_date,
    )


async def _finalize_order(
    db: Session,
    table: Table,
    order_items: list[OrderItem],
    *,
    client_order_id: str | None = None,
    scheduled_for: datetime | None = None,
    loyalty_phone: str | None = None,
    loyalty_birth_date: date | None = None,
) -> Order:
    """
    Queue commune à toute création de commande, quelle que soit l'origine des
    `OrderItem` déjà validés/figés : le panier envoyé par un seul appareil
    (`create_order`) ou le panier partagé d'une table
    (`create_order_from_table_cart`). Isolée ici pour que les deux chemins ne
    puissent jamais diverger sur la fidélité, les logs ou la diffusion staff.
    """
    order = Order(
        restaurant_id=table.restaurant_id,
        table_id=table.id,
        scheduled_for=scheduled_for,
        loyalty_phone=loyalty_phone,
        client_order_id=client_order_id,
    )
    order.items.extend(order_items)

    db.add(order)
    db.commit()
    db.refresh(order)

    # Enregistre la fiche fidélité dès la commande si le client a saisi son
    # numéro (même s'il n'est jamais passé par une vérification de statut
    # séparée) — le compteur, lui, n'avance qu'au paiement confirmé.
    if order.loyalty_phone:
        loyalty_service.get_or_create_member(db, order.restaurant_id, order.loyalty_phone, loyalty_birth_date)

    log_event(
        logger, "order.created",
        restaurant_id=order.restaurant_id, order_id=order.id, table_id=order.table_id,
    )

    # Le serveur assigné à la table doit voir la commande immédiatement.
    await manager.broadcast(
        order.restaurant_id, channel="staff",
        message={
            "event": "order.pending_confirmation",
            "order_id": order.id,
            "table_id": order.table_id,
            "table_label": order.table_label,
            "created_at": order.created_at.isoformat(),
            "scheduled_for": order.scheduled_for.isoformat() if order.scheduled_for else None,
        },
    )
    # Alerte même écran éteint (demande de Wassim, 2026-08-26) — jamais pour
    # une pré-commande programmée (mode Ramadan) : "à anticiper", pas à
    # prendre en charge maintenant, ce serait une fausse alerte.
    if not order.scheduled_for:
        staff_service.notify_restaurant_staff(
            db, order.restaurant_id,
            title="Nouvelle commande",
            body=f"Table {order.table_label} vient de commander.",
        )
    return order


async def create_order_from_table_cart(
    db: Session, table: Table, client_order_id: str | None = None
) -> Order:
    """
    Valide le panier partagé d'une table (voir `table_cart.py`) : n'importe
    quel appareil connecté au canal de la table peut déclencher cet appel,
    et la commande créée porte l'état tenu par le serveur au moment de
    l'appel — jamais un panier local potentiellement périmé (`ROADMAP.md`
    §Override — Panier synchronisé multi-appareils).

    `pop_all` lit et vide le panier en une seule opération synchrone : deux
    appareils qui valident au même instant ne peuvent jamais transformer
    deux fois le même panier en deux commandes distinctes.
    """
    # Rejeu du même appareil : même garde-fou que `create_order` (ligne plus
    # bas) — une coupure entre le `pop_all` ci-dessous et le "cart.validated"
    # qui devait revenir au client laisse ce dernier réessayer en pensant
    # n'avoir jamais validé. Vérifié AVANT `pop_all` : si la commande existe
    # déjà, on la rend telle quelle, sans toucher au panier (qui peut déjà
    # porter les articles ajoutés par un autre convive depuis).
    if client_order_id:
        replayed = (
            db.query(Order)
            .filter(Order.table_id == table.id, Order.client_order_id == client_order_id)
            .first()
        )
        if replayed:
            log_event(
                logger, "order.create_replayed",
                restaurant_id=replayed.restaurant_id, order_id=replayed.id, table_id=replayed.table_id,
            )
            # Sans ce broadcast, l'appareil qui réessaie n'a AUCUN retour : le
            # chemin normal (plus bas) prévient le canal via "cart.validated",
            # jamais la valeur de retour de cette fonction (`_pump_table` l'ignore) —
            # sans le rejouer ici, il resterait bloqué sur "Valider..." indéfiniment.
            await manager.broadcast(
                replayed.restaurant_id, channel=table_channel(table.id),
                message={"event": "cart.validated", "order_id": replayed.id, "public_token": replayed.public_token},
            )
            return replayed

    # Import différé : `table_cart` importe `resolve_selected_options` depuis
    # `menu_item_resolution`, jamais depuis ce module, pour éviter le cycle
    # (`table_cart` a besoin de créer des commandes, ce module a besoin du
    # panier partagé) — l'import au niveau du module suffirait déjà à casser
    # le cycle, gardé ici local pour que le lien de dépendance saute aux yeux.
    from app.modules.orders import table_cart

    items = table_cart.table_cart_store.pop_all(table.id)
    if not items:
        raise HTTPException(
            status_code=422,
            detail={"code": "EMPTY_ORDER", "message": "order must contain at least one item"},
        )

    try:
        order_items = _build_order_items(db, table.restaurant_id, items)
    except HTTPException:
        # Un article devenu indisponible entre l'ajout et la validation ne
        # doit jamais faire disparaître le panier des AUTRES convives : on le
        # restaure tel quel et on informe toute la table, plutôt que de
        # laisser les autres appareils croire — jusqu'à leur prochaine
        # mutation — qu'il est resté ce qu'ils avaient sous les yeux.
        for item in items:
            table_cart.table_cart_store.set_line(table.id, item)
        await manager.broadcast(
            table.restaurant_id, channel=table_channel(table.id), message=table_cart.snapshot_message(table.id)
        )
        raise

    order = await _finalize_order(db, table, order_items, client_order_id=client_order_id)

    await manager.broadcast(
        table.restaurant_id, channel=table_channel(table.id),
        message={"event": "cart.validated", "order_id": order.id, "public_token": order.public_token},
    )
    return order


async def update_order_items(db: Session, order: Order, payload: schemas.OrderItemsUpdate) -> Order:
    """
    Édition directe par le client — fenêtre 1 uniquement, tant que la
    commande est encore `PENDING_CONFIRMATION`. Passé ce point, une
    modification doit passer par une demande (voir `create_modification_request`)
    plutôt que remplacer silencieusement une commande déjà confirmée : le
    serveur a pu confirmer entre l'ouverture de cet écran et cet appel, d'où
    le 409 explicite plutôt qu'un écrasement.
    """
    if order.status != OrderStatus.PENDING_CONFIRMATION:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ORDER_NOT_MODIFIABLE",
                "message": "order can no longer be edited directly, it has already been confirmed",
            },
        )
    if not payload.items:
        raise HTTPException(
            status_code=422,
            detail={"code": "EMPTY_ORDER", "message": "order must contain at least one item"},
        )

    new_items = _build_order_items(db, order.restaurant_id, payload.items)
    # `cascade="all, delete-orphan"` sur `Order.items` (models.py) : vider la
    # collection supprime réellement les anciennes lignes au commit, pas
    # seulement le lien — jamais de ligne orpheline en base.
    order.items.clear()
    order.items.extend(new_items)
    order.items_updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(order)

    log_event(
        logger, "order.items_updated",
        restaurant_id=order.restaurant_id, order_id=order.id, table_id=order.table_id,
    )

    # Le pool serveur doit voir que la commande a changé avant de confirmer —
    # sans ce broadcast, un serveur qui a ouvert l'écran juste avant l'édition
    # confirmerait sur l'ancien contenu affiché à l'écran.
    await manager.broadcast(
        order.restaurant_id, channel="staff",
        message={
            "event": "order.items_updated",
            "order_id": order.id,
            "items_updated_at": order.items_updated_at.isoformat(),
        },
    )
    # Et les AUTRES appareils qui suivent cette même commande (panier de
    # table partagé, `table_cart.py` : plusieurs convives valident ensemble
    # puis suivent tous le même `order_id`) — sans ce second broadcast sur le
    # canal de la commande, un convive qui n'a pas fait la modification ne la
    # voit jamais tant qu'il ne rafraîchit pas sa page à la main.
    await manager.broadcast(
        order.restaurant_id, channel=_order_channel(order.id),
        message={
            "event": "order.items_updated",
            "order_id": order.id,
            "items_updated_at": order.items_updated_at.isoformat(),
        },
    )
    return order


async def create_modification_request(
    db: Session, order: Order, payload: schemas.ModificationRequestCreate
) -> OrderModificationRequest:
    """
    Fenêtre 2 : la commande est déjà confirmée (peut-être déjà en cuisine),
    le client ne modifie plus directement — il demande, et le serveur décide
    ligne par ligne après vérification avec la cuisine (voir
    `resolve_modification_request`). Même forme de payload que
    `update_order_items` (le panier souhaité dans son ensemble) : le diff est
    calculé ici, jamais envoyé tel quel par le client.
    """
    if order.status not in MODIFICATION_REQUEST_STATUSES:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "MODIFICATION_REQUEST_NOT_ALLOWED",
                "message": "order is not in a state that accepts modification requests",
            },
        )
    # `MODIFICATION_REQUEST_STATUSES` ne connaît que `status` : une commande
    # déjà payée (CONFIRMED/SENT_TO_KITCHEN/IN_PREPARATION s'y trouvent tous)
    # pouvait donc se voir ajouter des articles après paiement, `total_amount`
    # (models.py, recalculé depuis `order.items`) grimpant sans jamais être
    # réencaissé — même angle mort que le F-5 (audit 2026-08-18) déjà corrigé
    # pour l'annulation dans `transition_status`.
    # PARTIALLY_PAID inclus, même raison que transition_status ci-dessous :
    # ajouter des articles changerait `total_amount` alors qu'une part a déjà
    # été réglée sur la base de l'ancien total.
    if order.payment_status in (PaymentStatus.PAID, PaymentStatus.PARTIALLY_PAID):
        raise HTTPException(
            status_code=409,
            detail={"code": "ORDER_ALREADY_PAID", "message": "cannot request a modification on a paid order"},
        )
    if order.pending_modification_request is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "MODIFICATION_REQUEST_ALREADY_PENDING",
                "message": "a modification request is already pending for this order",
            },
        )

    # Même validation qu'une commande (existence, rattachement au restaurant,
    # disponibilité) — le résultat n'est pas gardé, seulement les erreurs
    # qu'il peut lever : un article inexistant ou indisponible ne doit jamais
    # se retrouver dans une demande.
    _build_order_items(db, order.restaurant_id, payload.items)

    current_by_menu_item = {item.menu_item_id: item for item in order.items}
    requested_by_menu_item = {line.menu_item_id: line for line in payload.items}

    lines: list[OrderModificationLine] = []
    for menu_item_id in set(current_by_menu_item) | set(requested_by_menu_item):
        current_item = current_by_menu_item.get(menu_item_id)
        requested_line = requested_by_menu_item.get(menu_item_id)
        previous_quantity = current_item.quantity if current_item else 0
        requested_quantity = requested_line.quantity if requested_line else 0
        if previous_quantity == requested_quantity:
            continue

        if current_item is not None:
            # Ajustement (hausse ou baisse) d'un article déjà commandé : nom
            # et prix déjà figés à la commande d'origine, jamais relus depuis
            # MenuItem, qui a pu changer entre-temps.
            menu_item_name = current_item.menu_item_name
            unit_price = float(current_item.unit_price)
        else:
            # Article pas encore dans la commande : rien à réutiliser, on part
            # du prix actuel de la carte — même règle qu'une commande neuve.
            menu_item = db.get(MenuItem, menu_item_id)
            menu_item_name = menu_item.name
            unit_price = float(menu_item.price)

        lines.append(
            OrderModificationLine(
                menu_item_id=menu_item_id,
                menu_item_name=menu_item_name,
                unit_price=unit_price,
                previous_quantity=previous_quantity,
                requested_quantity=requested_quantity,
                notes=(requested_line.notes if requested_line else current_item.notes),
                is_shared=(requested_line.is_shared if requested_line else current_item.is_shared),
            )
        )

    if not lines:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "NO_CHANGES_REQUESTED",
                "message": "requested items are identical to the current order",
            },
        )

    request = OrderModificationRequest(order_id=order.id, restaurant_id=order.restaurant_id, lines=lines)
    db.add(request)
    db.commit()
    db.refresh(request)

    log_event(
        logger, "order.modification_requested",
        restaurant_id=order.restaurant_id, order_id=order.id, request_id=request.id,
    )

    # La file dédiée du pool serveur doit voir la demande sans recharger la
    # page — même principe que "order.pending_confirmation" à la création.
    await manager.broadcast(
        order.restaurant_id, channel="staff",
        message={
            "event": "order.modification_requested",
            "order_id": order.id,
            "table_id": order.table_id,
            "table_label": order.table_label,
            "request_id": request.id,
            "created_at": request.created_at.isoformat(),
            "lines": [
                {
                    "menu_item_name": line.menu_item_name,
                    "previous_quantity": line.previous_quantity,
                    "requested_quantity": line.requested_quantity,
                }
                for line in lines
            ],
        },
    )
    # Et les AUTRES appareils qui suivent cette même commande (panier de
    # table partagé) : sans ce broadcast, l'écran de suivi d'un convive qui
    # n'a pas fait la demande ne désactive jamais son propre bouton
    # "modifier" (`OrderOut.pending_modification_request`, lu par le
    # frontend) — il peut tenter une seconde demande concurrente et tomber
    # sur MODIFICATION_REQUEST_ALREADY_PENDING sans comprendre pourquoi.
    await manager.broadcast(
        order.restaurant_id, channel=_order_channel(order.id),
        message={"event": "order.modification_requested", "order_id": order.id},
    )
    return request


async def list_pending_modification_requests(db: Session, restaurant_id: int) -> list[OrderModificationRequest]:
    """Rechargement d'état pour la file serveur au montage — même raison
    d'être que list_active_orders : le WebSocket seul ne rattrape jamais ce
    qui s'est passé avant la connexion."""
    return (
        db.query(OrderModificationRequest)
        .options(
            selectinload(OrderModificationRequest.lines),
            selectinload(OrderModificationRequest.order).selectinload(Order.table),
        )
        .filter(
            OrderModificationRequest.restaurant_id == restaurant_id,
            OrderModificationRequest.status == ModificationRequestStatus.PENDING,
        )
        .order_by(OrderModificationRequest.created_at)
        .all()
    )


async def resolve_modification_request(
    db: Session,
    order: Order,
    request_id: int,
    decisions: list[schemas.ModificationLineDecision],
    staff: Staff,
) -> OrderModificationRequest:
    """
    Le serveur répond ligne par ligne, après vérification avec la cuisine —
    en un seul appel qui doit couvrir exactement les lignes encore en
    attente (jamais de résolution silencieusement partielle). Les lignes
    acceptées sont appliquées aux vraies `OrderItem` ; les refusées ne
    touchent à rien, le client peut ensuite commander séparément ce qui a
    été refusé (flux normal de création, aucune route dédiée).
    """
    request = db.get(OrderModificationRequest, request_id)
    if not request or request.order_id != order.id or request.restaurant_id != staff.restaurant_id:
        raise HTTPException(
            status_code=404,
            detail={"code": "MODIFICATION_REQUEST_NOT_FOUND", "message": "modification request not found"},
        )
    if request.status != ModificationRequestStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "MODIFICATION_REQUEST_ALREADY_RESOLVED",
                "message": "this modification request has already been resolved",
            },
        )

    lines_by_id = {line.id: line for line in request.lines}
    pending_ids = {line.id for line in request.lines if line.status == ModificationLineStatus.PENDING}
    decided_ids = {decision.line_id for decision in decisions}
    if decided_ids != pending_ids or any(decision.line_id not in lines_by_id for decision in decisions):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INCOMPLETE_RESOLUTION",
                "message": "every pending line must receive a decision, exactly once",
            },
        )

    items_by_menu_item = {item.menu_item_id: item for item in order.items}
    for decision in decisions:
        line = lines_by_id[decision.line_id]
        line.status = ModificationLineStatus.ACCEPTED if decision.accepted else ModificationLineStatus.DECLINED
        if not decision.accepted:
            continue

        existing = items_by_menu_item.get(line.menu_item_id)
        if line.requested_quantity == 0:
            if existing:
                order.items.remove(existing)
        elif existing:
            existing.quantity = line.requested_quantity
            existing.notes = line.notes
            existing.is_shared = line.is_shared
        else:
            new_item = OrderItem(
                menu_item_id=line.menu_item_id,
                menu_item_name=line.menu_item_name,
                unit_price=line.unit_price,
                quantity=line.requested_quantity,
                notes=line.notes,
                is_shared=line.is_shared,
            )
            order.items.append(new_item)
            items_by_menu_item[line.menu_item_id] = new_item

    request.status = ModificationRequestStatus.RESOLVED
    request.resolved_at = datetime.now(timezone.utc)
    order.items_updated_at = request.resolved_at
    db.commit()
    db.refresh(request)
    db.refresh(order)

    log_event(
        logger, "order.modification_resolved",
        restaurant_id=order.restaurant_id, order_id=order.id, request_id=request.id, staff_id=staff.id,
    )

    # Le client attend la réponse sur l'écran de suivi — détail ligne par
    # ligne pour qu'un refus partiel ne se lise jamais comme un refus global
    # ni comme une acceptation totale.
    await manager.broadcast(
        order.restaurant_id, channel=_order_channel(order.id),
        message={
            "event": "order.modification_resolved",
            "order_id": order.id,
            "request_id": request.id,
            "lines": [
                {
                    "id": line.id,
                    "menu_item_id": line.menu_item_id,
                    "menu_item_name": line.menu_item_name,
                    "unit_price": float(line.unit_price),
                    "previous_quantity": line.previous_quantity,
                    "requested_quantity": line.requested_quantity,
                    "notes": line.notes,
                    "is_shared": line.is_shared,
                    "status": line.status.value,
                }
                for line in request.lines
            ],
        },
    )
    # Retire la demande de la file serveur partagée, chez les collègues qui
    # ne sont pas celui qui vient de répondre.
    await manager.broadcast(
        order.restaurant_id, channel="staff",
        message={"event": "order.modification_resolved", "order_id": order.id, "request_id": request.id},
    )
    return request


async def claim_order(db: Session, order_id: int, staff: Staff) -> Order:
    """
    Prise en charge d'une commande en attente depuis le pool partagé —
    c'est ce qui fait passer une commande de "visible par tous les
    serveurs" à "affectée à Sami", et alimente les stats par serveur
    (dashboard manager, Phase 3).
    """
    order = db.get(Order, order_id)
    if not order or order.restaurant_id != staff.restaurant_id:
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "order not found"})
    if order.status != OrderStatus.PENDING_CONFIRMATION:
        raise HTTPException(
            status_code=409,
            detail={"code": "INVALID_TRANSITION", "message": "order is not pending confirmation"},
        )
    if order.taken_by_staff_id is not None and order.taken_by_staff_id != staff.id:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ALREADY_CLAIMED",
                "message": "order already claimed by another staff member",
                "taken_by_staff_id": order.taken_by_staff_id,
            },
        )

    order.taken_by_staff_id = staff.id
    order.taken_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(order)

    log_event(logger, "order.claimed", restaurant_id=order.restaurant_id, order_id=order.id, staff_id=staff.id)

    await manager.broadcast(
        order.restaurant_id, channel="staff",
        message={
            "event": "order.claimed",
            "order_id": order.id,
            "taken_by_staff_id": staff.id,
            "taken_by_staff_name": staff.name,
        },
    )
    await _broadcast_staff_assigned(order, staff)
    return order


async def _broadcast_staff_assigned(order: Order, staff: Staff) -> None:
    """Le client suit sa commande sur son téléphone — dès qu'un serveur est
    affecté (claim explicite ou auto-claim à la confirmation), on le lui dit
    par son prénom plutôt que de le laisser deviner."""
    await manager.broadcast(
        order.restaurant_id, channel=_order_channel(order.id),
        message={"event": "order.staff_assigned", "order_id": order.id, "staff_name": staff.name},
    )


async def transition_status(db: Session, order_id: int, new_status: OrderStatus, staff: Staff) -> Order:
    order = db.get(Order, order_id)
    if not order or order.restaurant_id != staff.restaurant_id:
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "order not found"})

    allowed = ALLOWED_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "INVALID_TRANSITION",
                "message": f"cannot go from '{order.status.value}' to '{new_status.value}'",
                "from": order.status.value,
                "to": new_status.value,
            },
        )

    # `ALLOWED_TRANSITIONS` ne connaît que `status` : une commande déjà payée
    # pouvait donc être annulée (F-5, audit 2026-08-18), `payment_status`
    # n'étant jamais regardé ici.
    # PARTIALLY_PAID inclus (identité de table, ROADMAP.md §Override,
    # extension paiement par personne) : annuler une commande dont au moins
    # une part a déjà été réglée laisserait cet argent encaissé pour rien,
    # sans commande à servir en face.
    if new_status == OrderStatus.CANCELLED and order.payment_status in (
        PaymentStatus.PAID, PaymentStatus.PARTIALLY_PAID,
    ):
        raise HTTPException(
            status_code=409,
            detail={"code": "ORDER_ALREADY_PAID", "message": "cannot cancel an order that has already been paid"},
        )

    order.status = new_status
    now = datetime.now(timezone.utc)
    newly_assigned = False
    if new_status == OrderStatus.CONFIRMED:
        order.confirmed_at = now
        # Un serveur qui confirme sans être passé par le claim explicite
        # (ex: bouton unique côté UI) se voit quand même attribuer la
        # commande — les stats par serveur ne doivent jamais dépendre d'une
        # étape UI facultative.
        if order.taken_by_staff_id is None:
            order.taken_by_staff_id = staff.id
            order.taken_at = now
            newly_assigned = True
    if new_status == OrderStatus.SENT_TO_KITCHEN:
        order.sent_to_kitchen_at = now
    if new_status == OrderStatus.IN_PREPARATION:
        order.preparation_started_at = now
    if new_status == OrderStatus.READY:
        order.ready_at = now
    if new_status == OrderStatus.SERVED:
        order.served_at = now
    # L'abonnement push ne sert qu'à annoncer « votre commande est prête ». Sur
    # un statut terminal il n'a plus de finalité, et c'est un point de contact
    # vers le navigateur d'un client : on ne le garde pas (Phase 16).
    if new_status in TERMINAL_STATUSES:
        order.push_subscription = None

    db.commit()
    db.refresh(order)

    log_event(
        logger, "order.status_changed",
        restaurant_id=order.restaurant_id, order_id=order.id, new_status=new_status.value,
    )

    if newly_assigned:
        await _broadcast_staff_assigned(order, staff)

    # La cuisine ne doit voir la commande QUE une fois validée par le serveur.
    if new_status == OrderStatus.SENT_TO_KITCHEN:
        await manager.broadcast(
            order.restaurant_id, channel="kitchen",
            message={
                "event": "order.sent_to_kitchen",
                "order_id": order.id,
                "table_id": order.table_id,
                "table_label": order.table_label,
                "scheduled_for": order.scheduled_for.isoformat() if order.scheduled_for else None,
                "sent_to_kitchen_at": order.sent_to_kitchen_at.isoformat() if order.sent_to_kitchen_at else None,
                "items": [
                    {
                        "name": i.menu_item_name,
                        "quantity": i.quantity,
                        "notes": i.notes,
                        "is_shared": i.is_shared,
                        # France, F5/A2 : ce que la cuisine doit préparer
                        # exactement (« à point », « sans oignons »...), pas
                        # seulement l'article. Nom du prix jamais inclus ici —
                        # la cuisine n'en a pas besoin.
                        "options": [
                            {"group_name": o.group_name, "option_name": o.option_name} for o in i.options
                        ],
                    }
                    for i in order.items
                ],
            },
        )

    # Les serveurs aussi doivent savoir que la table est passée en cuisine :
    # sans ça, leur plan de salle la montre libre alors qu'elle est occupée, et
    # ils ne le découvrent qu'au prochain rechargement de page.
    if new_status == OrderStatus.SENT_TO_KITCHEN:
        await manager.broadcast(
            order.restaurant_id, channel="staff",
            message={
                "event": "order.sent_to_kitchen",
                "order_id": order.id,
                "table_id": order.table_id,
                "table_label": order.table_label,
            },
        )

    # Le plat est prêt : le serveur doit venir le chercher et le servir.
    # Sans ce broadcast, "ready" n'a jamais eu de porte de sortie dans l'UI
    # (audit QA — statut "served" mort).
    if new_status == OrderStatus.READY:
        await manager.broadcast(
            order.restaurant_id, channel="staff",
            message={
                "event": "order.ready", "order_id": order.id,
                "table_id": order.table_id, "table_label": order.table_label,
                "ready_at": order.ready_at.isoformat() if order.ready_at else None,
            },
        )
        # Le WebSocket ci-dessus ne réveille que l'onglet resté ouvert au
        # premier plan — la notification push touche aussi le client qui a
        # quitté la page (best-effort, no-op si pas d'abonnement/clés VAPID).
        # Réservée à Business (offre à trois paliers, 2026-08-18) : silencieux
        # pour les autres paliers, le WebSocket ci-dessus couvre déjà l'écran
        # resté ouvert.
        restaurant = db.get(Restaurant, order.restaurant_id)
        if order.push_subscription and restaurant and tier_includes(
            effective_tier(restaurant), SubscriptionTier.BUSINESS
        ):
            send_push_notification(
                order.push_subscription,
                title="Votre commande est prête !",
                body=f"Commande #{order.id} — un serveur arrive à votre table.",
            )

    # Le client qui a scanné le QR suit sa commande en direct (audit PO —
    # aucune visibilité après "commande envoyée" jusqu'ici).
    await manager.broadcast(
        order.restaurant_id, channel=_order_channel(order.id),
        message={"event": "order.status_changed", "order_id": order.id, "status": new_status.value},
    )

    return order


def _get_payable_order(db: Session, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "order not found"})
    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(
            status_code=409, detail={"code": "ORDER_CANCELLED", "message": "cannot pay a cancelled order"}
        )
    if order.payment_status == PaymentStatus.PAID:
        raise HTTPException(status_code=409, detail={"code": "ALREADY_PAID", "message": "order already paid"})
    # Rien ne garantissait qu'un humain côté restaurant avait vu la commande
    # avant qu'elle soit payée (F-5, audit 2026-08-18) — `request_cash_payment`
    # suppose ensuite que `taken_by_staff_id` est déjà renseigné (auto-claim à
    # la confirmation), hypothèse fausse sans ce garde-fou.
    if order.status == OrderStatus.PENDING_CONFIRMATION:
        raise HTTPException(
            status_code=409,
            detail={"code": "ORDER_NOT_CONFIRMED", "message": "cannot pay an order that hasn't been confirmed yet"},
        )
    # Sans ce garde-fou, une demande de modification encore en attente (voir
    # `create_modification_request`) pouvait être résolue APRÈS que le client
    # ait payé entre-temps — le total accepté par le serveur change alors
    # sans jamais être réencaissé, le même trou que `ORDER_ALREADY_PAID`
    # ci-dessus mais ouvert par l'autre bout. On bloque le paiement plutôt
    # que la résolution : la demande n'a pas de statut "annulée", la laisser
    # bloquée `pending` pour toujours serait pire.
    if order.pending_modification_request is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "MODIFICATION_REQUEST_PENDING",
                "message": "cannot pay while a modification request is still pending",
            },
        )
    return order


def _roster_names(table_id: int) -> list[str]:
    """Le roster courant de la table (identité de table, ROADMAP.md
    §Override) — import différé : `tables/roster` n'a pas besoin de connaître
    `orders`, seul ce module a besoin de lui (même raison que l'import
    différé de `table_cart` dans `create_order_from_table_cart`)."""
    from app.modules.tables.roster import table_roster_store

    return [p.name for p in table_roster_store.snapshot(table_id)]


def _split_mode(table_id: int) -> split.SplitMode:
    """Mode de répartition choisi par la table (« par plat » par défaut) —
    même import différé que `_roster_names`, même raison."""
    from app.modules.tables.split_mode import table_split_mode_store

    return table_split_mode_store.get(table_id)


def _paid_names(order: Order) -> set[str]:
    return {p.payer_name for p in order.payments if p.status == OrderPaymentStatus.PAID}


def _get_payable_share(
    db: Session, order_id: int, payer_key: str, payer_name: str
) -> tuple[Order, OrderPayment | None, float]:
    """
    Garde-fous + montant pour UNE part de commande. `payer_key` vide (aucune
    identité déclarée) : traité comme un appareil anonyme unique, jamais
    confondu avec un autre appel anonyme — voir le repli de `PayShareRequest`.

    Renvoie `(order, ligne_en_attente_existante, montant)` : si une part
    PENDING existe déjà pour cette clé (rejeu d'un double clic, ou retour sur
    un paiement carte non encore réglé), elle est renvoyée telle quelle —
    l'appelant ne doit jamais en créer une seconde pour la même personne.
    """
    order = _get_payable_order(db, order_id)

    for payment in order.payments:
        if payment.payer_key == payer_key:
            if payment.status == OrderPaymentStatus.PAID:
                raise HTTPException(
                    status_code=409, detail={"code": "SHARE_ALREADY_PAID", "message": "your share is already paid"}
                )
            return order, payment, float(payment.amount)

    names = _roster_names(order.table_id)
    amount = split.compute_payable_amount(order, names, payer_name, _paid_names(order), _split_mode(order.table_id))
    return order, None, amount


def _mark_order_pending(db: Session, order: Order, payment: OrderPayment) -> None:
    """
    Reflète, au niveau agrégé de la commande, qu'une part vient d'être mise
    en attente (carte initiée chez le fournisseur, espèces/terminal
    demandés) — `payment_method`/`tip_amount` continuent d'y être lisibles
    avant même qu'une part soit confirmée, comme avant ce chantier (l'écran
    de suivi et le serveur les affichaient déjà à ce stade). PARTIALLY_PAID
    prime sur PENDING : si quelqu'un a déjà réglé sa part, une nouvelle
    demande d'un autre convive ne doit pas faire disparaître cette
    information au niveau de la commande. `_after_share_paid` réécrit ces
    mêmes champs une fois la commande entièrement payée, à partir des seules
    parts PAID cette fois — une tentative abandonnée en cours de route (carte
    jamais réglée, cash finalement payé) ne doit pas polluer le total final.
    """
    db.flush()
    db.refresh(order)
    order.payment_method = payment.method
    order.tip_amount = sum(float(p.tip_amount) for p in order.payments)
    if order.payment_status not in (PaymentStatus.PARTIALLY_PAID, PaymentStatus.PAID):
        order.payment_status = PaymentStatus.PENDING
    db.commit()


def _after_share_paid(db: Session, order: Order, restaurant: Restaurant | None) -> bool:
    """
    Met à jour l'état agrégé de la commande après qu'UNE part vient d'être
    marquée payée. Renvoie True si la commande est désormais ENTIÈREMENT
    payée — c'est ce moment-là, et lui seul, qui déclenche facture/e-mail/
    fidélité, jamais à chaque part réglée (une table de trois ne doit pas
    recevoir trois factures).

    `payment_method`/`tip_amount`/`paid_at` restent les colonnes AGRÉGÉES
    lues par la facture — jamais mises à jour tant que tout le monde n'a pas
    payé, pour ne jamais représenter la commande comme payée par un seul
    moyen ou pour un seul pourboire pendant qu'il en manque une part.
    """
    db.refresh(order)
    if order.amount_remaining > 0.005:
        order.payment_status = PaymentStatus.PARTIALLY_PAID
        db.commit()
        return False

    paid_payments = [p for p in order.payments if p.status == OrderPaymentStatus.PAID]
    last = max(paid_payments, key=lambda p: p.paid_at or datetime.min.replace(tzinfo=timezone.utc)) if paid_payments else None
    if last:
        order.payment_method = last.method
    order.tip_amount = sum(float(p.tip_amount) for p in paid_payments)
    order.payment_status = PaymentStatus.PAID
    order.paid_at = datetime.now(timezone.utc)
    ensure_invoice_number(db, order)
    db.commit()
    db.refresh(order)

    if order.loyalty_phone:
        loyalty_service.record_completed_order(db, order.restaurant_id, order.loyalty_phone)
    _send_payment_confirmation(order, restaurant)
    return True


def _send_payment_confirmation(order: Order, restaurant: Restaurant | None) -> None:
    """
    Confirmation + facture PDF par email, si (et seulement si) le client a
    laissé son adresse au moment de payer (confirmations de paiement,
    2026-08-19) — quel que soit le moyen. Best-effort absolu : ne doit
    JAMAIS lever, un email raté ne doit jamais faire échouer un paiement déjà
    encaissé (un nom de plat en arabe ferait par exemple échouer le rendu PDF,
    la police du cœur ne couvrant que le latin-1).
    """
    if not order.customer_email or not restaurant or not is_email_enabled():
        return
    try:
        pdf_bytes = generate_invoice_pdf(order, restaurant)
        total = order.total_amount + float(order.tip_amount)
        sent = send_email_with_attachment(
            to=order.customer_email,
            subject=f"Votre facture - {restaurant.name}, commande #{order.id}",
            html_body=(
                f"<p>Bonjour,</p>"
                f"<p>Votre commande #{order.id} chez {restaurant.name} a bien été payée "
                f"({format_money(total)}). Vous trouverez la facture détaillée en pièce jointe.</p>"
                f"<p>Merci de votre visite !</p>"
            ),
            attachment_filename=f"facture-commande-{order.id}.pdf",
            attachment_bytes=pdf_bytes,
        )
        log_event(logger, "order.payment_confirmation_email", order_id=order.id, sent=sent)
    except Exception as err:  # noqa: BLE001 — best-effort, voir docstring
        log_event(logger, "order.payment_confirmation_email_failed", order_id=order.id, error=str(err))


async def pay_by_card_simulated(
    db: Session, order_id: int, payer_key: str, payer_name: str, tip_amount: float,
    customer_email: str | None = None,
) -> Order:
    """
    Paiement carte — mode simulé (Konnect/Stripe choisis comme prestataires,
    mais pas de vraie intégration tant qu'un pilote resto réel n'a pas de clés
    API). Règle la part de CE convive (identité de table, ROADMAP.md
    §Override, extension paiement par personne), pas forcément toute
    l'addition. Confirmation immédiate, comme le fallback simulé de Darna
    quand Konnect est désactivé.

    Réservé à Pro et Business (offre à trois paliers, 2026-08-18) : en
    Essentiel, seul l'encaissement en espèces est proposé.
    """
    order, existing, amount = _get_payable_share(db, order_id, payer_key, payer_name)

    restaurant = db.get(Restaurant, order.restaurant_id)
    if not restaurant or not tier_includes(effective_tier(restaurant), SubscriptionTier.PRO):
        raise upgrade_required_error(SubscriptionTier.PRO)

    payment = existing or OrderPayment(order_id=order.id, payer_key=payer_key, payer_name=payer_name, method=PaymentMethod.CARD)
    payment.amount = amount
    payment.tip_amount = tip_amount
    payment.status = OrderPaymentStatus.PAID
    payment.paid_at = datetime.now(timezone.utc)
    if customer_email:
        payment.customer_email = customer_email
        order.customer_email = customer_email
    if not existing:
        db.add(payment)
    db.commit()

    log_event(
        logger, "order.share_paid_card_simulated",
        restaurant_id=order.restaurant_id, order_id=order.id, payer_name=payer_name,
        amount=amount, tip_amount=tip_amount,
    )
    fully_paid = _after_share_paid(db, order, restaurant)
    db.refresh(order)
    # Les autres appareils qui suivent cette commande (panier de table
    # partagé) doivent voir la part réglée sans rafraîchir — même événement
    # que le paiement carte réel (`settle_card_payment`) et les paiements
    # cash/terminal.
    await manager.broadcast(
        order.restaurant_id, channel=_order_channel(order.id),
        message={"event": "order.payment_confirmed", "order_id": order.id, "fully_paid": fully_paid},
    )
    return order


async def start_card_payment(
    db: Session, order_id: int, payer_key: str, payer_name: str, tip_amount: float,
    customer_email: str | None = None,
) -> tuple[Order, str | None]:
    """
    Paiement carte du client — modèle direct (connexion Konnect/Stripe au
    paiement carte, 2026-08-19) : réglé chez LE RESTAURANT, jamais chez Tawla.
    Règle la part de CE convive, pas forcément toute l'addition (identité de
    table, ROADMAP.md §Override, extension paiement par personne). Retombe
    sur le mode démo (`pay_by_card_simulated`) tant que ce restaurant précis
    n'a pas connecté son propre wallet/compte — dégradation gracieuse comme
    le reste de l'intégration.

    Renvoie `(order, pay_url)` : `pay_url` non-null seulement quand un
    règlement réel vient d'être initié — cette part reste alors PENDING, le
    client doit être redirigé pour payer.
    """
    order, existing, amount = _get_payable_share(db, order_id, payer_key, payer_name)

    restaurant = db.get(Restaurant, order.restaurant_id)
    if not restaurant or not tier_includes(effective_tier(restaurant), SubscriptionTier.PRO):
        raise upgrade_required_error(SubscriptionTier.PRO)

    credentials = restaurant.payment_credentials()
    provider = get_payment_provider(credentials)
    if not provider.is_available():
        order = await pay_by_card_simulated(db, order_id, payer_key, payer_name, tip_amount, customer_email)
        return order, None

    # Rejeu (retour navigateur avant règlement, double clic) : redirige vers
    # LE MÊME paiement en cours plutôt que d'en initier un second pour la
    # même personne — `payment_ref` a été gardé sur la ligne existante.
    if existing and existing.payment_ref:
        provider_again = get_payment_provider(credentials)
        try:
            state = provider_again.get_payment(existing.payment_ref)
            if state.status == "completed":
                await settle_card_payment(db, order_id, existing.id)
                db.refresh(order)
                return order, None
        except PaymentProviderError:
            pass  # retombe sur une nouvelle initiation ci-dessous

    payment = existing or OrderPayment(order_id=order.id, payer_key=payer_key, payer_name=payer_name, method=PaymentMethod.CARD)
    payment.amount = amount
    payment.tip_amount = tip_amount
    payment.status = OrderPaymentStatus.PENDING
    if customer_email:
        payment.customer_email = customer_email
        order.customer_email = customer_email
    if not existing:
        db.add(payment)
    _mark_order_pending(db, order, payment)
    db.refresh(payment)

    charge_amount = amount + tip_amount
    qr_token = order.table.qr_token
    try:
        result = provider.init_payment(
            amount=charge_amount,
            order_id=str(order.id),
            payment_id=str(payment.id),
            description=f"{order.table_label} — {payer_name or 'commande'} #{order.id}",
            success_url=(
                f"{settings.frontend_url}/menu/{qr_token}"
                f"?konnect=success&order_id={order.id}&order_token={order.public_token}&payment_id={payment.id}"
            ),
            fail_url=f"{settings.frontend_url}/menu/{qr_token}?konnect=fail",
            lifespan_minutes=30,
        )
    except PaymentProviderError as err:
        log_event(
            logger, "order.card_payment_init_failed",
            restaurant_id=order.restaurant_id, order_id=order.id, payer_name=payer_name, error=str(err),
        )
        raise HTTPException(
            status_code=502, detail={"code": "PAYMENT_INIT_FAILED", "message": "could not start the payment"}
        ) from err

    payment.payment_ref = result.payment_ref
    db.commit()
    db.refresh(order)

    log_event(
        logger, "order.card_payment_initiated",
        restaurant_id=order.restaurant_id, order_id=order.id, payer_name=payer_name,
        payment_ref=result.payment_ref, amount=charge_amount,
    )
    # Les AUTRES appareils qui suivent cette commande doivent voir qu'un
    # paiement est en cours pour cette personne.
    await manager.broadcast(
        order.restaurant_id, channel=_order_channel(order.id),
        message={"event": "order.payment_requested", "order_id": order.id},
    )
    return order, result.pay_url


SettleCardResult = Literal["paid", "pending", "not_found", "error"]


async def settle_card_payment(db: Session, order_id: int, payment_id: int) -> SettleCardResult:
    """
    Règle une part payée par carte (Konnect/Stripe) en attente — appelée par
    le webhook ET par le filet de sécurité `/pay/card/check`, même principe
    d'idempotence que `settle_subscription_payment` : gardée par
    `payment_ref`, jamais réglée deux fois pour la même référence.
    """
    order = db.get(Order, order_id)
    if not order:
        return "not_found"
    payment = db.get(OrderPayment, payment_id)
    if not payment or payment.order_id != order_id:
        return "not_found"

    # Rien à régler : déjà réglé par un appel concurrent (webhook + retour
    # client arrivés en même temps), ou pas une part carte en attente.
    if payment.method != PaymentMethod.CARD or payment.status != OrderPaymentStatus.PENDING:
        return "pending"
    payment_ref = payment.payment_ref
    if not payment_ref:
        return "pending"

    restaurant = db.get(Restaurant, order.restaurant_id)
    credentials = restaurant.payment_credentials() if restaurant else None
    if not credentials:
        # Fournisseur déconnecté par le manager entre l'initiation et le
        # règlement (rare) : rien à régler sans identifiants, ne pas
        # planter le webhook pour autant.
        # Volontairement PAS `provider.is_available()` ici (voir sa docstring
        # dans payment_provider.py) : un paiement déjà initié se règle même si
        # le drapeau global a été désactivé entre-temps, seuls les
        # identifiants du restaurant comptent à ce stade.
        log_event(
            logger, "order.card_payment_settle_missing_credentials",
            restaurant_id=order.restaurant_id, order_id=order.id, payment_id=payment_id,
        )
        return "error"
    provider = get_payment_provider(credentials)

    try:
        state = provider.get_payment(payment_ref)
    except PaymentProviderError as err:
        log_event(
            logger, "order.card_payment_settle_fetch_failed",
            restaurant_id=order.restaurant_id, order_id=order.id, payment_id=payment_id, error=str(err),
        )
        return "error"

    if state.status != "completed":
        return "pending"

    # Contrôle d'intégrité : montant réellement reçu jamais inférieur à la
    # part + pourboire figés à l'initiation — jamais un montant transmis par
    # le client ou par le webhook lui-même.
    expected_smallest_unit = provider.to_smallest_unit(float(payment.amount) + float(payment.tip_amount))
    if state.reached_amount < expected_smallest_unit:
        log_event(
            logger, "order.card_payment_amount_mismatch",
            restaurant_id=order.restaurant_id, order_id=order.id, payment_id=payment_id,
            expected_smallest_unit=expected_smallest_unit, reached_amount=state.reached_amount,
        )
        return "error"

    # Mise à jour gardée par `payment_ref` (pas par id seul) : c'est la garde
    # d'idempotence — un règlement concurrent pour la MÊME référence ne peut
    # jamais s'appliquer deux fois.
    updated = (
        db.query(OrderPayment)
        .filter(OrderPayment.id == payment.id, OrderPayment.payment_ref == payment_ref)
        .update({"status": OrderPaymentStatus.PAID, "paid_at": datetime.now(timezone.utc)})
    )
    db.commit()

    log_event(
        logger, "order.card_payment_settled",
        restaurant_id=order.restaurant_id, order_id=order.id, payment_id=payment_id, already_settled=updated == 0,
    )

    if updated:
        fully_paid = _after_share_paid(db, order, restaurant)
        db.refresh(order)
        # Le client peut avoir sa page ouverte en attendant le webhook —
        # même événement que la confirmation d'un paiement en espèces.
        await manager.broadcast(
            order.restaurant_id, channel=_order_channel(order.id),
            message={"event": "order.payment_confirmed", "order_id": order.id, "fully_paid": fully_paid},
        )

    return "paid"


async def request_cash_payment(
    db: Session, order_id: int, payer_key: str, payer_name: str, tip_amount: float = 0,
    customer_email: str | None = None,
) -> Order:
    """Le client demande à payer sa part en espèces — prévient le serveur
    assigné (identité de table, ROADMAP.md §Override, extension paiement par
    personne : plusieurs demandes peuvent être en attente pour la même
    commande, une par convive)."""
    order, existing, amount = _get_payable_share(db, order_id, payer_key, payer_name)

    payment = existing or OrderPayment(order_id=order.id, payer_key=payer_key, payer_name=payer_name, method=PaymentMethod.CASH)
    payment.amount = amount
    # Le pourboire était ignoré sur ce chemin : le client le saisissait, le
    # serveur venait encaisser le total sans lui, et l'écart n'apparaissait
    # qu'au comptage de la caisse.
    payment.tip_amount = tip_amount
    payment.status = OrderPaymentStatus.PENDING
    if customer_email:
        payment.customer_email = customer_email
        order.customer_email = customer_email
    if not existing:
        db.add(payment)
    _mark_order_pending(db, order, payment)
    db.refresh(payment)

    a_encaisser = amount + tip_amount
    log_event(
        logger, "order.cash_payment_requested",
        restaurant_id=order.restaurant_id, order_id=order.id, payer_name=payer_name, amount=a_encaisser,
    )

    # Diffusé sur le canal "staff" partagé (pas d'infra par membre du
    # personnel), mais porte taken_by_staff_id : le frontend n'affiche la
    # demande qu'au serveur dédié à cette table (ou au manager, qui voit
    # tout). Toute commande qui en est là est forcément déjà confirmée, donc
    # taken_by_staff_id est garanti non-nul (auto-claim à la confirmation).
    await manager.broadcast(
        order.restaurant_id, channel="staff",
        message={
            "event": "order.cash_requested",
            "order_id": order.id,
            "payment_id": payment.id,
            "table_id": order.table_id,
            "table_label": order.table_label,
            "payer_name": payer_name,
            # Ce que le serveur doit réellement encaisser pour CETTE
            # personne, pourboire compris.
            "amount": a_encaisser,
            "taken_by_staff_id": order.taken_by_staff_id,
            "loyalty_phone": order.loyalty_phone,
        },
    )
    # Les AUTRES appareils qui suivent cette commande doivent voir la demande
    # de paiement sans rafraîchir.
    await manager.broadcast(
        order.restaurant_id, channel=_order_channel(order.id),
        message={"event": "order.payment_requested", "order_id": order.id},
    )
    return order


async def confirm_cash_payment(db: Session, payment_id: int, staff: Staff) -> Order:
    """Le serveur confirme avoir encaissé la part en espèces de CE convive."""
    payment = db.get(OrderPayment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "order not found"})
    order = db.get(Order, payment.order_id)
    if not order or order.restaurant_id != staff.restaurant_id:
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "order not found"})
    if payment.method != PaymentMethod.CASH or payment.status != OrderPaymentStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail={"code": "NO_PENDING_CASH_PAYMENT", "message": "no pending cash payment for this share"},
        )

    payment.status = OrderPaymentStatus.PAID
    payment.paid_at = datetime.now(timezone.utc)
    db.commit()

    log_event(
        logger, "order.cash_payment_confirmed",
        restaurant_id=order.restaurant_id, order_id=order.id, payment_id=payment.id, staff_id=staff.id,
    )
    fully_paid = _after_share_paid(db, order, db.get(Restaurant, order.restaurant_id))
    db.refresh(order)

    # Le client qui a demandé à payer en espèces peut avoir sa page ouverte
    # en attendant que le serveur passe encaisser.
    await manager.broadcast(
        order.restaurant_id, channel=_order_channel(order.id),
        message={"event": "order.payment_confirmed", "order_id": order.id, "fully_paid": fully_paid},
    )
    return order


async def request_card_terminal_payment(
    db: Session, order_id: int, payer_key: str, payer_name: str, tip_amount: float = 0,
    customer_email: str | None = None,
) -> Order:
    """
    Le client demande à payer sa part par carte physique — un serveur
    apporte le terminal. Même mécanique que le paiement en espèces (carte
    physique / en ligne / espèces, 2026-08-19), moyen distinct pour ne pas
    mélanger les deux dans les stats de moyen de paiement.
    """
    order, existing, amount = _get_payable_share(db, order_id, payer_key, payer_name)

    payment = existing or OrderPayment(
        order_id=order.id, payer_key=payer_key, payer_name=payer_name, method=PaymentMethod.CARD_TERMINAL
    )
    payment.amount = amount
    payment.tip_amount = tip_amount
    payment.status = OrderPaymentStatus.PENDING
    if customer_email:
        payment.customer_email = customer_email
        order.customer_email = customer_email
    if not existing:
        db.add(payment)
    _mark_order_pending(db, order, payment)
    db.refresh(payment)

    a_encaisser = amount + tip_amount
    log_event(
        logger, "order.card_terminal_payment_requested",
        restaurant_id=order.restaurant_id, order_id=order.id, payer_name=payer_name, amount=a_encaisser,
    )

    await manager.broadcast(
        order.restaurant_id, channel="staff",
        message={
            "event": "order.card_terminal_requested",
            "order_id": order.id,
            "payment_id": payment.id,
            "table_id": order.table_id,
            "table_label": order.table_label,
            "payer_name": payer_name,
            "amount": a_encaisser,
            "taken_by_staff_id": order.taken_by_staff_id,
            "loyalty_phone": order.loyalty_phone,
        },
    )
    # Même raison que `request_cash_payment` : les autres appareils de la
    # table doivent voir la demande sans rafraîchir.
    await manager.broadcast(
        order.restaurant_id, channel=_order_channel(order.id),
        message={"event": "order.payment_requested", "order_id": order.id},
    )
    return order


async def confirm_card_terminal_payment(db: Session, payment_id: int, staff: Staff) -> Order:
    """Le serveur confirme avoir encaissé la carte physique de CE convive."""
    payment = db.get(OrderPayment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "order not found"})
    order = db.get(Order, payment.order_id)
    if not order or order.restaurant_id != staff.restaurant_id:
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "order not found"})
    if payment.method != PaymentMethod.CARD_TERMINAL or payment.status != OrderPaymentStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "NO_PENDING_CARD_TERMINAL_PAYMENT",
                "message": "no pending card terminal payment for this share",
            },
        )

    payment.status = OrderPaymentStatus.PAID
    payment.paid_at = datetime.now(timezone.utc)
    db.commit()

    log_event(
        logger, "order.card_terminal_payment_confirmed",
        restaurant_id=order.restaurant_id, order_id=order.id, payment_id=payment.id, staff_id=staff.id,
    )
    fully_paid = _after_share_paid(db, order, db.get(Restaurant, order.restaurant_id))
    db.refresh(order)

    await manager.broadcast(
        order.restaurant_id, channel=_order_channel(order.id),
        message={"event": "order.payment_confirmed", "order_id": order.id, "fully_paid": fully_paid},
    )
    return order
