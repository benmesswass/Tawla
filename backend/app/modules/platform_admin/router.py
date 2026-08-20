from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.modules.platform_admin import schemas, security, service
from app.modules.platform_admin.dependencies import get_current_platform_admin
from app.modules.staff.security import verify_password

router = APIRouter(prefix="/api/v1/platform-admin", tags=["platform-admin"])

# Hash bcrypt valide comparé même quand aucun mot de passe n'est configuré —
# même stratégie anti-timing que /auth/login (staff/router.py::_DUMMY_HASH),
# ici pour ne pas laisser deviner si PLATFORM_ADMIN_PASSWORD_HASH est posé.
_DUMMY_HASH = "$2b$12$f/0oq4Vt.wjtcqw76TM1DONwSQqoVa/lcI0H/3sTvjhBSBTJBjYHG"  # nosemgrep: generic.secrets.security.detected-bcrypt-hash.detected-bcrypt-hash


@router.post("/login", response_model=schemas.AdminLoginResponse, dependencies=[Depends(rate_limit())])
def login(payload: schemas.AdminLoginRequest):
    configured_hash = settings.platform_admin_password_hash
    # Fail-closed : un hash vide (défaut de dev, ou prod pas encore
    # configurée) refuse tout mot de passe plutôt que d'ouvrir l'accès au
    # chiffre d'affaires de tous les restaurants clients.
    if not configured_hash:
        verify_password(payload.password, _DUMMY_HASH)
        raise HTTPException(
            status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "invalid password"}
        )
    if not verify_password(payload.password, configured_hash):
        raise HTTPException(
            status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "invalid password"}
        )
    return schemas.AdminLoginResponse(access_token=security.create_admin_token())


@router.get(
    "/overview",
    response_model=schemas.PlatformOverview,
    dependencies=[Depends(get_current_platform_admin)],
)
async def overview(db: Session = Depends(get_db)):
    return await service.get_overview(db)
