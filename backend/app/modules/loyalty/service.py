from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.dates import as_utc
from app.core.logging import get_logger, log_event
from app.modules.loyalty import schemas
from app.modules.loyalty.models import LOYALTY_REWARD_THRESHOLD, LoyaltyMember
from app.modules.tables import service as tables_service

logger = get_logger("loyalty")

# Durée de conservation d'une fiche fidélité sans nouvelle commande (Phase 16).
# 24 mois : un client qui n'est pas revenu depuis deux ans n'a plus de
# programme de fidélité en cours, donc plus de finalité au stockage de son
# numéro. Volontairement une constante et non un réglage par restaurant : un
# délai de rétention négociable au cas par cas n'est plus une politique.
RETENTION_WITHOUT_ORDER = timedelta(days=730)


def _get_member(db: Session, restaurant_id: int, phone_number: str) -> LoyaltyMember | None:
    return (
        db.query(LoyaltyMember)
        .filter(LoyaltyMember.restaurant_id == restaurant_id, LoyaltyMember.phone_number == phone_number)
        .first()
    )


def get_or_create_member(
    db: Session, restaurant_id: int, phone_number: str, birth_date: date | None = None
) -> LoyaltyMember:
    """
    Seul chemin de création d'une fiche, et il part d'une commande réelle : le
    client donne son propre numéro, sur la table qu'il vient de scanner.

    Volontairement **pas** exposé en route publique (Phase 19.1) — appelé
    uniquement depuis `orders/service.py::create_order`. Ne fait jamais avancer
    le compteur : ça arrive au paiement confirmé (voir record_completed_order),
    jamais à la simple saisie.
    """
    member = _get_member(db, restaurant_id, phone_number)
    if member:
        if birth_date and not member.birth_date:
            member.birth_date = birth_date
            db.commit()
            db.refresh(member)
        return member

    member = LoyaltyMember(restaurant_id=restaurant_id, phone_number=phone_number, birth_date=birth_date)
    db.add(member)
    db.commit()
    db.refresh(member)
    log_event(logger, "loyalty.member_created", restaurant_id=member.restaurant_id, member_id=member.id)
    return member


def lookup_for_client(db: Session, payload: schemas.LoyaltyLookup) -> LoyaltyMember:
    """
    Consultation par le client attablé, en lecture seule (Phase 19.1). Le
    restaurant vient du `qr_token`, jamais d'un identifiant fourni.

    Résidu assumé et documenté : avec le token de la table en main, on peut
    encore savoir si un numéro est connu de **ce** restaurant. C'est le même
    niveau d'accès que passer commande, et le prix d'une carte de fidélité
    sans compte.
    """
    table = tables_service.get_table_by_qr_token(db, payload.qr_token)
    member = _get_member(db, table.restaurant_id, payload.phone_number)
    if not member:
        raise HTTPException(
            status_code=404, detail={"code": "LOYALTY_MEMBER_NOT_FOUND", "message": "loyalty member not found"}
        )
    return member


def record_completed_order(db: Session, restaurant_id: int, phone_number: str) -> None:
    """
    Appelé une fois la commande réellement payée (carte ou cash confirmé) —
    jamais à la création, pour qu'une commande annulée ou jamais payée ne
    fasse pas gagner de points.
    """
    member = _get_member(db, restaurant_id, phone_number)
    if not member:
        return

    member.order_count += 1
    member.last_order_at = datetime.now(timezone.utc)
    if member.order_count % LOYALTY_REWARD_THRESHOLD == 0:
        member.reward_available = True
    db.commit()
    log_event(
        logger, "loyalty.order_recorded",
        restaurant_id=restaurant_id, member_id=member.id, order_count=member.order_count,
    )


def purge_inactive_members(db: Session, now: datetime | None = None, dry_run: bool = False) -> int:
    """
    Supprime les fiches fidélité sans commande depuis `RETENTION_WITHOUT_ORDER`
    (Phase 16 — loi organique 2004-63 : pas de conservation sans finalité).

    Lancée à la main via `scripts/purge_donnees_personnelles.py`, pas par un
    ordonnanceur : à ce stade il n'y a pas assez de trafic pour justifier une
    tâche de fond, et une purge automatique mal réglée détruit des données
    qu'on ne peut pas récupérer. `dry_run` compte sans supprimer.

    La suppression est réelle et non un drapeau `is_deleted` : garder la ligne
    avec le numéro dedans ne serait pas une purge.
    """
    threshold = (now or datetime.now(timezone.utc)) - RETENTION_WITHOUT_ORDER
    # `last_order_at` est nul pour les fiches créées avant la Phase 16 et pour
    # celles qui n'ont jamais abouti à une commande payée : c'est `created_at`
    # qui fait alors foi, sinon ces fiches ne seraient jamais purgées.
    stale = [
        member
        for member in db.query(LoyaltyMember).all()
        if as_utc(member.last_order_at or member.created_at) < threshold
    ]
    if dry_run:
        return len(stale)

    for member in stale:
        db.delete(member)
    db.commit()
    if stale:
        log_event(logger, "loyalty.members_purged", count=len(stale))
    return len(stale)


def get_member_for_staff(db: Session, restaurant_id: int, phone_number: str) -> LoyaltyMember:
    member = _get_member(db, restaurant_id, phone_number)
    if not member:
        raise HTTPException(
            status_code=404, detail={"code": "LOYALTY_MEMBER_NOT_FOUND", "message": "loyalty member not found"}
        )
    return member


def redeem_reward(db: Session, member_id: int, restaurant_id: int) -> LoyaltyMember:
    member = db.get(LoyaltyMember, member_id)
    if not member or member.restaurant_id != restaurant_id:
        raise HTTPException(
            status_code=404, detail={"code": "LOYALTY_MEMBER_NOT_FOUND", "message": "loyalty member not found"}
        )
    if not member.reward_available:
        raise HTTPException(
            status_code=409, detail={"code": "NO_REWARD_AVAILABLE", "message": "no reward available to redeem"}
        )

    member.reward_available = False
    db.commit()
    db.refresh(member)
    log_event(logger, "loyalty.reward_redeemed", restaurant_id=restaurant_id, member_id=member.id)
    return member
