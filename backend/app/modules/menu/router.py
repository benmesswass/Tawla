from hashlib import sha256

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.logging import get_logger, log_event
from app.core.subscription import require_tier
from app.modules.menu import csv_import, options, regimes, schemas, suggestions
from app.modules.menu.models import MenuItem, MenuItemOptionGroup, MenuRegime
from app.modules.notifications.manager import manager
from app.modules.staff.dependencies import require_role
from app.modules.staff.models import Staff, StaffRole
from app.modules.tables import service as tables_service
from app.modules.tenants.models import SubscriptionTier

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
    payload: schemas.MenuCsvImport,
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER),
    _tier: Staff = Depends(require_tier(SubscriptionTier.PRO)),
):
    """
    Import d'une carte complète depuis un export de tableur. Saisir 30 plats un
    par un est le premier abandon probable d'un restaurateur (Phase 13.2).

    Les lignes valides sont importées même si d'autres sont fautives : le
    manager reçoit la liste précise des lignes à corriger, plutôt que de devoir
    recommencer tout le fichier pour une faute de frappe.

    Réservé à Pro et Business (offre à trois paliers, 2026-08-18).
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


def _sorted_menu(db: Session, restaurant_id: int) -> list[MenuItem]:
    items = (
        db.query(MenuItem)
        # Groupes d'options et régimes chargés en une fois : cet écran liste
        # toute la carte d'un coup (dashboard manager comme parcours client),
        # une requête par article n'y a pas sa place (même principe que
        # list_active_orders côté commandes).
        .options(
            selectinload(MenuItem.option_groups).selectinload(MenuItemOptionGroup.options),
            selectinload(MenuItem.regimes),
        )
        .filter(MenuItem.restaurant_id == restaurant_id)
        .order_by(MenuItem.name)
        .all()
    )
    return sorted(items, key=lambda item: (_category_rank(item.category), item.name))


@router.get("/by-restaurant/{restaurant_id}", response_model=list[schemas.MenuItemOut])
def list_menu(restaurant_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_MANAGER)):
    """
    Gestion de la carte côté dashboard manager.

    S-1 (audit 2026-08-18) : cette route était publique et acceptait un
    identifiant incrémental — la carte et les prix de n'importe quel
    établissement se lisaient sans jeton. Le parcours client passe désormais
    par `/by-table/{qr_token}` (ci-dessous), lié à la table scannée.
    """
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    return _sorted_menu(db, restaurant_id)


@router.get("/by-restaurant/{restaurant_id}/suggestions", response_model=dict[int, list[int]])
def list_suggestions(restaurant_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_MANAGER)):
    """
    Toutes les suggestions du restaurant, en une requête : `{id du plat: [ids
    proposés]}`. Gestion côté dashboard manager — voir S-1 ci-dessus, même
    fermeture que `list_menu`.
    """
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    return suggestions.get_suggestions_map(db, restaurant_id, only_available=True)


@router.get("/by-table/{qr_token}", response_model=list[schemas.MenuItemOut])
def list_menu_by_table(qr_token: str, db: Session = Depends(get_db)):
    """
    Parcours client, après scan du QR — public, mais lié à la table (comme
    les commandes depuis la Phase 12.2), pas à un identifiant à deviner.
    """
    table = tables_service.get_table_by_qr_token(db, qr_token)
    return _sorted_menu(db, table.restaurant_id)


@router.get("/by-table/{qr_token}/suggestions", response_model=dict[int, list[int]])
def list_suggestions_by_table(qr_token: str, db: Session = Depends(get_db)):
    """Suggestions du restaurant de la table scannée — même principe que
    `list_menu_by_table`. Les articles indisponibles sont écartés : proposer
    un plat en rupture est pire que ne rien proposer."""
    table = tables_service.get_table_by_qr_token(db, qr_token)
    return suggestions.get_suggestions_map(db, table.restaurant_id, only_available=True)


@router.get("/by-restaurant/{restaurant_id}/regimes", response_model=list[schemas.MenuRegimeOut])
def list_regimes(restaurant_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_MANAGER)):
    """Vocabulaire de régimes du restaurant (« Halal », « Végétarien »...),
    pour l'écran manager qui coche ensuite ceux qui s'appliquent à chaque
    article — voir menu/regimes.py. Demande de Wassim, 2026-08-26."""
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    return (
        db.query(MenuRegime)
        .filter(MenuRegime.restaurant_id == restaurant_id)
        .order_by(MenuRegime.display_order)
        .all()
    )


@router.put("/by-restaurant/{restaurant_id}/regimes", response_model=list[schemas.MenuRegimeOut])
def set_regimes(
    restaurant_id: int,
    payload: schemas.MenuRegimesUpdate,
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER),
):
    """Le manager définit le vocabulaire de régimes de son restaurant. Un nom
    déjà présent garde sa ligne (et donc ses articles tagués) — voir la
    docstring de regimes.set_restaurant_regimes pour la raison."""
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    result = regimes.set_restaurant_regimes(db, restaurant_id, payload.names)
    log_event(logger, "menu.regimes_set", restaurant_id=restaurant_id, count=len(result))
    return result


@router.put("/{item_id}/regimes", response_model=schemas.MenuItemOut)
def set_item_regimes(
    item_id: int,
    payload: schemas.MenuItemRegimesUpdate,
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER),
):
    """Le manager coche, pour cet article, un sous-ensemble du vocabulaire
    déjà défini pour le restaurant."""
    item = regimes.set_item_regimes(db, item_id, payload.regime_ids, staff.restaurant_id)
    log_event(
        logger, "menu.item_regimes_set",
        restaurant_id=staff.restaurant_id, menu_item_id=item_id, count=len(item.regimes),
    )
    return item


@router.put("/{item_id}/suggestions", response_model=schemas.MenuItemSuggestionsOut)
def set_suggestions(
    item_id: int,
    payload: schemas.MenuSuggestionsUpdate,
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER),
    _tier: Staff = Depends(require_tier(SubscriptionTier.PRO)),
):
    """Le manager choisit ce qui est proposé « avec ce plat » — remplacement en
    bloc, ce qui rend l'appel rejouable sans effet de bord.

    Réservé à Pro et Business (offre à trois paliers, 2026-08-18)."""
    suggested = suggestions.set_suggestions(db, item_id, payload.suggested_item_ids, staff.restaurant_id)
    log_event(
        logger, "menu.suggestions_set",
        restaurant_id=staff.restaurant_id, menu_item_id=item_id, count=len(suggested),
    )
    return schemas.MenuItemSuggestionsOut(menu_item_id=item_id, suggested_items=suggested)


@router.put("/{item_id}/option-groups", response_model=schemas.MenuItemOut)
def set_option_groups(
    item_id: int,
    payload: schemas.MenuItemOptionGroupsUpdate,
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER),
):
    """Le manager configure les groupes d'options d'un article (cuisson,
    sauce, accompagnement...) — remplacement en bloc, voir menu/options.py."""
    item = options.set_option_groups(db, item_id, payload.groups, staff.restaurant_id)
    log_event(
        logger, "menu.option_groups_set",
        restaurant_id=staff.restaurant_id, menu_item_id=item_id, group_count=len(payload.groups),
    )
    return item


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


# --- Photos de la carte ------------------------------------------------------

# Formats acceptés : ceux que produit un téléphone, plus le webp des
# navigateurs récents. Pas de SVG — un SVG est un document exécutable, servi
# depuis notre domaine il ouvrirait une injection de script.
FORMATS_PHOTO = {"image/jpeg", "image/png", "image/webp"}

# Le navigateur redimensionne avant d'envoyer (voir frontend/lib/photo.ts) :
# 3 Mo laissent passer une photo correcte tout en refusant l'envoi brut d'un
# appareil photo, qui immobiliserait la connexion du restaurant en plein service.
TAILLE_PHOTO_MAX = 3 * 1024 * 1024


@router.put("/{item_id}/image", response_model=schemas.MenuItemOut)
async def upload_menu_item_image(
    item_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    staff: Staff = Depends(_MANAGER),
    _tier: Staff = Depends(require_tier(SubscriptionTier.PRO)),
):
    """
    Photo déposée par le manager sur la carte. Réservée au manager : la photo
    d'un plat est un acte de gestion, au même titre que son prix.

    Réservé à Pro et Business (offre à trois paliers, 2026-08-18).
    """
    item = _get_item_in_scope(db, item_id, staff)

    if file.content_type not in FORMATS_PHOTO:
        raise HTTPException(
            status_code=415,
            detail={"code": "UNSUPPORTED_IMAGE", "message": "image must be jpeg, png or webp"},
        )

    contenu = await file.read()
    if len(contenu) > TAILLE_PHOTO_MAX:
        raise HTTPException(
            status_code=413,
            detail={"code": "IMAGE_TOO_LARGE", "message": "image exceeds 3 MB"},
        )

    item.image_data = contenu
    item.image_content_type = file.content_type
    # L'empreinte du contenu dans l'URL : sans elle, une photo remplacée
    # resterait l'ancienne dans le cache du téléphone des clients, et le
    # manager croirait que son dépôt n'a pas fonctionné.
    item.image_url = f"/api/v1/menu-items/{item.id}/image?v={sha256(contenu).hexdigest()[:12]}"
    db.commit()
    db.refresh(item)

    log_event(logger, "menu.image_uploaded", restaurant_id=item.restaurant_id, menu_item_id=item.id)
    return item


@router.get("/{item_id}/image")
def get_menu_item_image(item_id: int, db: Session = Depends(get_db)):
    """
    Publique, comme la carte elle-même : c'est le client attablé qui la
    regarde, et il n'a pas de compte.

    Mise en cache longue sans risque : l'URL porte l'empreinte du contenu,
    donc une photo remplacée change d'adresse.
    """
    item = db.get(MenuItem, item_id)
    if not item or not item.image_data:
        raise HTTPException(status_code=404, detail={"code": "IMAGE_NOT_FOUND", "message": "no image"})

    return Response(
        content=item.image_data,
        media_type=item.image_content_type or "image/jpeg",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.delete("/{item_id}/image", response_model=schemas.MenuItemOut)
def delete_menu_item_image(item_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_MANAGER)):
    """Retirer une photo ratée sans avoir à en déposer une autre."""
    item = _get_item_in_scope(db, item_id, staff)
    item.image_data = None
    item.image_content_type = None
    item.image_url = None
    db.commit()
    db.refresh(item)
    return item
