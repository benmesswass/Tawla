import json

from pywebpush import webpush

from app.core.config import settings
from app.core.logging import get_logger, log_event

logger = get_logger("push")

# Délai maximal d'un envoi push (ROADMAP_PRODUCTION.md §P1.5).
#
# À poser EXPLICITEMENT : `pywebpush` a un défaut de `10000`, que `requests`
# interprète en **secondes** — soit près de trois heures. Un service de push
# lent (FCM, Mozilla…) immobilisait donc un thread et sa connexion base pour
# une durée pratiquement illimitée, à chaque commande créée, une fois par
# membre du personnel abonné.
#
# 5 s : une notification est best-effort et son intérêt est d'arriver TOUT DE
# SUITE. Passé ce délai, le serveur a de toute façon déjà vu la commande sur
# son écran — insister ne sert plus personne.
DELAI_PUSH_SECONDES = 5

# Budget total pour prévenir TOUTE une équipe. Sans lui, le plafond ci-dessus
# se multiplie par le nombre d'abonnés : une brigade de six, un service de
# push en panne, et une seule commande retient un thread une demi-minute.
BUDGET_PUSH_EQUIPE_SECONDES = 15


def is_push_configured() -> bool:
    return bool(settings.vapid_public_key and settings.vapid_private_key)


def send_push_notification(subscription_json: str, title: str, body: str) -> None:
    """
    Best-effort : une notification push ne doit jamais faire échouer le
    flux de commande qui la déclenche (ex: passage en "prête" côté cuisine).
    No-op silencieux si les clés VAPID ne sont pas configurées (dev par
    défaut). Toute erreur (JSON invalide, abonnement expiré, navigateur qui
    a coupé les notifications..., délai dépassé) est loguée puis avalée —
    jamais remontée.
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
            timeout=DELAI_PUSH_SECONDES,
        )
    except Exception as exc:  # noqa: BLE001 — best-effort, ne doit jamais remonter
        log_event(logger, "push.send_failed", error=str(exc))
