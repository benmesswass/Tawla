from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.etat_partage import decoder, encoder, magasin
from app.modules.menu.models import MenuItem
from app.modules.orders import schemas
from app.modules.orders.menu_item_resolution import resolve_selected_options


class TableCartStore:
    """
    Panier partagé d'une table — jamais en base, jamais de migration (voir
    `docs/adr/0005-panier-de-table-en-memoire.md`, toujours valable : rien de
    ceci n'est durable, et c'est voulu).

    Depuis P2.1 le stockage passe par `core/etat_partage.py::magasin` : dicts
    en mémoire par défaut (comportement identique à avant), Redis dès que
    `REDIS_URL` est renseignée — c'est ce qui permet à deux téléphones de la
    même table de tomber sur le même panier même s'ils sont servis par deux
    instances backend différentes. Effet de bord gagné au passage : un
    déploiement ne vide plus les paniers des clients attablés.

    Une ligne par (`menu_item_id`, `added_by_key`), jamais deux pour la même
    paire — même limitation déjà assumée par le panier local d'un seul
    appareil (v1, `CartLine` côté frontend) : ce chantier ne l'étend pas à
    plusieurs lignes du même article avec des options différentes pour une
    même personne. En revanche deux personnes différentes qui commandent le
    même plat obtiennent bien deux lignes distinctes (identité de table,
    ROADMAP.md §Override) — `added_by_key` fait partie de la clé pour ça,
    `None`/vide regroupé sous une seule clé de repli (appareil sans identité
    déclarée).
    """

    @staticmethod
    def _cle(table_id: int) -> str:
        return f"panier:{table_id}"

    @staticmethod
    def _champ(item: schemas.OrderItemCreate) -> str:
        return f"{item.menu_item_id}|{item.added_by_key or ''}"

    def snapshot(self, table_id: int) -> list[schemas.OrderItemCreate]:
        return _relire(magasin.lire(self._cle(table_id)))

    def set_line(self, table_id: int, item: schemas.OrderItemCreate) -> None:
        """Quantité à 0 retire la ligne — même convention qu'un panier local
        où décrémenter sous 1 fait disparaître l'article."""
        cle, champ = self._cle(table_id), self._champ(item)
        if item.quantity <= 0:
            magasin.retirer(cle, champ)
        else:
            magasin.ecrire(cle, champ, encoder(item.model_dump()))

    def pop_all(self, table_id: int) -> list[schemas.OrderItemCreate]:
        """Lit et vide le panier en UNE seule opération atomique : deux
        appareils qui valident au même instant ne peuvent jamais transformer
        deux fois le même panier en deux commandes, l'un des deux tombe
        forcément sur un panier déjà vidé. La garantie tenait à l'absence
        d'`await` entre la lecture et le vidage en mono-instance ; elle tient
        désormais au `MULTI/EXEC` du magasin, qui la préserve entre instances."""
        return _relire(magasin.vider_et_lire(self._cle(table_id)))


def _relire(champs: dict[str, str]) -> list[schemas.OrderItemCreate]:
    return [schemas.OrderItemCreate(**decoder(valeur)) for valeur in champs.values()]


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
