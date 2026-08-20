from fastapi import Header, HTTPException

from app.modules.platform_admin.security import decode_admin_token


def get_current_platform_admin(authorization: str | None = Header(default=None)) -> None:
    """Dépendance de garde pour les routes `/platform-admin/*` — pas de compte
    en base à retrouver, un seul opérateur : un token valide suffit."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail={"code": "NOT_AUTHENTICATED", "message": "missing bearer token"}
        )

    token = authorization.removeprefix("Bearer ").strip()
    try:
        decode_admin_token(token)
    except Exception as exc:
        raise HTTPException(
            status_code=401, detail={"code": "INVALID_TOKEN", "message": "invalid or expired token"}
        ) from exc
