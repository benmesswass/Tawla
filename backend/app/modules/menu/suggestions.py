"""
Suggestions « avec ce plat » (Phase 14.1).

Règles métier tenues ici plutôt que dans le routeur, parce qu'elles sont
partagées entre l'écriture (manager) et la lecture (client) :

- un plat ne se suggère jamais lui-même ;
- une suggestion pointe toujours vers un article du même restaurant ;
- trois au maximum, sinon la proposition devient une deuxième carte ;
- côté client, un article indisponible n'est jamais proposé — proposer un plat
  en rupture est pire que ne rien proposer.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.menu.models import MenuItem, MenuSuggestion

MAX_SUGGESTIONS = 3


def _item_in_restaurant(db: Session, item_id: int, restaurant_id: int) -> MenuItem:
    item = db.get(MenuItem, item_id)
    if not item or item.restaurant_id != restaurant_id:
        raise HTTPException(
            status_code=404,
            detail={"code": "ITEM_NOT_FOUND", "message": f"menu item {item_id} not found", "menu_item_id": item_id},
        )
    return item


def set_suggestions(db: Session, menu_item_id: int, suggested_ids: list[int], restaurant_id: int) -> list[MenuItem]:
    item = _item_in_restaurant(db, menu_item_id, restaurant_id)

    unique_ids = list(dict.fromkeys(suggested_ids))  # dédoublonne en gardant l'ordre du manager
    if len(unique_ids) > MAX_SUGGESTIONS:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "TOO_MANY_SUGGESTIONS",
                "message": f"{MAX_SUGGESTIONS} suggestions au maximum par article",
            },
        )
    if item.id in unique_ids:
        raise HTTPException(
            status_code=422,
            detail={"code": "SELF_SUGGESTION", "message": "un plat ne peut pas se suggérer lui-même"},
        )

    suggested = [_item_in_restaurant(db, suggested_id, restaurant_id) for suggested_id in unique_ids]

    db.query(MenuSuggestion).filter(MenuSuggestion.menu_item_id == item.id).delete()
    for suggested_item in suggested:
        db.add(
            MenuSuggestion(
                restaurant_id=restaurant_id, menu_item_id=item.id, suggested_item_id=suggested_item.id
            )
        )
    db.commit()
    return suggested


def get_suggestions(db: Session, menu_item_id: int, *, only_available: bool) -> list[MenuItem]:
    query = (
        db.query(MenuItem)
        .join(MenuSuggestion, MenuSuggestion.suggested_item_id == MenuItem.id)
        .filter(MenuSuggestion.menu_item_id == menu_item_id)
    )
    if only_available:
        query = query.filter(MenuItem.is_available.is_(True))
    return query.order_by(MenuSuggestion.id).all()


def get_suggestions_map(db: Session, restaurant_id: int, *, only_available: bool) -> dict[int, list[int]]:
    """
    Toutes les suggestions d'un restaurant en une requête.

    Le menu client charge la carte entière d'un coup : interroger les
    suggestions plat par plat ferait autant d'allers-retours que d'articles, sur
    une connexion mobile de salle.
    """
    query = (
        db.query(MenuSuggestion.menu_item_id, MenuItem.id)
        .join(MenuItem, MenuSuggestion.suggested_item_id == MenuItem.id)
        .filter(MenuSuggestion.restaurant_id == restaurant_id)
    )
    if only_available:
        query = query.filter(MenuItem.is_available.is_(True))

    suggestions: dict[int, list[int]] = {}
    for menu_item_id, suggested_id in query.order_by(MenuSuggestion.id).all():
        suggestions.setdefault(menu_item_id, []).append(suggested_id)
    return suggestions
