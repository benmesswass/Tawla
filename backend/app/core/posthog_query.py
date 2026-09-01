"""
Lecture agrégée des événements PostHog pour la section « Produit &
acquisition » du dashboard admin plateforme (voir platform_admin/service.py,
frontend/app/admin/page.tsx). Requêtes HogQL via POSTHOG_PERSONAL_API_KEY
(lecture seule, scope insight:read + query:read) — jamais le project token
d'écriture utilisé par app/core/analytics.py pour émettre les événements.

Dégradation gracieuse partout : sans clé personnelle, ou si PostHog répond
en erreur, chaque fonction renvoie `None` plutôt que de lever — la section
du dashboard admin reste juste vide, jamais un dashboard cassé pour un souci
externe.
"""
from datetime import date, timedelta
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger, log_event

logger = get_logger("posthog_query")

_DEMO_ENGAGEMENT_EVENTS = ["menu_edited", "table_managed", "staff_managed", "csv_imported"]
_FUNNEL_EVENTS = ["demo_clicked", "signup_submitted", "purchase_completed"]


def _run_hogql(query: str, values: dict[str, Any] | None = None) -> list[list[Any]] | None:
    if not settings.posthog_personal_api_key:
        return None
    try:
        response = httpx.post(
            f"{settings.posthog_app_host}/api/projects/{settings.posthog_project_id}/query/",
            headers={"Authorization": f"Bearer {settings.posthog_personal_api_key}"},
            json={"query": {"kind": "HogQLQuery", "query": query, "values": values or {}}},
            timeout=15,
        )
        response.raise_for_status()
    except httpx.HTTPError as err:
        log_event(logger, "posthog_query.request_failed", error=str(err))
        return None
    payload = response.json()
    if payload.get("error"):
        log_event(logger, "posthog_query.query_error", error=payload["error"])
        return None
    return payload["results"]


def demo_starts_by_day(days: int = 30) -> list[dict] | None:
    rows = _run_hogql(
        "SELECT toDate(timestamp) AS day, count() AS n FROM events "
        "WHERE event = 'demo_clicked' AND properties.env = 'production' "
        "AND timestamp >= now() - INTERVAL {days} DAY "
        "GROUP BY day ORDER BY day",
        {"days": days},
    )
    if rows is None:
        return None
    # PostHog ne renvoie que les jours avec au moins un événement — on
    # complète les jours à zéro nous-mêmes, sinon la courbe relierait deux
    # jours actifs distants par une diagonale trompeuse (fausse impression
    # de montée progressive là où il n'y a que deux pics isolés).
    counts = {str(day): n for day, n in rows}
    today = date.today()
    return [
        {"date": (d := today - timedelta(days=offset)).isoformat(), "count": counts.get(d.isoformat(), 0)}
        for offset in range(days - 1, -1, -1)
    ]


def demo_engagement_totals(days: int = 30) -> list[dict] | None:
    """Ce que les visiteurs testent réellement en démo — filtré aux
    événements émis avec is_demo=true (dashboard/page.tsx, BandeauDemo.tsx),
    pas ceux d'un vrai restaurateur payant sur le même code."""
    rows = _run_hogql(
        "SELECT event, count() AS n FROM events "
        "WHERE event IN {events} AND properties.is_demo = true AND properties.env = 'production' "
        "AND timestamp >= now() - INTERVAL {days} DAY "
        "GROUP BY event ORDER BY n DESC",
        {"events": _DEMO_ENGAGEMENT_EVENTS, "days": days},
    )
    if rows is None:
        return None
    return [{"event": event, "count": n} for event, n in rows]


def paywall_hits_by_tier(days: int = 30) -> list[dict] | None:
    rows = _run_hogql(
        "SELECT properties.required_tier AS tier, count() AS n FROM events "
        "WHERE event = 'paywall_hit' AND properties.env = 'production' "
        "AND timestamp >= now() - INTERVAL {days} DAY "
        "GROUP BY tier ORDER BY n DESC",
        {"days": days},
    )
    if rows is None:
        return None
    return [{"tier": tier, "count": n} for tier, n in rows]


def acquisition_funnel(days: int = 30) -> list[dict] | None:
    """Nombre de visiteurs distincts par étape — pas un funnel strictement
    ordonné par utilisateur (complexité/fragilité pas justifiées au volume
    actuel), juste le compte à chaque étape sur la période."""
    rows = _run_hogql(
        "SELECT event, count(DISTINCT distinct_id) AS users FROM events "
        "WHERE event IN {events} AND properties.env = 'production' "
        "AND timestamp >= now() - INTERVAL {days} DAY "
        "GROUP BY event",
        {"events": _FUNNEL_EVENTS, "days": days},
    )
    if rows is None:
        return None
    counts = {event: users for event, users in rows}
    return [{"event": event, "users": counts.get(event, 0)} for event in _FUNNEL_EVENTS]
