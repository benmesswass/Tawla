from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.staff.dependencies import get_current_staff, require_role
from app.modules.staff.models import Staff, StaffRole
from app.modules.tables import schemas, service
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
    return service.get_table_by_qr_token(db, qr_token)


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


@router.get("/plan/{restaurant_id}", response_model=list[schemas.TablePlanOut])
def read_plan(
    restaurant_id: int,
    db: Session = Depends(get_db),
    staff: Staff = Depends(get_current_staff),
):
    """Le plan tel que le service le lit. Ouvert à tous les rôles : le serveur
    et la cuisine regardent la même salle que le manager."""
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    return db.query(Table).filter(Table.restaurant_id == restaurant_id).order_by(Table.id).all()


@router.put("/plan/{restaurant_id}", response_model=list[schemas.TableOut])
def save_plan(
    restaurant_id: int,
    payload: schemas.PlanUpdate,
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER),
):
    """
    Enregistre le plan de salle en une seule écriture.

    Dessiner la salle est un acte de gestion, réservé au manager : un plan qui
    se réorganiserait en plein service serait pire qu'aucun plan.

    Les tables sont d'abord toutes vérifiées, puis toutes écrites. Sans ce
    découpage, une table étrangère glissée en fin de liste laisserait le plan
    à moitié enregistré — et un plan à moitié juste envoie un serveur au
    mauvais endroit.
    """
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})

    tables: list[tuple[Table, schemas.TablePlacement]] = []
    for placement in payload.placements:
        table = db.get(Table, placement.table_id)
        if not table or table.restaurant_id != restaurant_id:
            raise HTTPException(
                status_code=404,
                detail={"code": "TABLE_NOT_FOUND", "message": f"table {placement.table_id} not found"},
            )
        tables.append((table, placement))

    for table, placement in tables:
        table.pos_x = placement.pos_x
        table.pos_y = placement.pos_y
        table.shape = placement.shape
        table.seats = placement.seats
    db.commit()

    return (
        db.query(Table)
        .filter(Table.restaurant_id == restaurant_id)
        .order_by(Table.id)
        .all()
    )
