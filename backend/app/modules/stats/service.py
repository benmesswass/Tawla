from datetime import date as date_type
from datetime import datetime, time, timedelta, timezone

from sqlalchemy.orm import Session, selectinload

from app.modules.orders.models import Order
from app.modules.orders.service import ACTIVE_STATUSES
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
