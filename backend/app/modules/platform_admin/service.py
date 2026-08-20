from datetime import date as date_type
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.dates import as_utc
from app.modules.orders.models import Order, OrderStatus, PaymentStatus
from app.modules.platform_admin import schemas
from app.modules.tenants.models import Restaurant, SubscriptionTier

# Trois mois de tendance : assez pour montrer un rythme d'expansion, pas
# assez pour qu'un graphique en barres devienne illisible sur mobile.
_WEEKS_IN_TREND = 12


def _is_paid(order: Order) -> bool:
    """Même définition que `stats/service.py::_paid_orders` : réglée pour de
    vrai (carte aboutie ou espèces confirmées par le serveur), pas seulement
    "pas annulée" — sinon la recette affichée compte des commandes que
    personne n'a payées."""
    return order.payment_status == PaymentStatus.PAID and order.status != OrderStatus.CANCELLED


def _week_start(value: datetime) -> date_type:
    d = as_utc(value).date()
    return d - timedelta(days=d.weekday())


def _weekly_series(
    restaurants: list[Restaurant], orders: list[Order], now: datetime
) -> list[schemas.WeeklyPoint]:
    current_week = _week_start(now)
    weeks = [current_week - timedelta(weeks=i) for i in range(_WEEKS_IN_TREND - 1, -1, -1)]
    index = {week: i for i, week in enumerate(weeks)}
    points = [
        schemas.WeeklyPoint(week_start=week, restaurants_created=0, orders_count=0, revenue_tnd=0.0)
        for week in weeks
    ]

    for restaurant in restaurants:
        week = _week_start(restaurant.created_at)
        if week in index:
            points[index[week]].restaurants_created += 1

    for order in orders:
        week = _week_start(order.created_at)
        if week in index:
            point = points[index[week]]
            point.orders_count += 1
            if _is_paid(order):
                point.revenue_tnd += order.total_amount

    return points


async def get_overview(db: Session) -> schemas.PlatformOverview:
    """
    Chiffres clés tous restaurants confondus, pour l'opérateur de la
    plateforme — pas la vue d'un manager sur son seul établissement
    (`stats/service.py`). Échelle actuelle (quelques pilotes) : tout tient en
    mémoire sans agrégation SQL, comme le reste du module `stats`.
    """
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    restaurants = db.query(Restaurant).order_by(Restaurant.created_at).all()
    orders = db.query(Order).all()

    orders_by_restaurant: dict[int, list[Order]] = {}
    for order in orders:
        orders_by_restaurant.setdefault(order.restaurant_id, []).append(order)

    restaurants_by_tier = {tier.value: 0 for tier in SubscriptionTier}
    restaurant_summaries: list[schemas.RestaurantSummary] = []
    for restaurant in restaurants:
        restaurants_by_tier[restaurant.subscription_tier.value] += 1
        restaurant_orders = orders_by_restaurant.get(restaurant.id, [])
        paid_orders = [o for o in restaurant_orders if _is_paid(o)]
        last_order_at = max((o.created_at for o in restaurant_orders), default=None)
        restaurant_summaries.append(
            schemas.RestaurantSummary(
                id=restaurant.id,
                name=restaurant.name,
                slug=restaurant.slug,
                subscription_tier=restaurant.subscription_tier,
                created_at=restaurant.created_at,
                orders_count=len(restaurant_orders),
                revenue_tnd=sum(o.total_amount for o in paid_orders),
                last_order_at=last_order_at,
            )
        )
    # Le plus actif d'abord : la question posée en ouvrant cet écran est "qui
    # utilise vraiment l'outil", pas "qui s'est inscrit en premier".
    restaurant_summaries.sort(key=lambda r: r.orders_count, reverse=True)

    orders_last_30d = [o for o in orders if as_utc(o.created_at) >= thirty_days_ago]
    all_paid = [o for o in orders if _is_paid(o)]
    paid_last_30d = [o for o in orders_last_30d if _is_paid(o)]

    return schemas.PlatformOverview(
        generated_at=now,
        restaurants_total=len(restaurants),
        restaurants_by_tier=restaurants_by_tier,
        restaurants_created_last_30d=sum(1 for r in restaurants if as_utc(r.created_at) >= thirty_days_ago),
        orders_total=len(orders),
        orders_last_30d=len(orders_last_30d),
        revenue_total_tnd=sum(o.total_amount for o in all_paid),
        revenue_last_30d_tnd=sum(o.total_amount for o in paid_last_30d),
        weekly=_weekly_series(restaurants, orders, now),
        restaurants=restaurant_summaries,
    )
