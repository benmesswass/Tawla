from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.dates import service_day_start
from app.core.email import is_email_enabled, send_email_with_attachment
from app.core.invoice import generate_invoice_pdf
from app.core.konnect import (
    KonnectError,
    get_konnect_payment,
    init_konnect_payment,
    is_konnect_enabled,
    sign_konnect_order_webhook,
    tnd_to_millimes,
)
from app.core.logging import get_logger, log_event
from app.core.markets import format_amount
from app.core.push import send_push_notification
from app.core.subscription import effective_tier, tier_includes, upgrade_required_error
from app.modules.loyalty import service as loyalty_service
from app.modules.menu.models import MenuFormula, MenuItem
from app.modules.notifications.manager import manager
from app.modules.orders import schemas
from app.modules.orders.models import (
    Order,
    OrderFormula,
    OrderFormulaSelection,
    OrderItem,
    OrderItemOptionChoice,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.modules.staff.models import Staff
from app.modules.tables import service as tables_service
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

# Au-delà de ce délai, une commande encore en attente de confirmation est
# considérée comme perdue : personne ne l'a prise en charge. C'est la moitié de
# la définition de « commande perdue » utilisée par la page de preuve
# (`stats/service.py::get_proof_stats`), l'autre moitié étant les annulations.
#
# Dix minutes est une proposition, pas une vérité : c'est le seuil à confronter
# au premier restaurant pilote (Phase 13.3 de la ROADMAP). Un service de midi
# tendu peut légitimement mettre 5 minutes à prendre une commande ; au-delà de
# 10, le client a déjà relevé la tête pour chercher un serveur.
ABANDONED_PENDING_AFTER = timedelta(minutes=10)

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
        # service — une requête par commande n'y a pas sa place.
        .options(selectinload(Order.table))
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


async def list_pending_cash_payments(db: Session, restaurant_id: int) -> list[Order]:
    """
    Tables ayant demandé à payer en espèces mais pas encore encaissées. Séparé
    de `list_active_orders` : le paiement arrive souvent APRÈS "servie", donc
    hors de `ACTIVE_STATUSES` — sans cette requête dédiée, un écran serveur
    rafraîchi après la demande de paiement ne la verrait jamais (même classe
    de bug que l'audit du 2026-08-10 sur les commandes en attente).
    """
    return (
        db.query(Order)
        .options(selectinload(Order.table))
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.payment_method == PaymentMethod.CASH,
            Order.payment_status == PaymentStatus.PENDING,
            # Même borne que list_active_orders (Phase 19.5) : sans elle, une
            # demande d'encaissement vieille de plusieurs jours reste affichée
            # indéfiniment à l'écran serveur (F-4, audit 2026-08-18).
            Order.created_at >= service_day_start(),
        )
        .order_by(Order.created_at)
        .all()
    )


async def list_pending_card_terminal_payments(db: Session, restaurant_id: int) -> list[Order]:
    """Tables ayant demandé à payer par carte physique, pas encore encaissées
    — même principe que list_pending_cash_payments, moyen distinct."""
    return (
        db.query(Order)
        .options(selectinload(Order.table))
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.payment_method == PaymentMethod.CARD_TERMINAL,
            Order.payment_status == PaymentStatus.PENDING,
            Order.created_at >= service_day_start(),
        )
        .order_by(Order.created_at)
        .all()
    )


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


