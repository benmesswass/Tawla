from pydantic import BaseModel, ConfigDict

from app.core.dates import UtcDatetime
from app.modules.tenants.models import SubscriptionTier


class AdminRestaurantOut(BaseModel):
    """
    Vue **admin** d'un restaurant — jamais servie ailleurs que sous
    `require_admin` (voir admin/router.py). `subscription_tier` est la valeur
    BRUTE en base, volontairement pas `effective_tier()` : Wassim doit voir
    ce qui est écrit, pas la projection qu'en fait le gating produit.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    created_at: UtcDatetime
    subscription_tier: SubscriptionTier
    subscription_period_end: UtcDatetime | None
    is_active: bool
    promo_gratuit: bool
    launch_promo_granted: bool
    has_paid_for_subscription: bool


class PromoUpdateIn(BaseModel):
    promo_gratuit: bool
