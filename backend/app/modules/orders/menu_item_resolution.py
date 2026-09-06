from fastapi import HTTPException

from app.modules.menu.models import MenuItem, MenuItemOption


def resolve_selected_options(menu_item: MenuItem, selected_option_ids: list[int]) -> list[MenuItemOption]:
    """
    Vérifie et retourne les options choisies pour un article — France, F5/A2.

    Le client n'envoie que des ids : ceux qui n'appartiennent pas à un groupe
    de CET article sont rejetés (jamais un id d'un autre article ou d'un autre
    restaurant, deviné ou copié depuis une commande différente), et chaque
    groupe doit recevoir entre min_select et max_select choix.

    Module séparé de `service.py` : `table_cart.py` (panier partagé
    multi-appareils) en a besoin sans dépendre de `service.py`, qui a
    lui-même besoin de `table_cart.py` pour créer une commande à partir du
    panier partagé — les deux dans le même fichier créeraient un import
    circulaire.
    """
    options_by_id = {opt.id: opt for group in menu_item.option_groups for opt in group.options}

    selected: list[MenuItemOption] = []
    for option_id in selected_option_ids:
        option = options_by_id.get(option_id)
        if option is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "OPTION_NOT_FOUND",
                    "message": f"option {option_id} does not belong to '{menu_item.name}'",
                    "menu_item_id": menu_item.id,
                },
            )
        selected.append(option)

    counts: dict[int, int] = {}
    for option in selected:
        counts[option.group_id] = counts.get(option.group_id, 0) + 1

    for group in menu_item.option_groups:
        count = counts.get(group.id, 0)
        if not (group.min_select <= count <= group.max_select):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "INVALID_OPTION_SELECTION",
                    "message": f"'{group.name}' requires between {group.min_select} and {group.max_select} choice(s)",
                    "menu_item_id": menu_item.id,
                    "group_id": group.id,
                    "group_name": group.name,
                },
            )
    return selected
