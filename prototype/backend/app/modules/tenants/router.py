from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.tenants import schemas
from app.modules.tenants.models import Restaurant

router = APIRouter(prefix="/api/v1/restaurants", tags=["restaurants"])


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
    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=404, detail={"code": "RESTAURANT_NOT_FOUND", "message": "restaurant not found"}
        )
    return restaurant
