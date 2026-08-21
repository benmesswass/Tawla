from datetime import date as date_type

from pydantic import BaseModel, ConfigDict, Field

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


class AdminCreateIn(BaseModel):
    """Voir platform_admin/router.py::create_admin — `secret` n'est vérifié
    que si la requête n'apporte aucun JWT admin valide ; laisser vide quand
    on est déjà connecté sur /admin (voir lib/platformAdmin.ts::createAdmin,
    qui envoie le JWT dans l'en-tête, jamais dans ce champ)."""

    secret: str = ""
    email: str
    name: str
    password: str = Field(min_length=8)


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
    # Activation et offre de lancement (2026-08-20/21) — de quoi voir d'un
    # coup d'œil qui est bloqué, qui bénéficie d'une promo personnalisée, et
    # qui n'a encore jamais payé pour de vrai (voir Restaurant.is_active/
    # custom_promo_discount_percent/launch_promo_discount_percent/
    # has_paid_for_subscription).
    is_active: bool
    custom_promo_discount_percent: int | None
    custom_promo_ends_at: UtcDatetime | None
    launch_promo_discount_percent: int | None
    has_paid_for_subscription: bool


class PromoUpdateIn(BaseModel):
    """`duration_days = 0` retire la promo en cours — voir
    platform_admin/router.py::set_restaurant_promo."""

    discount_percent: int = Field(ge=0, le=100)
    duration_days: int = Field(ge=0)


class PromoUpdateOut(BaseModel):
    custom_promo_discount_percent: int | None
    custom_promo_ends_at: UtcDatetime | None


class LaunchCampaignOut(BaseModel):
    """Réglages en cours de l'offre de lancement (2026-08-21) — voir
    Restaurant.launch_promo_discount_percent et core/subscription.py::
    get_launch_campaign. `grants_used` : combien de places déjà prises,
    visible seulement ici (jamais sur l'endpoint public /auth/launch-promo,
    qui ne renvoie qu'un booléen de disponibilité)."""

    discount_percent: int
    max_grants: int
    grants_used: int


class LaunchCampaignUpdate(BaseModel):
    discount_percent: int = Field(ge=0, le=100)
    max_grants: int = Field(ge=0)


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
