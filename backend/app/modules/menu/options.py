"""
Groupes d'options sur un article (« Cuisson », « Sauce », « Accompagnement »)
— France, phase F5/A2 : le manque fonctionnel jugé le plus grave pour vendre
en France, indépendant de la stratégie d'encaissement (S1/S2) et donc du
seul point de MARCHE_FRANCE.md codable avant l'arbitrage de la Phase F2.

Même principe que menu/suggestions.py : remplacement en bloc de tous les
groupes d'un article, jamais d'édition groupe par groupe — l'appel reste
rejouable sans effet de bord, et évite toute logique de diff.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.menu import schemas
from app.modules.menu.models import MenuItem, MenuItemOption, MenuItemOptionGroup


def _item_in_restaurant(db: Session, item_id: int, restaurant_id: int) -> MenuItem:
    item = db.get(MenuItem, item_id)
    if not item or item.restaurant_id != restaurant_id:
        raise HTTPException(
            status_code=404,
            detail={"code": "ITEM_NOT_FOUND", "message": f"menu item {item_id} not found", "menu_item_id": item_id},
        )
    return item


def set_option_groups(
    db: Session, menu_item_id: int, groups: list[schemas.MenuItemOptionGroupIn], restaurant_id: int
) -> MenuItem:
    item = _item_in_restaurant(db, menu_item_id, restaurant_id)

    # Remplacement en bloc via la collection ORM, jamais une DELETE en requête
    # brute : `cascade="all, delete-orphan"` sur MenuItem.option_groups n'agit
    # que quand un groupe quitte la collection Python. Une DELETE directe
    # contourne l'ORM et heurte la contrainte de clé étrangère dès qu'un groupe
    # a encore des options (constaté contre Postgres — SQLite, utilisé par les
    # tests, n'applique pas les clés étrangères par défaut et laissait passer).
    item.option_groups = [
        MenuItemOptionGroup(
            restaurant_id=restaurant_id,
            menu_item_id=item.id,
            name=group.name,
            min_select=group.min_select,
            max_select=group.max_select,
            display_order=group_order,
            options=[
                MenuItemOption(name=opt.name, price_delta=opt.price_delta, display_order=opt_order)
                for opt_order, opt in enumerate(group.options)
            ],
        )
        for group_order, group in enumerate(groups)
    ]
    db.commit()
    db.refresh(item)
    return item
