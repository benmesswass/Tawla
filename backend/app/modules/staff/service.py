import secrets

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_event
from app.core.push import send_push_notification
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


def save_push_subscription(db: Session, staff: Staff, subscription: schemas.PushSubscriptionIn) -> None:
    """
    Opt-in explicite du membre du personnel sur l'écran serveur — jamais
    déclenché automatiquement (même règle que orders/service.py::
    save_push_subscription, dont c'est le pendant côté équipe).
    """
    staff.push_subscription = subscription.model_dump_json()
    db.commit()


def notify_restaurant_staff(db: Session, restaurant_id: int, title: str, body: str) -> None:
    """
    Alerte, même écran éteint ou onglet en arrière-plan, tout le personnel
    abonné de ce restaurant — nouvelle commande à prendre en charge ou appel
    serveur (demande de Wassim, 2026-08-26). Disponible à TOUS les paliers,
    contrairement à la notification client (« commande prête », réservée à
    Business) : rater une commande ou un appel a un coût opérationnel direct,
    quel que soit le palier payé.

    Pas de filtre par rôle : seul l'opt-in compte, et seul l'écran serveur
    (`/staff`, partagé serveur+manager) propose le bouton d'abonnement — la
    cuisine, sur un écran différent, n'a simplement jamais l'occasion de
    s'abonner ici.

    Best-effort comme send_push_notification lui-même : une erreur pour un
    abonné ne doit jamais empêcher les suivants.
    """
    subscribers = (
        db.query(Staff)
        .filter(
            Staff.restaurant_id == restaurant_id,
            Staff.is_active.is_(True),
            Staff.push_subscription.isnot(None),
        )
        .all()
    )
    for member in subscribers:
        send_push_notification(member.push_subscription, title, body)


def purge_push_subscriptions_of_inactive_staff(db: Session, dry_run: bool = False) -> int:
    """
    Un salarié désactivé (parti de l'établissement) n'a plus de raison
    d'être notifié — son abonnement push devient une donnée personnelle sans
    finalité (Phase 16, même principe que orders/service.py::
    purge_terminal_push_subscriptions).
    """
    stale = (
        db.query(Staff)
        .filter(Staff.is_active.is_(False), Staff.push_subscription.isnot(None))
        .all()
    )
    if dry_run:
        return len(stale)

    for member in stale:
        member.push_subscription = None
    db.commit()
    if stale:
        log_event(logger, "staff.push_subscriptions_purged", count=len(stale))
    return len(stale)


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
