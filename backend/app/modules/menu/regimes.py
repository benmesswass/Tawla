"""
Vocabulaire de régimes alimentaires, propre à chaque restaurant (« Halal »,
« Végétarien », « Vegan », ou tout nom choisi par le manager) — demande de
Wassim (2026-08-26), remplace l'idée d'une liste figée de marqueurs pour le
marché français (§A6 de MARCHE_FRANCE.md) : « halal » n'est central qu'en
Tunisie, ailleurs c'est un régime parmi d'autres. Coexiste avec
`MenuItem.is_halal`, ne le remplace pas (voir menu/models.py).

Deux opérations bien distinctes, à ne jamais confondre :
- le VOCABULAIRE du restaurant (ce fichier, `set_restaurant_regimes`) ;
- les régimes COCHÉS sur un article donné (`set_item_regimes`), qui piochent
  dans ce vocabulaire.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.menu.models import MenuItem, MenuRegime


def set_restaurant_regimes(db: Session, restaurant_id: int, names: list[str]) -> list[MenuRegime]:
    """
    Remplace le vocabulaire du restaurant — mais **jamais** par une DELETE
    puis recréation en bloc : un article garde son régime tant que le nom
    survit dans la nouvelle liste, sinon éditer une seule fois le vocabulaire
    (ex. ajouter « Sans porc ») décocherait silencieusement « Halal » et
    « Végétarien » sur tous les articles qui les portaient déjà. Chaque nom
    inchangé garde donc sa ligne (et son id, donc ses articles tagués) ; un
    nom disparu de la liste est effacé (et disparaît de ses articles, en
    cascade — c'est la conséquence attendue de le retirer du vocabulaire) ;
    un nom nouveau est créé.
    """
    # Dédoublonné en gardant l'ordre d'envoi du manager, qui devient l'ordre
    # d'affichage (display_order) — un nom vide ou blanc n'est pas un régime.
    seen: set[str] = set()
    ordered_names: list[str] = []
    for raw in names:
        name = raw.strip()
        if name and name not in seen:
            seen.add(name)
            ordered_names.append(name)

    existing_by_name = {
        r.name: r
        for r in db.query(MenuRegime).filter(MenuRegime.restaurant_id == restaurant_id).all()
    }

    kept_or_created: list[MenuRegime] = []
    for order, name in enumerate(ordered_names):
        regime = existing_by_name.get(name)
        if regime:
            regime.display_order = order
        else:
            regime = MenuRegime(restaurant_id=restaurant_id, name=name, display_order=order)
            db.add(regime)
        kept_or_created.append(regime)

    for name, regime in existing_by_name.items():
        if name not in seen:
            db.delete(regime)

    db.commit()
    for regime in kept_or_created:
        db.refresh(regime)
    return sorted(kept_or_created, key=lambda r: r.display_order)


def _item_in_restaurant(db: Session, item_id: int, restaurant_id: int) -> MenuItem:
    item = db.get(MenuItem, item_id)
    if not item or item.restaurant_id != restaurant_id:
        raise HTTPException(
            status_code=404,
            detail={"code": "ITEM_NOT_FOUND", "message": f"menu item {item_id} not found", "menu_item_id": item_id},
        )
    return item


def set_item_regimes(db: Session, item_id: int, regime_ids: list[int], restaurant_id: int) -> MenuItem:
    """Coche, pour UN article, un sous-ensemble du vocabulaire déjà défini
    pour le restaurant. Un id qui n'appartient pas à ce restaurant est
    silencieusement écarté plutôt que de lever — un vocabulaire modifié entre
    le chargement de l'écran et l'enregistrement ne doit pas bloquer le
    manager sur une erreur qu'il ne peut pas comprendre."""
    item = _item_in_restaurant(db, item_id, restaurant_id)

    valid_ids = {
        r.id for r in db.query(MenuRegime.id).filter(
            MenuRegime.restaurant_id == restaurant_id, MenuRegime.id.in_(regime_ids)
        ).all()
    }
    item.regimes = (
        db.query(MenuRegime)
        .filter(MenuRegime.id.in_(rid for rid in regime_ids if rid in valid_ids))
        .all()
    )
    db.commit()
    db.refresh(item)
    return item
