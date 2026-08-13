from datetime import date as date_type
from datetime import datetime, time, timedelta, timezone

from sqlalchemy.orm import Session, selectinload

from app.core.dates import as_utc
from app.modules.orders.models import Order, OrderStatus
from app.modules.orders.service import ABANDONED_PENDING_AFTER, ACTIVE_STATUSES
from app.modules.staff.models import Staff
from app.modules.stats import schemas

# Pas de config timezone par resto pour l'instant (MVP mono-pays) — décalage
# fixe Tunisie (UTC+1, pas d'heure d'été) uniquement pour l'affichage des
# heures de pointe. Les bornes de journée, elles, restent en UTC pour rester
# cohérentes avec le reste du code (created_at etc.) — un léger décalage sur
# les commandes proches de minuit est un compromis assumé (YAGNI).
TUNISIA_UTC_OFFSET_HOURS = 1


def _average(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


async def get_dashboard_stats(db: Session, restaurant_id: int, day: date_type) -> schemas.DashboardStats:
    day_start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    orders_today = (
        db.query(Order)
        .options(selectinload(Order.items))
        .filter(Order.restaurant_id == restaurant_id, Order.created_at >= day_start, Order.created_at < day_end)
        .all()
    )

    wait_confirmation = [(o.confirmed_at - o.created_at).total_seconds() for o in orders_today if o.confirmed_at]
    confirmation_to_kitchen = [
        (o.sent_to_kitchen_at - o.confirmed_at).total_seconds()
        for o in orders_today
        if o.confirmed_at and o.sent_to_kitchen_at
    ]
    kitchen_to_served = [
        (o.served_at - o.sent_to_kitchen_at).total_seconds()
        for o in orders_today
        if o.sent_to_kitchen_at and o.served_at
    ]

    timing = schemas.TimingStats(
        avg_wait_confirmation_seconds=_average(wait_confirmation),
        avg_confirmation_to_kitchen_seconds=_average(confirmation_to_kitchen),
        avg_kitchen_to_served_seconds=_average(kitchen_to_served),
    )

    staff_counts: dict[int, int] = {}
    for o in orders_today:
        if o.taken_by_staff_id is not None:
            staff_counts[o.taken_by_staff_id] = staff_counts.get(o.taken_by_staff_id, 0) + 1

    staff_performance: list[schemas.StaffPerformance] = []
    if staff_counts:
        staff_rows = db.query(Staff).filter(Staff.id.in_(staff_counts.keys())).all()
        staff_by_id = {s.id: s for s in staff_rows}
        for staff_id, count in sorted(staff_counts.items(), key=lambda kv: -kv[1]):
            s = staff_by_id.get(staff_id)
            if s:
                staff_performance.append(
                    schemas.StaffPerformance(staff_id=s.id, staff_name=s.name, role=s.role, orders_taken=count)
                )

    item_counts: dict[str, int] = {}
    for o in orders_today:
        for line in o.items:
            item_counts[line.menu_item_name] = item_counts.get(line.menu_item_name, 0) + line.quantity
    top_items = [
        schemas.TopMenuItem(menu_item_name=name, quantity=qty)
        for name, qty in sorted(item_counts.items(), key=lambda kv: -kv[1])[:10]
    ]

    hour_counts: dict[int, int] = {}
    for o in orders_today:
        local_hour = (o.created_at + timedelta(hours=TUNISIA_UTC_OFFSET_HOURS)).hour
        hour_counts[local_hour] = hour_counts.get(local_hour, 0) + 1
    orders_by_hour = [schemas.HourlyCount(hour=h, count=hour_counts[h]) for h in sorted(hour_counts)]

    active_orders_count = (
        db.query(Order).filter(Order.restaurant_id == restaurant_id, Order.status.in_(ACTIVE_STATUSES)).count()
    )

    return schemas.DashboardStats(
        date=day,
        active_orders_count=active_orders_count,
        timing=timing,
        staff_performance=staff_performance,
        top_items=top_items,
        orders_by_hour=orders_by_hour,
    )


def _period_proof(
    db: Session, restaurant_id: int, start: date_type, end: date_type, now: datetime
) -> schemas.PeriodProof:
    """
    Calcule les trois chiffres de preuve sur une période bornée (jours inclus).

    `now` est passé en paramètre plutôt que lu ici : la période précédente et la
    période courante doivent être évaluées avec la même référence temporelle,
    sinon le seuil d'abandon ne veut pas dire la même chose des deux côtés de la
    comparaison.
    """
    period_start = datetime.combine(start, time.min, tzinfo=timezone.utc)
    period_end = datetime.combine(end, time.min, tzinfo=timezone.utc) + timedelta(days=1)

    orders = (
        db.query(Order)
        .options(selectinload(Order.items))
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.created_at >= period_start,
            Order.created_at < period_end,
        )
        .all()
    )

    abandoned_before = now - ABANDONED_PENDING_AFTER
    cancelled = [o for o in orders if o.status == OrderStatus.CANCELLED]
    abandoned = [
        o
        for o in orders
        if o.status == OrderStatus.PENDING_CONFIRMATION and as_utc(o.created_at) < abandoned_before
    ]

    order_to_kitchen = [
        (o.sent_to_kitchen_at - o.created_at).total_seconds() for o in orders if o.sent_to_kitchen_at
    ]
    paid_orders = [o for o in orders if o.status != OrderStatus.CANCELLED]
    baskets = [o.total_amount for o in paid_orders]

    # Une commande « avec suggestion » est une commande où le client a accepté
    # au moins une proposition. Comparer ces paniers aux autres est la seule
    # façon d'attribuer une hausse à la vente incitative plutôt qu'à une table
    # plus nombreuse.
    with_suggestion = [o for o in paid_orders if any(line.from_suggestion for line in o.items)]
    boosted_ids = {o.id for o in with_suggestion}
    without_suggestion = [o for o in paid_orders if o.id not in boosted_ids]

    return schemas.PeriodProof(
        start=start,
        end=end,
        orders_count=len(orders),
        lost_orders_count=len(cancelled) + len(abandoned),
        cancelled_count=len(cancelled),
        abandoned_count=len(abandoned),
        avg_order_to_kitchen_seconds=_average(order_to_kitchen),
        avg_basket_amount=_average(baskets),
        orders_with_suggestion_count=len(with_suggestion),
        avg_basket_with_suggestion=_average([o.total_amount for o in with_suggestion]),
        avg_basket_without_suggestion=_average([o.total_amount for o in without_suggestion]),
    )


