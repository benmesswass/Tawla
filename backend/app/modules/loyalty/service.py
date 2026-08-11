from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_event
from app.modules.loyalty import schemas
from app.modules.loyalty.models import LOYALTY_REWARD_THRESHOLD, LoyaltyMember

logger = get_logger("loyalty")


def _get_member(db: Session, restaurant_id: int, phone_number: str) -> LoyaltyMember | None:
    return (
        db.query(LoyaltyMember)
        .filter(LoyaltyMember.restaurant_id == restaurant_id, LoyaltyMember.phone_number == phone_number)
        .first()
    )


def lookup_or_create(db: Session, payload: schemas.LoyaltyLookup) -> LoyaltyMember:
    """
    Appelé par le client au moment de commander (numéro facultatif) — crée
    la fiche fidélité si c'est sa première visite, ou la retrouve sinon.
    Ne fait jamais avancer le compteur : ça arrive uniquement au paiement
    confirmé (voir record_completed_order), jamais à la simple saisie.
    """
    member = _get_member(db, payload.restaurant_id, payload.phone_number)
    if member:
        if payload.birth_date and not member.birth_date:
            member.birth_date = payload.birth_date
            db.commit()
            db.refresh(member)
        return member

    member = LoyaltyMember(
        restaurant_id=payload.restaurant_id, phone_number=payload.phone_number, birth_date=payload.birth_date
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    log_event(logger, "loyalty.member_created", restaurant_id=member.restaurant_id, member_id=member.id)
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
    if member.order_count % LOYALTY_REWARD_THRESHOLD == 0:
        member.reward_available = True
    db.commit()
    log_event(
        logger, "loyalty.order_recorded",
        restaurant_id=restaurant_id, member_id=member.id, order_count=member.order_count,
    )


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
