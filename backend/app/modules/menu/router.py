from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger, log_event
from app.modules.menu import csv_import, schemas
from app.modules.menu.models import MenuItem
from app.modules.notifications.manager import manager
from app.modules.staff.dependencies import require_role
from app.modules.staff.models import Staff, StaffRole

logger = get_logger("menu")

router = APIRouter(prefix="/api/v1/menu-items", tags=["menu"])

_MANAGER = require_role(StaffRole.MANAGER)

# Ordre logique d'un repas plutôt que l'ordre alphabétique par défaut
# (audit PO : "Boissons"/"Desserts" passaient avant "Plats"). Toute
# catégorie absente de cette liste est repoussée en fin de carte.
CATEGORY_ORDER = ["Entrées", "Plats", "Desserts", "Boissons"]


def _category_rank(category: str) -> int:
    try:
        return CATEGORY_ORDER.index(category)
    except ValueError:
        return len(CATEGORY_ORDER)


def _get_item_in_scope(db: Session, item_id: int, staff: Staff) -> MenuItem:
    item = db.get(MenuItem, item_id)
    if not item or item.restaurant_id != staff.restaurant_id:
        raise HTTPException(status_code=404, detail={"code": "ITEM_NOT_FOUND", "message": "menu item not found"})
    return item


@router.post("", response_model=schemas.MenuItemOut, status_code=201)
def create_menu_item(payload: schemas.MenuItemCreate, db: Session = Depends(get_db), staff: Staff = Depends(_MANAGER)):
    if payload.restaurant_id != staff.restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    item = MenuItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/import-csv", response_model=schemas.MenuCsvImportResult)
def import_menu_csv(
    payload: schemas.MenuCsvImport, db: Session = Depends(get_db), staff: Staff = Depends(_MANAGER)
):
    """
    Import d'une carte complète depuis un export de tableur. Saisir 30 plats un
    par un est le premier abandon probable d'un restaurateur (Phase 13.2).

    Les lignes valides sont importées même si d'autres sont fautives : le
    manager reçoit la liste précise des lignes à corriger, plutôt que de devoir
    recommencer tout le fichier pour une faute de frappe.
    """
    result = csv_import.parse_menu_csv(payload.content)
    if not result.items:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "CSV_UNREADABLE",
                "message": "aucun article n'a pu être lu dans ce fichier",
                "errors": result.errors,
            },
        )

    applied = csv_import.apply_items(
        db, staff.restaurant_id, result.items, disable_missing=payload.replace_existing
    )

    log_event(
        logger, "menu.csv_imported",
        restaurant_id=staff.restaurant_id, created=applied.created_count,
        updated=applied.updated_count, disabled=applied.disabled_count, errors=len(result.errors),
    )
    return schemas.MenuCsvImportResult(
        created_count=applied.created_count,
        updated_count=applied.updated_count,
        disabled_count=applied.disabled_count,
        errors=result.errors,
    )


@router.get("/by-restaurant/{restaurant_id}", response_model=list[schemas.MenuItemOut])
def list_menu(restaurant_id: int, db: Session = Depends(get_db)):
    """
    Endpoint public appelé par la page client après scan du QR.
    Ne renvoie que ce qui est nécessaire pour afficher le menu, triée dans
    l'ordre logique d'un repas (voir CATEGORY_ORDER).
    """
    items = (
        db.query(MenuItem)
        .filter(MenuItem.restaurant_id == restaurant_id)
        .order_by(MenuItem.name)
        .all()
    )
    return sorted(items, key=lambda item: (_category_rank(item.category), item.name))


@router.patch("/{item_id}/availability", response_model=schemas.MenuItemOut)
async def set_availability(
    item_id: int, payload: schemas.MenuItemAvailability, db: Session = Depends(get_db), staff: Staff = Depends(_MANAGER)
):
    """Rupture de stock en un clic — le resto en a besoin en permanence."""
    item = _get_item_in_scope(db, item_id, staff)
    item.is_available = payload.is_available
    db.commit()
    db.refresh(item)

    # Un client déjà sur la page menu doit voir la rupture instantanément,
    # pas seulement au moment où il tente de commander l'article.
    await manager.broadcast(
        item.restaurant_id, channel="menu",
        message={
            "event": "menu_item.availability_changed",
            "menu_item_id": item.id,
            "is_available": item.is_available,
        },
    )
    return item


@router.patch("/{item_id}", response_model=schemas.MenuItemOut)
def update_menu_item(
    item_id: int, payload: schemas.MenuItemUpdate, db: Session = Depends(get_db), staff: Staff = Depends(_MANAGER)
):
    """Édition depuis le dashboard resto (nom, prix, catégorie, description, photo)."""
    item = _get_item_in_scope(db, item_id, staff)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def delete_menu_item(item_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_MANAGER)):
    item = _get_item_in_scope(db, item_id, staff)
    db.delete(item)
    db.commit()
