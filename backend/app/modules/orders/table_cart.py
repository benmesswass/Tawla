from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.menu.models import MenuItem
from app.modules.orders import schemas
from app.modules.orders.menu_item_resolution import resolve_selected_options


class TableCartStore:
    """
    Panier partagé d'une table, tenu EN MÉMOIRE — jamais en base, jamais de
    migration (voir `docs/adr/0005-panier-de-table-en-memoire.md`). Même
    logique que `notifications/manager.py::ConnectionManager` : un dict en
    mémoire suffit en mono-instance, remplacé par un pub/sub le jour où ça ne
    suffit plus, sans toucher aux appelants.

    Une ligne par `menu_item_id`, jamais deux — même limitation déjà assumée
    par le panier local d'un seul appareil (v1, `CartLine` côté frontend) :
    ce chantier ne l'étend pas à plusieurs lignes du même article avec des
    options différentes.
    """

    def __init__(self) -> None:
        self._carts: dict[int, dict[int, schemas.OrderItemCreate]] = defaultdict(dict)

    def snapshot(self, table_id: int) -> list[schemas.OrderItemCreate]:
        return list(self._carts.get(table_id, {}).values())

    def set_line(self, table_id: int, item: schemas.OrderItemCreate) -> None:
        """Quantité à 0 retire la ligne — même convention qu'un panier local
        où décrémenter sous 1 fait disparaître l'article."""
        if item.quantity <= 0:
            self._carts[table_id].pop(item.menu_item_id, None)
        else:
            self._carts[table_id][item.menu_item_id] = item

    def pop_all(self, table_id: int) -> list[schemas.OrderItemCreate]:
        """Lit et vide le panier en une seule opération synchrone (aucun
        `await` entre les deux) : deux appareils qui valident au même
        instant ne peuvent jamais transformer deux fois le même panier en
        deux commandes, l'un des deux tombe forcément sur un panier déjà vidé."""
        lines = list(self._carts.get(table_id, {}).values())
        self._carts.pop(table_id, None)
        return lines


table_cart_store = TableCartStore()


def validate_cart_line(db: Session, restaurant_id: int, item: schemas.OrderItemCreate) -> None:
    """
    Même contrôle que la première moitié de `orders/service.py::_build_order_items`
    (existence, rattachement au restaurant, disponibilité, options valides) —
    sans le prix : le panier partagé ne diffuse que la sélection, jamais un
    prix. Chaque appareil connaît déjà la carte (`menu` côté frontend) et
    l'affiche lui-même ; le prix n'est refigé qu'à la validation, dans
    `orders/service.py::create_order_from_table_cart`, exactement comme
    aujourd'hui pour le panier d'un seul appareil.
    """
    menu_item = db.get(MenuItem, item.menu_item_id)
    if not menu_item or menu_item.restaurant_id != restaurant_id:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "ITEM_NOT_FOUND",
                "message": f"menu item {item.menu_item_id} not found",
                "menu_item_id": item.menu_item_id,
            },
        )
    if not menu_item.is_available:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ITEM_UNAVAILABLE",
                "message": f"'{menu_item.name}' is no longer available",
                "item_name": menu_item.name,
                "menu_item_id": menu_item.id,
            },
        )
    resolve_selected_options(menu_item, item.selected_option_ids)


def snapshot_message(table_id: int) -> dict:
    lines = table_cart_store.snapshot(table_id)
    return {"event": "cart.updated", "lines": [line.model_dump() for line in lines]}
