import json

from pywebpush import webpush

from app.core.config import settings
from app.core.logging import get_logger, log_event

logger = get_logger("push")


def is_push_configured() -> bool:
    return bool(settings.vapid_public_key and settings.vapid_private_key)


def send_push_notification(subscription_json: str, title: str, body: str) -> None:
    """
    Best-effort : une notification push ne doit jamais faire échouer le
    flux de commande qui la déclenche (ex: passage en "prête" côté cuisine).
    No-op silencieux si les clés VAPID ne sont pas configurées (dev par
    défaut). Toute erreur (JSON invalide, abonnement expiré, navigateur qui
    a coupé les notifications...) est loguée puis avalée — jamais remontée.
    """
    if not is_push_configured():
        return

    try:
        subscription_info = json.loads(subscription_json)
        webpush(
            subscription_info=subscription_info,
            data=json.dumps({"title": title, "body": body}),
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": f"mailto:{settings.vapid_contact_email}"},
        )
    except Exception as exc:  # noqa: BLE001 — best-effort, ne doit jamais remonter
        log_event(logger, "push.send_failed", error=str(exc))
