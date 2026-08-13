from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.staff.dependencies import require_role
from app.modules.staff.models import Staff, StaffRole
from app.modules.tenants import schemas
from app.modules.tenants.models import Restaurant

router = APIRouter(prefix="/api/v1/restaurants", tags=["restaurants"])

_MANAGER = require_role(StaffRole.MANAGER)


# `POST /api/v1/restaurants` a été supprimé en Phase 12.2 : il créait un
# établissement sans aucune authentification (n'importe qui pouvait polluer la
# base), n'était appelé par aucun frontend, et faisait doublon avec
# `POST /api/v1/auth/register` qui crée le restaurant ET son premier manager.
# Les tests s'en servaient comme fixture : ils passent désormais par
# `tests/conftest.py::create_restaurant`, qui écrit directement en base.


@router.get("/{restaurant_id}", response_model=schemas.RestaurantOut)
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    """Public — la page client en a besoin pour afficher le nom du resto et la bannière iftar."""
    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=404, detail={"code": "RESTAURANT_NOT_FOUND", "message": "restaurant not found"}
        )
    return restaurant


@router.patch("/{restaurant_id}/ramadan-mode", response_model=schemas.RestaurantOut)
def set_ramadan_mode(
    restaurant_id: int,
    payload: schemas.RamadanModeUpdate,
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER),
):
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})

    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=404, detail={"code": "RESTAURANT_NOT_FOUND", "message": "restaurant not found"}
        )

    restaurant.ramadan_mode_enabled = payload.enabled
    restaurant.iftar_time = payload.iftar_time
    db.commit()
    db.refresh(restaurant)
    return restaurant


@router.patch("/{restaurant_id}/cafe-mode", response_model=schemas.RestaurantOut)
def set_cafe_mode(
    restaurant_id: int,
    payload: schemas.CafeModeUpdate,
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER),
):
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})

    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=404, detail={"code": "RESTAURANT_NOT_FOUND", "message": "restaurant not found"}
        )

    restaurant.cafe_mode_enabled = payload.enabled
    db.commit()
    db.refresh(restaurant)
    return restaurant


@router.patch("/{restaurant_id}/kitchen-sound", response_model=schemas.RestaurantOut)
def set_kitchen_sound(
    restaurant_id: int,
    payload: schemas.KitchenSoundUpdate,
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER),
):
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})

    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=404, detail={"code": "RESTAURANT_NOT_FOUND", "message": "restaurant not found"}
        )

    restaurant.kitchen_sound_enabled = payload.enabled
    db.commit()
    db.refresh(restaurant)
    return restaurant
