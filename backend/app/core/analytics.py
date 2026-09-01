"""
Émission d'événements produit vers PostHog — funnel démo → abonnement Tawla
(tooling business interne, pas une fonctionnalité restaurateur/convive).
Appelé depuis subscription_payments.py pour purchase_completed. Dégradation
gracieuse : sans POSTHOG_API_KEY (voir .env.example), aucun envoi n'est
tenté — jamais bloquant pour le flux de paiement.
"""
from posthog import Posthog

from app.core.config import settings

_client = Posthog(settings.posthog_api_key, host=settings.posthog_host) if settings.posthog_api_key else None


def capture_event(distinct_id: str, event: str, **properties) -> None:
    if not _client:
        return
    _client.capture(event, distinct_id=distinct_id, properties=properties)
