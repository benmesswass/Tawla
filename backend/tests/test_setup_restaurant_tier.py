"""
Le palier vendu à un pilote est celui saisi dans le fichier de configuration
de `scripts/setup_restaurant.py` — il n'existe pas d'autre porte d'entrée
(offre à trois paliers, 2026-08-18) : aucun portail self-service, la
facturation reste manuelle.
"""
from scripts.setup_restaurant import upsert_restaurant

from app.modules.tenants.models import SubscriptionTier


def test_a_new_pilot_is_created_with_the_sold_tier(db_session):
    restaurant, created = upsert_restaurant(
        db_session, "Chez Slah", "setup-tier-nouveau", SubscriptionTier.PRO
    )
    assert created is True
    assert restaurant.subscription_tier == SubscriptionTier.PRO


def test_rerunning_with_a_different_tier_upgrades_the_pilot(db_session):
    """Relancer le script avec une config mise à jour — après un appel où le
    patron passe à un palier supérieur — doit changer le palier existant."""
    restaurant, _created = upsert_restaurant(
        db_session, "Chez Slah", "setup-tier-upgrade", SubscriptionTier.ESSENTIEL
    )
    assert restaurant.subscription_tier == SubscriptionTier.ESSENTIEL

    same_restaurant, created_again = upsert_restaurant(
        db_session, "Chez Slah", "setup-tier-upgrade", SubscriptionTier.BUSINESS
    )
    assert created_again is False
    assert same_restaurant.id == restaurant.id
    assert same_restaurant.subscription_tier == SubscriptionTier.BUSINESS


def test_rerunning_with_the_same_tier_does_not_touch_the_restaurant(db_session):
    upsert_restaurant(db_session, "Chez Slah", "setup-tier-stable", SubscriptionTier.PRO)

    restaurant, created_again = upsert_restaurant(
        db_session, "Chez Slah", "setup-tier-stable", SubscriptionTier.PRO
    )
    assert created_again is False
    assert restaurant.subscription_tier == SubscriptionTier.PRO
