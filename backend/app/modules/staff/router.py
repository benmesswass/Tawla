from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.staff import schemas, security
from app.modules.staff.dependencies import get_current_staff
from app.modules.staff.models import Staff

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Hash bcrypt valide d'un mot de passe factice — comparé même quand l'email
# n'existe pas, pour ne pas révéler l'existence d'un compte par le timing
# (même stratégie qu'un login public classique, gardée ici par cohérence
# même si le staff n'est pas grand public).
_DUMMY_HASH = "$2b$12$f/0oq4Vt.wjtcqw76TM1DONwSQqoVa/lcI0H/3sTvjhBSBTJBjYHG"  # nosemgrep: generic.secrets.security.detected-bcrypt-hash.detected-bcrypt-hash


@router.post("/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    staff = db.query(Staff).filter(Staff.email == payload.email.lower()).first()

    if not staff:
        security.verify_password(payload.password, _DUMMY_HASH)
        raise HTTPException(
            status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "invalid email or password"}
        )

    if not security.verify_password(payload.password, staff.password_hash):
        raise HTTPException(
            status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "invalid email or password"}
        )

    token = security.create_access_token(staff.id, staff.restaurant_id, staff.role.value)
    return schemas.LoginResponse(access_token=token, staff=staff)


@router.get("/me", response_model=schemas.StaffOut)
def me(staff: Staff = Depends(get_current_staff)):
    return staff
