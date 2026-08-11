from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.staff.dependencies import require_role
from app.modules.staff.models import Staff, StaffRole
from app.modules.tables import schemas
from app.modules.tables.models import Table

router = APIRouter(prefix="/api/v1/tables", tags=["tables"])

_MANAGER = require_role(StaffRole.MANAGER)


@router.post("", response_model=schemas.TableOut, status_code=201)
def create_table(payload: schemas.TableCreate, db: Session = Depends(get_db), staff: Staff = Depends(_MANAGER)):
    if payload.restaurant_id != staff.restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    table = Table(restaurant_id=payload.restaurant_id, label=payload.label, zone=payload.zone)
    db.add(table)
    db.commit()
    db.refresh(table)
    return table


@router.get("/by-restaurant/{restaurant_id}", response_model=list[schemas.TableOut])
def list_tables(restaurant_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_MANAGER)):
    """Gestion des tables et de leurs zones de salle côté dashboard manager."""
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    return db.query(Table).filter(Table.restaurant_id == restaurant_id).order_by(Table.id).all()


@router.patch("/{table_id}", response_model=schemas.TableOut)
def update_table(
    table_id: int, payload: schemas.TableUpdate, db: Session = Depends(get_db), staff: Staff = Depends(_MANAGER)
):
    table = db.get(Table, table_id)
    if not table or table.restaurant_id != staff.restaurant_id:
        raise HTTPException(status_code=404, detail={"code": "TABLE_NOT_FOUND", "message": "table not found"})

    table.label = payload.label
    table.zone = payload.zone
    db.commit()
    db.refresh(table)
    return table


@router.get("/by-token/{qr_token}", response_model=schemas.TableOut)
def get_table_by_token(qr_token: str, db: Session = Depends(get_db)):
    """
    Endpoint appelé quand le client scanne le QR code — public, pas d'auth.
    Le token est opaque : impossible de deviner une autre table.
    """
    table = db.query(Table).filter(Table.qr_token == qr_token).first()
    if not table:
        raise HTTPException(status_code=404, detail={"code": "INVALID_TABLE_CODE", "message": "invalid table code"})
    return table


@router.post("/{table_id}/assign-staff", response_model=schemas.TableOut)
def assign_staff(
    table_id: int, payload: schemas.TableAssignStaff, db: Session = Depends(get_db), staff: Staff = Depends(_MANAGER)
):
    table = db.get(Table, table_id)
    if not table or table.restaurant_id != staff.restaurant_id:
        raise HTTPException(status_code=404, detail={"code": "TABLE_NOT_FOUND", "message": "table not found"})

    # Faille d'isolation trouvée à l'audit : cet endpoint acceptait n'importe
    # quel staff_id, y compris inexistant ou d'un autre restaurant.
    target_staff = db.get(Staff, payload.staff_id)
    if not target_staff:
        raise HTTPException(status_code=404, detail={"code": "STAFF_NOT_FOUND", "message": "staff not found"})
    if target_staff.restaurant_id != table.restaurant_id:
        raise HTTPException(
            status_code=409,
            detail={"code": "STAFF_WRONG_RESTAURANT", "message": "staff does not belong to this restaurant"},
        )

    table.assigned_staff_id = payload.staff_id
    db.commit()
    db.refresh(table)
    return table