def _resolve_selected_options(
    menu_item: MenuItem, selected_choice_ids: list[int]
) -> tuple[list[OrderItemOptionChoice], float]:
    """
    F5-A2 (MARCHE_FRANCE.md) — revérifie intégralement les options choisies
    pour CET article, jamais confiance au client (CLAUDE.md) : appartenance à
    l'article, groupe requis satisfait, une seule valeur hors
    `allow_multiple`. Renvoie les lignes figées à écrire sur l'`OrderItem`
    (nom + supplément au moment T, voir `OrderItemOptionChoice`) et le
    supplément total à ajouter au prix unitaire.
    """
    choice_to_group = {choice.id: group for group in menu_item.option_groups for choice in group.choices}

    selected_by_group: dict[int, list[int]] = {}
    for choice_id in selected_choice_ids:
        group = choice_to_group.get(choice_id)
        if group is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "INVALID_OPTION_CHOICE",
                    "message": f"choice {choice_id} does not belong to item {menu_item.id}",
                },
            )
        selected_by_group.setdefault(group.id, []).append(choice_id)

    for group in menu_item.option_groups:
        chosen = selected_by_group.get(group.id, [])
        if group.is_required and not chosen:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "OPTION_GROUP_REQUIRED",
                    "message": f"'{group.name}' requires a choice",
                    "group_id": group.id,
                    "menu_item_id": menu_item.id,
                },
            )
        if not group.allow_multiple and len(chosen) > 1:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "OPTION_GROUP_SINGLE_CHOICE",
                    "message": f"'{group.name}' accepts only one choice",
                    "group_id": group.id,
                },
            )

    frozen: list[OrderItemOptionChoice] = []
    total_delta = 0.0
    for group in menu_item.option_groups:
        for choice in group.choices:
            if choice.id in selected_by_group.get(group.id, []):
                delta = float(choice.price_delta)
                total_delta += delta
                frozen.append(
                    OrderItemOptionChoice(
                        choice_id=choice.id, group_name=group.name, choice_name=choice.name, price_delta=delta
                    )
                )
    return frozen, total_delta


