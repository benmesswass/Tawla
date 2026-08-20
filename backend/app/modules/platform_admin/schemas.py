from datetime import date as date_type

from pydantic import BaseModel, ConfigDict

from app.core.dates import UtcDatetime
from app.modules.tenants.models import SubscriptionTier


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class PlatformAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    is_active: bool


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: PlatformAdminOut


class RestaurantSummary(BaseModel):
    """Une ligne par restaurant client — de quoi voir en un coup d'œil lequel
    est réellement utilisé, pas seulement inscrit ou payant."""

    id: int
    name: str
    slug: str
    # Palier réellement actif (`effective_tier()`), jamais `subscription_tier`
    # brut : sinon un palier payé en ligne et expiré depuis longtemps
    # continuerait d'apparaître comme Pro/Business ici.
    effective_tier: SubscriptionTier
    created_at: UtcDatetime
    orders_count: int
    revenue_tnd: float
    last_order_at: UtcDatetime | None
    # Signal de rétention par établissement (Phase 24 de ROADMAP.md) : un
    # restaurant sans ouverture récente est un restaurant qui décroche, même
    # si sa recette du mois dernier avait l'air bonne.
    dashboard_views_last_7d: int


class WeeklyPoint(BaseModel):
    week_start: date_type
    restaurants_created: int


class PlatformOverview(BaseModel):
    """
    Les chiffres indispensables de l'opérateur, tous restaurants confondus —
    même discipline que `PeriodProof` : volontairement pas un chiffre de plus
    que ce que la spec liste. Jamais la vue d'un manager sur son restaurant
    (`stats/schemas.py::DashboardStats`), toujours l'agrégat plateforme.
    """

    generated_at: UtcDatetime

    # 1. Expansion — la seule vraie mesure.
    restaurants_total: int
    restaurants_created_last_30d: int

    # 2. Montée en gamme — palier réellement actif, pas la colonne brute.
    restaurants_by_tier: dict[str, int]

    # 3. MRR réel — paliers payés en ligne et toujours actifs uniquement,
    # jamais les pilotes fixés à la main (voir service.py::_is_paying_online).
    # Un MRR qui compterait les pilotes gratuits mentirait à Wassim sur son
    # propre chiffre d'affaires.
    mrr_tnd: float
    paying_restaurants_count: int

    # 4. Rétention — le signal qui précède une résiliation, cf. ROADMAP.md
    # Phase 24. `restaurants_active_last_7d` = combien de restaurants ont eu
    # au moins une ouverture, pas juste le volume brut.
    dashboard_views_last_7d: int
    restaurants_active_last_7d: int

    # 5. Volume réel qui passe par l'outil, 7 derniers jours.
    orders_last_7d: int
    gmv_last_7d_tnd: float

    # 6. Qualité de service plateforme — même définition que chaque resto
    # voit déjà chez lui (`stats/service.py::lost_orders`), jamais une
    # redéfinition. `None` = aucune commande sur la période, pas 0%.
    lost_orders_rate_last_7d: float | None

    weekly_signups: list[WeeklyPoint]
    restaurants: list[RestaurantSummary]
