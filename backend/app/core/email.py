"""
Confirmation de paiement + facture PDF, envoyées uniquement si le client a
laissé son adresse au moment de payer (confirmations de paiement, 2026-08-19).

Dégradation gracieuse comme Konnect : sans `RESEND_API_KEY`, l'envoi est
silencieusement ignoré (juste loggé) — jamais une exception qui remonterait
jusqu'à l'appelant. Un email raté ne doit jamais faire échouer un paiement
déjà encaissé.
"""
import base64
import os

import httpx

from app.core.logging import get_logger, log_event

logger = get_logger("email")

RESEND_API_URL = "https://api.resend.com/emails"


def is_email_enabled() -> bool:
    return bool(os.environ.get("RESEND_API_KEY"))


def send_email_with_attachment(
    *, to: str, subject: str, html_body: str, attachment_filename: str, attachment_bytes: bytes,
) -> bool:
    """`True` si effectivement envoyé. Ne lève jamais — voir docstring du module."""
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        return False

    from_address = os.environ.get("RESEND_FROM_EMAIL", "Tawla <onboarding@resend.dev>")
    body = {
        "from": from_address,
        "to": [to],
        "subject": subject,
        "html": html_body,
        "attachments": [
            {"filename": attachment_filename, "content": base64.b64encode(attachment_bytes).decode("ascii")}
        ],
    }
    try:
        res = httpx.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=body,
            timeout=15,
        )
    except httpx.HTTPError as err:
        log_event(logger, "email.send_error", to=to, error=str(err))
        return False

    if res.status_code >= 400:
        log_event(logger, "email.send_failed", to=to, status=res.status_code, body=res.text[:300])
        return False
    return True
