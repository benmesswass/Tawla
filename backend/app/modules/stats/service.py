from datetime import date as date_type
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session, selectinload

from app.core.dates import as_utc, service_day_bounds, service_day_start
from app.modules.orders.models import Order, OrderStatus, PaymentStatus
from app.modules.orders.service import ABANDONED_PENDING_AFTER, ACTIVE_STATUSES
from app.modules.staff.models import Staff
from app.modules.stats import schemas
from app.modules.stats.models import DashboardView

# Pas de config timezone par resto pour l'instant (MVP mono-pays) — décalage
# fixe Tunisie (UTC+1, pas d'heure d'été) uniquement pour l'affichage des
# heures de pointe. Les bornes de journée, elles, restent en UTC pour rester
# cohérentes avec le reste du code (created_at etc.) — un léger décalage sur
# les commandes proches de minuit est un compromis assumé (YAGNI).
TUNISIA_UTC_OFFSET_HOURS = 1


def lost_orders(orders: list[Order], now: datetime) -> list[Order]:
    """
    Définition unique de « commande perdue » : annulée, ou jamais prise en
    charge au-delà du seuil d'abandon.

    Partagée par le tableau de bord et la page de preuve d'un restaurant, et
    par le dashboard plateforme (`platform_admin/service.py`) pour son taux de
    commandes perdues tous restaurants confondus — jamais une redéfinition :
    un restaurant qui verrait un taux différent chez lui et sur l'agrégat de
    Wassim cesserait de croire l'un des deux.
    """
    abandoned_before = now - ABANDONED_PENDING_AFTER
    return [
        o
        for o in orders
        if o.status == OrderStatus.CANCELLED
        or (o.status == OrderStatus.PENDING_CONFIRMATION and as_utc(o.created_at) < abandoned_before)
    ]


def paid_orders(orders: list[Order]) -> list[Order]:
    """
    Commandes qui comptent dans la recette : celles **réellement réglées** —
    paiement carte abouti, ou espèces confirmées par le serveur. Même ensemble
    que celui dont la page de preuve tire le panier moyen, et que le dashboard
    plateforme (`platform_admin/service.py`) utilise pour le GMV et le MRR.

    Longtemps c'était « tout sauf les annulées », et la recette additionnait
    donc des commandes que personne n'avait payées : le patron lisait chaque
    soir un chiffre plus haut que sa caisse. Constaté au premier service.

    Contrepartie assumée : le chiffre dépend désormais du personnel qui
    enregistre l'encaissement. Un service où l'on oublie de confirmer le cash
    sous-évaluera la recette — mais sous-évaluer ce qu'on ne peut pas prouver
    vaut mieux que gonfler ce qu'on montre au patron.
    """
    return [
        o
        for o in orders
        if o.payment_status == PaymentStatus.PAID and o.status != OrderStatus.CANCELLED
    ]