def _resolve_formula_selection(formula: MenuFormula, selected_item_ids: list[int]) -> list[OrderFormulaSelection]:
    """
    F5-A3 (MARCHE_FRANCE.md) — revérifie intégralement les choix de CETTE
    formule, jamais confiance au client (CLAUDE.md) : chaque article proposé
    doit appartenir à la formule, et chaque étape doit recevoir EXACTEMENT un
    choix (pas d'étape facultative dans cette première version — voir
    `MenuFormulaSlot`). Renvoie les lignes figées à écrire sur l'`OrderFormula`
    (étape + nom de l'article au moment T).
    """
    item_to_slot = {item.id: slot for slot in formula.slots for item in slot.items}

    selected_by_slot: dict[int, list[int]] = {}
    for item_id in selected_item_ids:
        slot = item_to_slot.get(item_id)
        if slot is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "INVALID_FORMULA_ITEM",
                    "message": f"item {item_id} is not part of formula {formula.id}",
                    "formula_id": formula.id,
                },
            )
        selected_by_slot.setdefault(slot.id, []).append(item_id)

    frozen: list[OrderFormulaSelection] = []
    for slot in formula.slots:
        chosen = selected_by_slot.get(slot.id, [])
        if len(chosen) != 1:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "FORMULA_SLOT_REQUIRES_ONE_CHOICE",
                    "message": f"'{slot.name}' requires exactly one choice",
                    "slot_id": slot.id,
                    "formula_id": formula.id,
                },
            )
        chosen_item = next(item for item in slot.items if item.id == chosen[0])
        frozen.append(
            OrderFormulaSelection(menu_item_id=chosen_item.id, slot_name=slot.name, menu_item_name=chosen_item.name)
        )
    return frozen


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

    if not payload.items and not payload.formulas:
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
    order = Order(
        restaurant_id=restaurant_id,
        table_id=table.id,
        scheduled_for=payload.scheduled_for,
        loyalty_phone=loyalty_phone,
        client_order_id=payload.client_order_id,
    )

    for line in payload.items:
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

        # F5-A2 : options choisies revérifiées entièrement côté serveur —
        # jamais le calcul de prix du client. `unit_price` inclut le
        # supplément, exactement comme une ligne de caisse (base + options).
        selected_options, options_delta = _resolve_selected_options(menu_item, line.selected_choice_ids)

        # Prix figé au moment T : voir commentaire dans models.py
        order.items.append(
            OrderItem(
                menu_item_id=menu_item.id,
                menu_item_name=menu_item.name,
                unit_price=float(menu_item.price) + options_delta,
                quantity=line.quantity,
                notes=line.notes,
                is_shared=line.is_shared,
                shared_with=",".join(str(p) for p in line.shared_with) or None,
                from_suggestion=line.from_suggestion,
                selected_options=selected_options,
            )
        )

    for formula_line in payload.formulas:
        formula = db.get(MenuFormula, formula_line.formula_id)
        if not formula or formula.restaurant_id != restaurant_id:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "FORMULA_NOT_FOUND",
                    "message": f"formula {formula_line.formula_id} not found",
                    "formula_id": formula_line.formula_id,
                },
            )
        if not formula.is_available:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "FORMULA_UNAVAILABLE",
                    "message": f"'{formula.name}' is no longer available",
                    "formula_id": formula.id,
                },
            )

        selections = _resolve_formula_selection(formula, formula_line.selected_item_ids)

        # Prix figé au moment T, TOUJOURS le prix fixe de la formule — jamais
        # la somme des articles choisis (voir MenuFormula.price).
        order.formulas.append(
            OrderFormula(
                formula_id=formula.id,
                formula_name=formula.name,
                unit_price=float(formula.price),
                quantity=formula_line.quantity,
                notes=formula_line.notes,
                is_shared=formula_line.is_shared,
                shared_with=",".join(str(p) for p in formula_line.shared_with) or None,
                selections=selections,
            )
        )

    db.add(order)
    db.commit()
    db.refresh(order)

    # Enregistre la fiche fidélité dès la commande si le client a saisi son
    # numéro (même s'il n'est jamais passé par une vérification de statut
    # séparée) — le compteur, lui, n'avance qu'au paiement confirmé.
    if order.loyalty_phone:
        loyalty_service.get_or_create_member(
            db, order.restaurant_id, order.loyalty_phone, payload.loyalty_birth_date
        )

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
    return order


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
    if new_status == OrderStatus.CANCELLED and order.payment_status == PaymentStatus.PAID:
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
                        # F5-A2 : sans ce champ, une commande arrivée en direct sur
                        # un écran cuisine déjà ouvert (le cas normal en service —
                        # `loadActiveOrders()` ne tourne qu'au montage/reconnexion,
                        # voir kitchen/page.tsx) affichait le plat sans ses options.
                        # Précalculé ici pour que le frontend n'ait qu'à le passer
                        # tel quel (`KitchenOrder.items.options`), sans dupliquer la
                        # logique de jointure déjà écrite pour la réponse REST.
                        "options": ", ".join(opt.choice_name for opt in i.selected_options) or None,
                    }
                    for i in order.items
                ]
                # F5-A3 : une formule part en cuisine comme un plat de plus —
                # son nom, et les articles choisis à chaque étape affichés là
                # où A2 affiche déjà les options (même case sur le ticket).
                + [
                    {
                        "name": f.formula_name,
                        "quantity": f.quantity,
                        "notes": f.notes,
                        "is_shared": f.is_shared,
                        "options": ", ".join(sel.menu_item_name for sel in f.selections) or None,
                    }
                    for f in order.formulas
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
    return order


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
        pdf_bytes = generate_invoice_pdf(order, restaurant.name)
        total = order.total_amount + float(order.tip_amount)
        sent = send_email_with_attachment(
            to=order.customer_email,
            subject=f"Votre facture - {restaurant.name}, commande #{order.id}",
            html_body=(
                f"<p>Bonjour,</p>"
                f"<p>Votre commande #{order.id} chez {restaurant.name} a bien été payée "
                f"({format_amount(total)}). Vous trouverez la facture détaillée en pièce jointe.</p>"
                f"<p>Merci de votre visite !</p>"
            ),
            attachment_filename=f"facture-commande-{order.id}.pdf",
            attachment_bytes=pdf_bytes,
        )
        log_event(logger, "order.payment_confirmation_email", order_id=order.id, sent=sent)
    except Exception as err:  # noqa: BLE001 — best-effort, voir docstring
        log_event(logger, "order.payment_confirmation_email_failed", order_id=order.id, error=str(err))


async def pay_by_card_simulated(db: Session, order_id: int, tip_amount: float, customer_email: str | None = None) -> Order:
    """
    Paiement carte — mode simulé (Konnect choisi comme prestataire, mais pas
    de vraie intégration tant qu'un pilote resto réel n'a pas de clés API).
    Couvre le prix total de la commande, pas juste des frais de service.
    Confirmation immédiate, comme le fallback simulé de Darna quand Konnect
    est désactivé — `payment_ref` reste vide ici, prêt à accueillir la
    référence Konnect le jour où l'intégration réelle remplace cette fonction.

    Réservé à Pro et Business (offre à trois paliers, 2026-08-18) : en
    Essentiel, seul l'encaissement en espèces est proposé.
    """
    order = _get_payable_order(db, order_id)

    restaurant = db.get(Restaurant, order.restaurant_id)
    if not restaurant or not tier_includes(effective_tier(restaurant), SubscriptionTier.PRO):
        raise upgrade_required_error(SubscriptionTier.PRO)

    order.payment_method = PaymentMethod.CARD
    order.tip_amount = tip_amount
    order.payment_status = PaymentStatus.PAID
    if customer_email:
        order.customer_email = customer_email
    db.commit()
    db.refresh(order)

    if order.loyalty_phone:
        loyalty_service.record_completed_order(db, order.restaurant_id, order.loyalty_phone)
    _send_payment_confirmation(order, restaurant)

    log_event(
        logger, "order.paid_card_simulated",
        restaurant_id=order.restaurant_id, order_id=order.id,
        amount=order.total_amount, tip_amount=tip_amount,
    )
    return order


async def start_card_payment(
    db: Session, order_id: int, tip_amount: float, customer_email: str | None = None
) -> tuple[Order, str | None]:
    """
    Paiement carte du client — modèle direct (connexion Konnect au paiement
    carte, 2026-08-19) : réglé chez LE RESTAURANT, jamais chez Tawla (dont le
    wallet ne sert qu'à son propre abonnement, voir subscription_payments.py).
    Retombe sur le mode démo (`pay_by_card_simulated`) tant que ce restaurant
    précis n'a pas connecté son propre wallet — dégradation gracieuse comme le
    reste de l'intégration Konnect.

    Renvoie `(order, pay_url)` : `pay_url` non-null seulement quand un
    règlement Konnect réel vient d'être initié — la commande reste alors
    `payment_status="pending"`, le client doit être redirigé pour payer.
    """
    order = _get_payable_order(db, order_id)

    restaurant = db.get(Restaurant, order.restaurant_id)
    if not restaurant or not tier_includes(effective_tier(restaurant), SubscriptionTier.PRO):
        raise upgrade_required_error(SubscriptionTier.PRO)

    credentials = restaurant.konnect_credentials()
    if not is_konnect_enabled() or not credentials:
        order = await pay_by_card_simulated(db, order_id, tip_amount, customer_email)
        return order, None

    api_key, wallet_id = credentials
    amount = order.total_amount + tip_amount
    qr_token = order.table.qr_token
    try:
        pay_url, payment_ref = init_konnect_payment(
            api_key=api_key,
            receiver_wallet_id=wallet_id,
            amount_tnd=amount,
            order_id=str(order.id),
            description=f"{order.table_label} — commande #{order.id}",
            webhook=(
                f"{settings.backend_url}/api/v1/orders/{order.id}/pay/card/webhook"
                f"?sig={sign_konnect_order_webhook(order.id)}"
            ),
            success_url=(
                f"{settings.frontend_url}/menu/{qr_token}"
                f"?konnect=success&order_id={order.id}&order_token={order.public_token}"
            ),
            fail_url=f"{settings.frontend_url}/menu/{qr_token}?konnect=fail",
            lifespan_minutes=30,
        )
    except KonnectError as err:
        log_event(
            logger, "order.card_payment_init_failed",
            restaurant_id=order.restaurant_id, order_id=order.id, error=str(err),
        )
        raise HTTPException(
            status_code=502, detail={"code": "PAYMENT_INIT_FAILED", "message": "could not start the payment"}
        ) from err

    order.payment_method = PaymentMethod.CARD
    order.payment_status = PaymentStatus.PENDING
    order.tip_amount = tip_amount
    order.payment_ref = payment_ref
    if customer_email:
        order.customer_email = customer_email
    db.commit()
    db.refresh(order)

    log_event(
        logger, "order.card_payment_initiated",
        restaurant_id=order.restaurant_id, order_id=order.id, payment_ref=payment_ref, amount=amount,
    )
    return order, pay_url


SettleCardResult = Literal["paid", "pending", "not_found", "error"]


async def settle_card_payment(db: Session, order_id: int) -> SettleCardResult:
    """
    Règle un paiement carte Konnect en attente — appelée par le webhook ET par
    le filet de sécurité `/pay/card/check`, même principe d'idempotence que
    `settle_subscription_payment` : gardée par `payment_ref`, jamais réglée
    deux fois pour la même référence.
    """
    order = db.get(Order, order_id)
    if not order:
        return "not_found"

    # Rien à régler : déjà réglé par un appel concurrent (webhook + retour
    # client arrivés en même temps), jamais initié, ou payé autrement.
    if order.payment_method != PaymentMethod.CARD or order.payment_status != PaymentStatus.PENDING:
        return "pending"
    payment_ref = order.payment_ref
    if not payment_ref:
        return "pending"

    restaurant = db.get(Restaurant, order.restaurant_id)
    credentials = restaurant.konnect_credentials() if restaurant else None
    if not credentials:
        # Konnect déconnecté par le manager entre l'initiation et le règlement
        # (rare) : rien à régler sans la clé, mais ne pas planter le webhook.
        log_event(
            logger, "order.card_payment_settle_missing_credentials",
            restaurant_id=order.restaurant_id, order_id=order.id,
        )
        return "error"
    api_key, _wallet_id = credentials

    try:
        payment = get_konnect_payment(payment_ref, api_key=api_key)
    except KonnectError as err:
        log_event(
            logger, "order.card_payment_settle_fetch_failed",
            restaurant_id=order.restaurant_id, order_id=order.id, error=str(err),
        )
        return "error"

    if payment.status != "completed":
        return "pending"

    # Contrôle d'intégrité : montant réellement reçu jamais inférieur au
    # total + pourboire figés à l'initiation — jamais un montant transmis par
    # le client ou par le webhook lui-même.
    expected_millimes = tnd_to_millimes(order.total_amount + float(order.tip_amount))
    if payment.reached_amount < expected_millimes:
        log_event(
            logger, "order.card_payment_amount_mismatch",
            restaurant_id=order.restaurant_id, order_id=order.id,
            expected_millimes=expected_millimes, reached_amount=payment.reached_amount,
        )
        return "error"

    # Mise à jour gardée par `payment_ref` (pas par id seul) : c'est la garde
    # d'idempotence — un règlement concurrent pour la MÊME référence ne peut
    # jamais s'appliquer deux fois.
    updated = (
        db.query(Order)
        .filter(Order.id == order.id, Order.payment_ref == payment_ref)
        .update({"payment_status": PaymentStatus.PAID})
    )
    db.commit()
    db.refresh(order)

    log_event(
        logger, "order.card_payment_settled",
        restaurant_id=order.restaurant_id, order_id=order.id, already_settled=updated == 0,
    )

    if updated:
        if order.loyalty_phone:
            loyalty_service.record_completed_order(db, order.restaurant_id, order.loyalty_phone)
        _send_payment_confirmation(order, restaurant)
        # Le client peut avoir sa page ouverte en attendant le webhook —
        # même événement que la confirmation d'un paiement en espèces.
        await manager.broadcast(
            order.restaurant_id, channel=_order_channel(order.id),
            message={"event": "order.payment_confirmed", "order_id": order.id},
        )

    return "paid"


async def request_cash_payment(
    db: Session, order_id: int, tip_amount: float = 0, customer_email: str | None = None
) -> Order:
    """Le client demande à payer en espèces — prévient le serveur assigné."""
    order = _get_payable_order(db, order_id)

    order.payment_method = PaymentMethod.CASH
    order.payment_status = PaymentStatus.PENDING
    # Le pourboire était ignoré sur ce chemin : le client le saisissait, le
    # serveur venait encaisser le total sans lui, et l'écart n'apparaissait
    # qu'au comptage de la caisse.
    order.tip_amount = tip_amount
    if customer_email:
        order.customer_email = customer_email
    db.commit()
    db.refresh(order)

    a_encaisser = order.total_amount + tip_amount
    log_event(
        logger, "order.cash_payment_requested",
        restaurant_id=order.restaurant_id, order_id=order.id, amount=a_encaisser,
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
            "table_id": order.table_id,
            "table_label": order.table_label,
            # Ce que le serveur doit réellement encaisser, pourboire compris —
            # c'est le montant qu'il annonce à la table.
            "amount": a_encaisser,
            "taken_by_staff_id": order.taken_by_staff_id,
            "loyalty_phone": order.loyalty_phone,
        },
    )
    return order


