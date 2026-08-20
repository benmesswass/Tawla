from datetime import date as date_type

from pydantic import BaseModel

from app.core.dates import UtcDatetime
from app.modules.tenants.models import SubscriptionTier


class AdminLoginRequest(BaseModel):
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RestaurantSummary(BaseModel):
    """Une ligne par restaurant client — de quoi voir en un coup d'œil lequel
    est réellement utilisé, pas seulement inscrit."""

    id: int
    name: str
    slug: str
    subscription_tier: SubscriptionTier
    created_at: UtcDatetime
    orders_count: int
    revenue_tnd: float
    last_order_at: UtcDatetime | None


class WeeklyPoint(BaseModel):
    """Une semaine (lundi comme premier jour) — la tendance d'expansion,
    semaine par semaine, plutôt qu'un seul chiffre cumulé qui ne dit rien du
    rythme."""

    week_start: date_type
    restaurants_created: int
    orders_count: int
    revenue_tnd: float


class PlatformOverview(BaseModel):
    """
    Les chiffres clés de la plateforme, tous restaurants confondus — pas la
    vue d'un manager sur son établissement (`stats/service.py`), mais celle de
    l'opérateur sur l'ensemble des clients.
    """

    generated_at: UtcDatetime

    restaurants_total: int
    # Clé = valeur de `SubscriptionTier` (ex: "essentiel"), pas l'enum lui-même
    # — un restaurant qui n'existe encore sur aucun palier ne doit pas faire
    # planter la sérialisation d'une clé absente.
    restaurants_by_tier: dict[str, int]
    restaurants_created_last_30d: int

    orders_total: int
    orders_last_30d: int
    revenue_total_tnd: float
    revenue_last_30d_tnd: float

    weekly: list[WeeklyPoint]
    restaurants: list[RestaurantSummary]