def _average(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


async def get_dashboard_stats(db: Session, restaurant_id: int, day: date_type) -> schemas.DashboardStats:
    # Instrumentation de rétention (ROADMAP.md Phase 24, voir stats/models.py)
    # — une ligne par appel, donc par ouverture de /dashboard ou
    # /dashboard/stats. Écrite en premier et indépendamment du reste : un
    # signal d'usage ne doit jamais dépendre du succès du calcul de stats.
    db.add(DashboardView(restaurant_id=restaurant_id))
    db.commit()

    # Bornée par la journée de service (5h Tunis, Phase 19.5), pas par minuit
    # UTC : sinon une commande de sohour (2h Tunis) apparaît sous un jour
    # différent ici et sur les écrans de service (F-3, audit 2026-08-18).
    day_start, day_end = service_day_bounds(day)

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
        db.query(Order)
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.status.in_(ACTIVE_STATUSES),
            # Même borne que `list_active_orders` (Phase 19.5) : sans elle, ce
            # nombre reste au-dessus de zéro indéfiniment tant qu'une commande
            # de la veille n'a jamais été confirmée ni annulée, alors que
            # l'écran serveur a cessé de la montrer (F-2, audit 2026-08-18).
            Order.created_at >= service_day_start(),
        )
        .count()
    )

    # Les deux chiffres que le patron vient chercher (Phase 17.1). Calculés
    # avec les mêmes règles que la page de preuve : les deux écrans parlent du
    # même jour au même homme, ils doivent dire la même chose.
    now = datetime.now(timezone.utc)
    revenue_today = sum(o.total_amount for o in paid_orders(orders_today))
    lost_orders_today = len(lost_orders(orders_today, now))

    return schemas.DashboardStats(
        date=day,
        revenue_today=revenue_today,
        lost_orders_today=lost_orders_today,
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
    # Même bornage par journée de service que get_dashboard_stats (F-3) :
    # le début de la période suit le début du jour `start`, sa fin suit la
    # fin du jour `end` — jours inclus des deux côtés.
    period_start = service_day_bounds(start)[0]
    period_end = service_day_bounds(end)[1]

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

    lost = lost_orders(orders, now)
    cancelled = [o for o in lost if o.status == OrderStatus.CANCELLED]
    abandoned = [o for o in lost if o.status != OrderStatus.CANCELLED]

    order_to_kitchen = [
        (o.sent_to_kitchen_at - o.created_at).total_seconds() for o in orders if o.sent_to_kitchen_at
    ]
    restaurant_paid_orders = paid_orders(orders)
    baskets = [o.total_amount for o in restaurant_paid_orders]

    # Une commande « avec suggestion » est une commande où le client a accepté
    # au moins une proposition. Comparer ces paniers aux autres est la seule
    # façon d'attribuer une hausse à la vente incitative plutôt qu'à une table
    # plus nombreuse.
    with_suggestion = [o for o in restaurant_paid_orders if any(line.from_suggestion for line in o.items)]
    boosted_ids = {o.id for o in with_suggestion}
    without_suggestion = [o for o in restaurant_paid_orders if o.id not in boosted_ids]

    return schemas.PeriodProof(
        start=start,
        end=end,
        orders_count=len(orders),
        lost_orders_count=len(lost),
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
    # Même bornage par journée de service que get_dashboard_stats (F-3) :
    # le début de la période suit le début du jour `start`, sa fin suit la
    # fin du jour `end` — jours inclus des deux côtés.
    period_start = service_day_bounds(start)[0]
    period_end = service_day_bounds(end)[1]

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
    # Bornée par la journée de service (5h Tunis, Phase 19.5), pas par minuit
    # UTC : sinon une commande de sohour (2h Tunis) apparaît sous un jour
    # différent ici et sur les écrans de service (F-3, audit 2026-08-18).
    day_start, day_end = service_day_bounds(day)

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


async def get_my_shift(db: Session, staff: Staff, day: date_type) -> schemas.MyShift:
    """
    La soirée du membre d'équipe connecté (Phase 17.3).

    Le staff vient du JWT, jamais de l'URL : il n'y a donc aucun identifiant à
    deviner, et personne ne peut demander la soirée d'un autre.
    """
    # Bornée par la journée de service (5h Tunis, Phase 19.5), pas par minuit
    # UTC : sinon une commande de sohour (2h Tunis) apparaît sous un jour
    # différent ici et sur les écrans de service (F-3, audit 2026-08-18).
    day_start, day_end = service_day_bounds(day)

    orders = (
        db.query(Order)
        .options(selectinload(Order.items))
        .filter(
            Order.restaurant_id == staff.restaurant_id,
            Order.taken_by_staff_id == staff.id,
            Order.created_at >= day_start,
            Order.created_at < day_end,
            Order.status != OrderStatus.CANCELLED,
        )
        .all()
    )

    delays = [
        (as_utc(o.taken_at) - as_utc(o.created_at)).total_seconds() for o in orders if o.taken_at
    ]
    return schemas.MyShift(
        date=day,
        orders_taken=len(orders),
        total_amount_handled=sum(o.total_amount for o in orders),
        avg_seconds_to_claim=_average(delays),
    )
