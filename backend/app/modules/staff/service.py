import secrets

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_event
from app.modules.staff import schemas, security
from app.modules.staff.models import Staff, StaffRole

logger = get_logger("staff")


def _generate_password() -> str:
    """
    Mot de passe temporaire transmis de la main à la main par le manager
    (aucun service d'e-mail dans le projet). `token_urlsafe(9)` donne 12
    caractères : assez court pour être dicté, assez long pour ne pas être
    devinable.
    """
    return secrets.token_urlsafe(9)


def _get_in_scope(db: Session, staff_id: int, manager: Staff) -> Staff:
    """
    404 et non 403 quand la cible appartient à un autre restaurant : on ne
    confirme pas l'existence d'un compte hors de son périmètre (même règle
    que partout ailleurs dans le projet).
    """
    target = db.get(Staff, staff_id)
    if not target or target.restaurant_id != manager.restaurant_id:
        raise HTTPException(status_code=404, detail={"code": "STAFF_NOT_FOUND", "message": "staff not found"})
    return target


def _count_other_active_managers(db: Session, target: Staff) -> int:
    return (
        db.query(Staff)
        .filter(
            Staff.restaurant_id == target.restaurant_id,
            Staff.role == StaffRole.MANAGER,
            Staff.is_active.is_(True),
            Staff.id != target.id,
        )
        .count()
    )


def _refuse_if_last_active_manager(db: Session, target: Staff) -> None:
    """
    Un restaurant sans manager actif est un restaurant définitivement
    verrouillé : plus personne ne peut créer de compte, modifier la carte ni
    rouvrir l'accès. On refuse donc la dernière opération qui y mènerait,
    qu'elle passe par la désactivation ou par un changement de rôle.
    """
    if target.role != StaffRole.MANAGER or not target.is_active:
        return
    if _count_other_active_managers(db, target) == 0:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "LAST_ACTIVE_MANAGER",
                "message": "this is the last active manager: create or reactivate another manager first",
            },
        )


def create_staff(db: Session, payload: schemas.StaffCreate, manager: Staff) -> tuple[Staff, str | None]:
    email = payload.email.lower()
    if db.query(Staff).filter(Staff.email == email).first():
        raise HTTPException(
            status_code=409, detail={"code": "EMAIL_EXISTS", "message": "an account already exists with this email"}
        )

    generated = None if payload.password else _generate_password()
    staff = Staff(
        restaurant_id=manager.restaurant_id,  # jamais depuis le payload
        name=payload.name,
        role=payload.role,
        email=email,
        password_hash=security.hash_password(payload.password or generated),
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)

    log_event(
        logger, "staff.created",
        restaurant_id=staff.restaurant_id, staff_id=staff.id, role=staff.role.value, created_by=manager.id,
    )
    return staff, generated


def list_staff(db: Session, restaurant_id: int) -> list[Staff]:
    return (
        db.query(Staff)
        .filter(Staff.restaurant_id == restaurant_id)
        .order_by(Staff.is_active.desc(), Staff.role, Staff.name)
        .all()
    )


def update_staff(db: Session, staff_id: int, payload: schemas.StaffUpdate, manager: Staff) -> Staff:
    target = _get_in_scope(db, staff_id, manager)

    # Les deux seuls changements qui peuvent retirer le dernier manager actif.
    losing_manager_role = payload.role is not None and payload.role != StaffRole.MANAGER
    being_disabled = payload.is_active is False
    if losing_manager_role or being_disabled:
        _refuse_if_last_active_manager(db, target)

    if payload.name is not None:
        target.name = payload.name
    if payload.role is not None:
        target.role = payload.role
    if payload.is_active is not None:
        target.is_active = payload.is_active

    db.commit()
    db.refresh(target)

    log_event(
        logger, "staff.updated",
        restaurant_id=target.restaurant_id, staff_id=target.id,
        role=target.role.value, is_active=target.is_active, updated_by=manager.id,
    )
    return target


def reset_password(db: Session, staff_id: int, manager: Staff) -> tuple[Staff, str]:
    target = _get_in_scope(db, staff_id, manager)

    password = _generate_password()
    target.password_hash = security.hash_password(password)
    db.commit()
    db.refresh(target)

    log_event(
        logger, "staff.password_reset",
        restaurant_id=target.restaurant_id, staff_id=target.id, reset_by=manager.id,
    )
    return target, password