async def get_proof_stats(
    db: Session, restaurant_id: int, start: date_type, end: date_type
) -> schemas.ProofStats:
    """
    Période demandée + période de même longueur juste avant. C'est cette
    comparaison, et pas les chiffres bruts, qui se montre à un patron à la fin
    d'un pilote (Phase 13.3).
    """
    now = datetime.now(timezone.utc)
    span_days = (end - start).days + 1
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=span_days - 1)

    return schemas.ProofStats(
        current=_period_proof(db, restaurant_id, start, end, now),
        previous=_period_proof(db, restaurant_id, previous_start, previous_end, now),
    )


async def get_team_report(
    db: Session, restaurant_id: int, start: date_type, end: date_type
) -> schemas.TeamReport:
    """
    Activité de chaque membre de l'équipe sur une période — la base des primes
    de rendement (Phase 14.2).

    Les comptes désactivés qui ont travaillé sur la période restent listés : un
    serveur parti en milieu de mois a droit à sa prime.
    """
    period_start = datetime.combine(start, time.min, tzinfo=timezone.utc)
    period_end = datetime.combine(end, time.min, tzinfo=timezone.utc) + timedelta(days=1)

    orders = (
        db.query(Order)
        .options(selectinload(Order.items))
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.taken_by_staff_id.isnot(None),
            Order.created_at >= period_start,
            Order.created_at < period_end,
            Order.status != OrderStatus.CANCELLED,
        )
        .all()
    )

    by_staff: dict[int, list[Order]] = {}
    for order in orders:
        by_staff.setdefault(order.taken_by_staff_id, []).append(order)

    if not by_staff:
        return schemas.TeamReport(start=start, end=end, staff=[])

    staff_by_id = {s.id: s for s in db.query(Staff).filter(Staff.id.in_(by_staff)).all()}

    rows: list[schemas.StaffPeriodReport] = []
    for staff_id, staff_orders in by_staff.items():
        member = staff_by_id.get(staff_id)
        if not member:
            continue
        delays = [
            (as_utc(o.taken_at) - as_utc(o.created_at)).total_seconds()
            for o in staff_orders
            if o.taken_at
        ]
        rows.append(
            schemas.StaffPeriodReport(
                staff_id=member.id,
                staff_name=member.name,
                role=member.role,
                orders_taken=len(staff_orders),
                avg_seconds_to_claim=_average(delays),
                total_amount_handled=sum(o.total_amount for o in staff_orders),
            )
        )

    rows.sort(key=lambda row: -row.orders_taken)
    return schemas.TeamReport(start=start, end=end, staff=rows)


async def get_kitchen_today_count(db: Session, restaurant_id: int, day: date_type) -> schemas.KitchenTodayCount:
    day_start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    count = (
        db.query(Order)
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.sent_to_kitchen_at.isnot(None),
            Order.sent_to_kitchen_at >= day_start,
            Order.sent_to_kitchen_at < day_end,
        )
        .count()
    )

    return schemas.KitchenTodayCount(date=day, count=count)
