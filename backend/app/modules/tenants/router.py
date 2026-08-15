from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.staff.dependencies import get_current_staff, require_role
from app.modules.staff.models import Staff, StaffRole
from app.modules.tables import service as tables_service
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


# Déclarée AVANT `/{restaurant_id}` : sinon FastAPI tente de lire « by-token »
# comme un entier et répond 422 au lieu de router ici.
@router.get("/by-token/{qr_token}", response_model=schemas.RestaurantPublicOut)
def get_restaurant_by_qr_token(qr_token: str, db: Session = Depends(get_db)):
    """
    Route client : publique, mais liée à une table précise par son `qr_token`
    opaque, comme toutes les routes du parcours de commande.

    Elle remplace la lecture par identifiant, qui était publique et
    incrémentale : parcourir 1, 2, 3… donnait la liste des établissements
    clients de Tawla et leur formule d'abonnement.
    """
    table = tables_service.get_table_by_qr_token(db, qr_token)
    return db.get(Restaurant, table.restaurant_id)


@router.get("/{restaurant_id}", response_model=schemas.RestaurantOut)
def get_restaurant(
    restaurant_id: int,
    db: Session = Depends(get_db),
    staff: Staff = Depends(get_current_staff),
):
    """
    Fiche complète — écran cuisine et dashboard, tous deux authentifiés.
    404 et non 403 sur un autre établissement : un 403 confirmerait qu'il
    existe.
    """
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(
            status_code=404, detail={"code": "RESTAURANT_NOT_FOUND", "message": "restaurant not found"}
        )
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
