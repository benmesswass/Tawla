from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.staff.dependencies import require_role
from app.modules.staff.models import Staff, StaffRole
from app.modules.tenants import schemas
from app.modules.tenants.models import Restaurant

router = APIRouter(prefix="/api/v1/restaurants", tags=["restaurants"])

_MANAGER = require_role(StaffRole.MANAGER)


@router.post("", response_model=schemas.RestaurantOut, status_code=201)
def create_restaurant(payload: schemas.RestaurantCreate, db: Session = Depends(get_db)):
    existing = db.query(Restaurant).filter(Restaurant.slug == payload.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail={"code": "SLUG_EXISTS", "message": "slug already exists"})

    restaurant = Restaurant(name=payload.name, slug=payload.slug)
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant


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
