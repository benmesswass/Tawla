from collections import defaultdict
from datetime import date as date_type
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.dates import as_utc
from app.core.markets import current_market
from app.core.subscription import effective_tier
from app.modules.orders.models import Order
from app.modules.platform_admin import schemas
from app.modules.stats.models import DashboardView
from app.modules.stats.service import lost_orders, paid_orders
from app.modules.tenants.models import Restaurant, SubscriptionTier

# Trois mois de tendance : assez pour montrer un rythme d'inscriptions, pas
# assez pour qu'un graphique en barres devienne illisible sur mobile.
_WEEKS_IN_TREND = 12


def _week_start(value: datetime) -> date_type:
    d = as_utc(value).date()
    return d - timedelta(days=d.weekday())


def _is_paying_online(restaurant: Restaurant, now: datetime) -> bool:
    """
    Palier payé en ligne et toujours actif — jamais un pilote fixé à la main
    par `setup_restaurant.py` (qui n'a pas d'échéance, voir
    `Restaurant.subscription_period_end`), NI un restaurant seulement actif
    via l'offre de lancement gratuite (2026-08-21, `has_paid_for_subscription`
    reste `False` tant qu'aucun vrai paiement n'a eu lieu — voir
    Restaurant.has_paid_for_subscription). Un MRR qui compterait les pilotes
    gratuits OU les bénéficiaires du mois gratuit mentirait à Wassim sur son
    propre chiffre d'affaires.

    Équivalent, pour les restaurants qui remplissent cette condition, à
    `effective_tier(restaurant) == restaurant.subscription_tier` : une
    échéance future ne fait jamais retomber le palier (voir subscription.py).
    """
    return (
        restaurant.has_paid_for_subscription
        and restaurant.subscription_period_end is not None
        and as_utc(restaurant.subscription_period_end) > now
    )


def _weekly_signups(restaurants: list[Restaurant], now: datetime) -> list[schemas.WeeklyPoint]:
    current_week = _week_start(now)
    weeks = [current_week - timedelta(weeks=i) for i in range(_WEEKS_IN_TREND - 1, -1, -1)]
    index = {week: i for i, week in enumerate(weeks)}
    counts = [0] * _WEEKS_IN_TREND

    for restaurant in restaurants:
        week = _week_start(restaurant.created_at)
        if week in index:
            counts[index[week]] += 1

    return [schemas.WeeklyPoint(week_start=week, restaurants_created=counts[i]) for i, week in enumerate(weeks)]


async def get_overview(db: Session) -> schemas.PlatformOverview:
    """
    Les chiffres indispensables de l'opérateur, tous restaurants confondus —
    échelle actuelle (quelques pilotes) : tout tient en mémoire sans
    agrégation SQL, comme le reste du module `stats`, jamais de job planifié.
    """
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    restaurants = db.query(Restaurant).order_by(Restaurant.created_at).all()
    orders = db.query(Order).all()
    recent_views = db.query(DashboardView).filter(DashboardView.viewed_at >= seven_days_ago).all()

    orders_by_restaurant: dict[int, list[Order]] = defaultdict(list)
    for order in orders:
        orders_by_restaurant[order.restaurant_id].append(order)

    views_by_restaurant: dict[int, int] = defaultdict(int)
    for view in recent_views:
        views_by_restaurant[view.restaurant_id] += 1

    restaurants_by_tier = {tier.value: 0 for tier in SubscriptionTier}
    # Nommé `_tnd` pour le déploiement tunisien d'aujourd'hui — le calcul lui
    # même vient déjà de current_market.tier_prices, donc juste dans la
    # devise du marché en service. Renommer ce champ (schemas.py, admin/
    # page.tsx) est un chantier séparé, à faire si un déploiement France
    # tourne un jour ce dashboard.
    mrr_tnd = 0.0
    paying_restaurants_count = 0
    restaurant_summaries: list[schemas.RestaurantSummary] = []

    for restaurant in restaurants:
        tier = effective_tier(restaurant)
        restaurants_by_tier[tier.value] += 1
        if _is_paying_online(restaurant, now):
            paying_restaurants_count += 1
            mrr_tnd += current_market.tier_prices.get(tier, 0)

        restaurant_orders = orders_by_restaurant.get(restaurant.id, [])
        restaurant_paid_orders = paid_orders(restaurant_orders)
        last_order_at = max((o.created_at for o in restaurant_orders), default=None)
        restaurant_summaries.append(
            schemas.RestaurantSummary(
                id=restaurant.id,
                name=restaurant.name,
                slug=restaurant.slug,
                effective_tier=tier,
                created_at=restaurant.created_at,
                orders_count=len(restaurant_orders),
                revenue_tnd=sum(o.total_amount for o in restaurant_paid_orders),
                last_order_at=last_order_at,
                dashboard_views_last_7d=views_by_restaurant.get(restaurant.id, 0),
                is_active=restaurant.is_active,
                custom_promo_discount_percent=restaurant.custom_promo_discount_percent,
                custom_promo_ends_at=restaurant.custom_promo_ends_at,
                launch_promo_discount_percent=restaurant.launch_promo_discount_percent,
                has_paid_for_subscription=restaurant.has_paid_for_subscription,
            )
        )
    # Le plus actif d'abord : la question posée en ouvrant cet écran est "qui
    # utilise vraiment l'outil", pas "qui s'est inscrit en premier".
    restaurant_summaries.sort(key=lambda r: r.orders_count, reverse=True)

    orders_last_7d = [o for o in orders if as_utc(o.created_at) >= seven_days_ago]
    gmv_last_7d = sum(o.total_amount for o in paid_orders(orders_last_7d))
    lost_last_7d = lost_orders(orders_last_7d, now)
    lost_rate_last_7d = (len(lost_last_7d) / len(orders_last_7d)) if orders_last_7d else None

    return schemas.PlatformOverview(
        generated_at=now,
        restaurants_total=len(restaurants),
        restaurants_created_last_30d=sum(1 for r in restaurants if as_utc(r.created_at) >= thirty_days_ago),
        restaurants_by_tier=restaurants_by_tier,
        mrr_tnd=mrr_tnd,
        paying_restaurants_count=paying_restaurants_count,
        dashboard_views_last_7d=len(recent_views),
        restaurants_active_last_7d=len(views_by_restaurant),
        orders_last_7d=len(orders_last_7d),
        gmv_last_7d_tnd=gmv_last_7d,
        lost_orders_rate_last_7d=lost_rate_last_7d,
        weekly_signups=_weekly_signups(restaurants, now),
        restaurants=restaurant_summaries,
    )
