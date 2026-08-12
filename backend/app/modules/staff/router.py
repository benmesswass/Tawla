import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.modules.staff import schemas, security
from app.modules.staff.dependencies import get_current_staff
from app.modules.staff.models import Staff, StaffRole
from app.modules.tenants.models import Restaurant

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Hash bcrypt valide d'un mot de passe factice — comparé même quand l'email
# n'existe pas, pour ne pas révéler l'existence d'un compte par le timing
# (même stratégie qu'un login public classique, gardée ici par cohérence
# même si le staff n'est pas grand public).
_DUMMY_HASH = "$2b$12$f/0oq4Vt.wjtcqw76TM1DONwSQqoVa/lcI0H/3sTvjhBSBTJBjYHG"  # nosemgrep: generic.secrets.security.detected-bcrypt-hash.detected-bcrypt-hash


def _slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "restaurant"


def _unique_slug(db: Session, name: str) -> str:
    base = _slugify(name)
    slug = base
    suffix = 2
    while db.query(Restaurant).filter(Restaurant.slug == slug).first():
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


@router.post("/register", response_model=schemas.LoginResponse, status_code=201, dependencies=[Depends(rate_limit)])
def register(payload: schemas.RegisterRequest, db: Session = Depends(get_db)):
    """
    Onboarding self-service d'un nouvel établissement : crée le restaurant
    et son premier compte manager en une seule fois, puis connecte
    immédiatement (même paire access_token/staff que /login) — pas d'étape
    de vérification d'e-mail (aucun service d'envoi en place, cohérent avec
    le reste du projet qui n'a aucune dépendance payante obligatoire).
    """
    email = payload.email.lower()
    if db.query(Staff).filter(Staff.email == email).first():
        raise HTTPException(
            status_code=409, detail={"code": "EMAIL_EXISTS", "message": "an account already exists with this email"}
        )

    restaurant = Restaurant(name=payload.restaurant_name, slug=_unique_slug(db, payload.restaurant_name))
    db.add(restaurant)
    db.flush()

    staff = Staff(
        restaurant_id=restaurant.id,
        name=payload.manager_name,
        role=StaffRole.MANAGER,
        email=email,
        password_hash=security.hash_password(payload.password),
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)

    token = security.create_access_token(staff.id, staff.restaurant_id, staff.role.value)
    return schemas.LoginResponse(access_token=token, staff=staff)


@router.post("/login", response_model=schemas.LoginResponse, dependencies=[Depends(rate_limit)])
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
