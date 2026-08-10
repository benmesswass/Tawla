from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.staff.models import Staff
from app.modules.tables import schemas
from app.modules.tables.models import Table

router = APIRouter(prefix="/api/v1/tables", tags=["tables"])


@router.post("", response_model=schemas.TableOut, status_code=201)
def create_table(payload: schemas.TableCreate, db: Session = Depends(get_db)):
    table = Table(restaurant_id=payload.restaurant_id, label=payload.label)
    db.add(table)
    db.commit()
    db.refresh(table)
    return table


@router.get("/by-token/{qr_token}", response_model=schemas.TableOut)
def get_table_by_token(qr_token: str, db: Session = Depends(get_db)):
    """
    Endpoint appelé quand le client scanne le QR code.
    Le token est opaque : impossible de deviner une autre table.
    """
    table = db.query(Table).filter(Table.qr_token == qr_token).first()
    if not table:
        raise HTTPException(status_code=404, detail={"code": "INVALID_TABLE_CODE", "message": "invalid table code"})
    return table


@router.post("/{table_id}/assign-staff", response_model=schemas.TableOut)
def assign_staff(table_id: int, payload: schemas.TableAssignStaff, db: Session = Depends(get_db)):
    table = db.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail={"code": "TABLE_NOT_FOUND", "message": "table not found"})

    # Faille d'isolation trouvée à l'audit : cet endpoint acceptait n'importe
    # quel staff_id, y compris inexistant ou d'un autre restaurant.
    staff = db.get(Staff, payload.staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail={"code": "STAFF_NOT_FOUND", "message": "staff not found"})
    if staff.restaurant_id != table.restaurant_id:
        raise HTTPException(
            status_code=409,
            detail={"code": "STAFF_WRONG_RESTAURANT", "message": "staff does not belong to this restaurant"},
        )

    table.assigned_staff_id = payload.staff_id
    db.commit()
    db.refresh(table)
    return table