async def confirm_cash_payment(db: Session, order_id: int, staff: Staff) -> Order:
    """Le serveur confirme avoir encaissé le cash à table."""
    order = db.get(Order, order_id)
    if not order or order.restaurant_id != staff.restaurant_id:
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "order not found"})
    if order.payment_method != PaymentMethod.CASH or order.payment_status != PaymentStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail={"code": "NO_PENDING_CASH_PAYMENT", "message": "no pending cash payment for this order"},
        )

    order.payment_status = PaymentStatus.PAID
    db.commit()
    db.refresh(order)

    if order.loyalty_phone:
        loyalty_service.record_completed_order(db, order.restaurant_id, order.loyalty_phone)
    _send_payment_confirmation(order, db.get(Restaurant, order.restaurant_id))

    log_event(
        logger, "order.cash_payment_confirmed",
        restaurant_id=order.restaurant_id, order_id=order.id, staff_id=staff.id,
    )

    # Le client qui a demandé à payer en espèces peut avoir sa page ouverte
    # en attendant que le serveur passe encaisser.
    await manager.broadcast(
        order.restaurant_id, channel=_order_channel(order.id),
        message={"event": "order.payment_confirmed", "order_id": order.id},
    )
    return order


async def request_card_terminal_payment(
    db: Session, order_id: int, tip_amount: float = 0, customer_email: str | None = None
) -> Order:
    """
    Le client demande à payer par carte physique — un serveur apporte le
    terminal. Même mécanique que le paiement en espèces (carte physique / en
    ligne / espèces, 2026-08-19), moyen distinct pour ne pas mélanger les
    deux dans les stats de moyen de paiement.
    """
    order = _get_payable_order(db, order_id)

    order.payment_method = PaymentMethod.CARD_TERMINAL
    order.payment_status = PaymentStatus.PENDING
    order.tip_amount = tip_amount
    if customer_email:
        order.customer_email = customer_email
    db.commit()
    db.refresh(order)

    a_encaisser = order.total_amount + tip_amount
    log_event(
        logger, "order.card_terminal_payment_requested",
        restaurant_id=order.restaurant_id, order_id=order.id, amount=a_encaisser,
    )

    await manager.broadcast(
        order.restaurant_id, channel="staff",
        message={
            "event": "order.card_terminal_requested",
            "order_id": order.id,
            "table_id": order.table_id,
            "table_label": order.table_label,
            "amount": a_encaisser,
            "taken_by_staff_id": order.taken_by_staff_id,
            "loyalty_phone": order.loyalty_phone,
        },
    )
    return order


async def confirm_card_terminal_payment(db: Session, order_id: int, staff: Staff) -> Order:
    """Le serveur confirme avoir encaissé la carte physique à table."""
    order = db.get(Order, order_id)
    if not order or order.restaurant_id != staff.restaurant_id:
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "order not found"})
    if order.payment_method != PaymentMethod.CARD_TERMINAL or order.payment_status != PaymentStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "NO_PENDING_CARD_TERMINAL_PAYMENT",
                "message": "no pending card terminal payment for this order",
            },
        )

    order.payment_status = PaymentStatus.PAID
    db.commit()
    db.refresh(order)

    if order.loyalty_phone:
        loyalty_service.record_completed_order(db, order.restaurant_id, order.loyalty_phone)
    _send_payment_confirmation(order, db.get(Restaurant, order.restaurant_id))

    log_event(
        logger, "order.card_terminal_payment_confirmed",
        restaurant_id=order.restaurant_id, order_id=order.id, staff_id=staff.id,
    )

    await manager.broadcast(
        order.restaurant_id, channel=_order_channel(order.id),
        message={"event": "order.payment_confirmed", "order_id": order.id},
    )
    return order
