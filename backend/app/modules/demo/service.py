"""
Établissements de démonstration jetables.

Un seul compte de démo partagé était la solution évidente, et elle est
mauvaise : les connexions temps réel sont groupées par `(restaurant_id,
channel)` (`notifications/manager.py`), donc deux restaurateurs en démo au
même moment verraient chacun les commandes de l'autre tomber sur son écran
cuisine. S'ajoutent le vandalisme — un compte manager en écriture dont le mot
de passe est public — et les numéros de fidélité d'un visiteur lisibles par le
suivant.

Le produit est multi-tenant sur `restaurant_id` depuis le premier jour : il
suffit donc de donner à chaque visiteur **son** établissement. L'isolation
n'est pas à écrire, elle est déjà là et déjà testée.

Ces établissements portent `is_demo` et une date d'expiration, et sont
supprimés en entier — pas anonymisés : rien de ce qu'ils contiennent n'a de
valeur au-delà de la démonstration.
"""
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.dates import as_utc
from app.core.logging import log_event
from app.core.markets import current_market
from app.modules.loyalty.models import LoyaltyMember
from app.modules.menu.models import (
    MenuFormula,
    MenuFormulaSlot,
    MenuItem,
    MenuItemOptionChoice,
    MenuItemOptionGroup,
    MenuSuggestion,
    menu_formula_slot_items,
)
from app.modules.menu.schemas import _default_is_halal
from app.modules.orders.models import Order, OrderFormula, OrderFormulaSelection, OrderItem, OrderItemOptionChoice
from app.modules.staff.models import Staff, StaffRole
from app.modules.staff.security import hash_password
from app.modules.stats.models import DashboardView
from app.modules.tables.models import Table
from app.modules.tenants.models import Restaurant, SubscriptionTier
from app.modules.waiter_calls.models import WaiterCall

import logging

logger = logging.getLogger("demo")

# Deux heures : plus long qu'une démonstration (deux minutes) sans obliger
# qui prend son temps à recommencer. C'est aussi la durée de conservation
# annoncée dans la politique de confidentialité — les deux doivent bouger
# ensemble.
DUREE_DEMO = timedelta(hours=2)

# Plafond de démos vivantes simultanées. Une route publique qui écrit en base
# doit avoir une borne dure en plus de la limite par IP : sans elle, un script
# suffit à remplir la base. 100 démos = bien plus que ce qu'un lancement
# tunisien produira, et 100 lignes `restaurants` ne coûtent rien.
PLAFOND_DEMOS = 100

# La carte de démonstration, alignée sur `scripts/seed_demo.py` : un
# restaurateur qui voit la démo en ligne puis en rendez-vous doit reconnaître
# les mêmes plats.
NOM_TN = "Dar Chaabane"
CARTE_TN = [
    ("Salade méchouia", "Entrées", 6.0),
    ("Brik à l'œuf", "Entrées", 4.5),
    ("Couscous au poisson", "Plats", 22.0),
    ("Grillade mixte", "Plats", 26.0),
    ("Baklawa", "Desserts", 5.0),
    ("Thé à la menthe", "Boissons", 3.0),
]

EQUIPE_TN = [
    ("Amine (manager)", StaffRole.MANAGER),
    ("Sami (serveur)", StaffRole.WAITER),
    ("Karim (cuisine)", StaffRole.KITCHEN),
]

# F5 (MARCHE_FRANCE.md §3.2) : « un restaurateur français qui voit une carte
# tunisienne en démo comprend que le produit n'est pas pour lui, en trois
# secondes ». Segment prioritaire identifié en F1 — brasserie/bistrot de
# quartier (§C3) — avec sa formule du jour (F5-A3) et sa carte des vins,
# les deux différenciateurs explicitement demandés par le dossier.
NOM_FR = "Brasserie du Central"
CARTE_FR = [
    ("Salade César", "Entrées", 8.0),
    ("Soupe à l'oignon gratinée", "Entrées", 7.5),
    ("Steak-frites", "Plats", 19.0),
    ("Poulet rôti, pommes grenaille", "Plats", 17.5),
    ("Tarte tatin", "Desserts", 7.0),
    ("Mousse au chocolat maison", "Desserts", 6.0),
    ("Café", "Boissons", 2.5),
    ("Verre de côtes-du-rhône", "Vins", 5.5),
]

EQUIPE_FR = [
    ("Camille (manager)", StaffRole.MANAGER),
    ("Léa (serveuse)", StaffRole.WAITER),
    ("Hugo (cuisine)", StaffRole.KITCHEN),
]


def _profil_demo() -> tuple[str, list[tuple[str, str, float]], list[tuple[str, StaffRole]]]:
    """Nom, carte et équipe à monter — décidés par le marché servi par CE
    déploiement (`current_market()`, jamais par requête), même principe que
    `_default_is_halal` (menu/schemas.py)."""
    if current_market().code == "fr":
        return NOM_FR, CARTE_FR, EQUIPE_FR
    return NOM_TN, CARTE_TN, EQUIPE_TN


def demos_vivantes(db: Session) -> int:
    return (
        db.query(Restaurant)
        .filter(Restaurant.is_demo.is_(True), Restaurant.demo_expires_at > datetime.now(timezone.utc))
        .count()
    )


def demos_expirees(db: Session) -> list[Restaurant]:
    return list(
        db.scalars(
            select(Restaurant).where(
                Restaurant.is_demo.is_(True),
                Restaurant.demo_expires_at.is_not(None),
                Restaurant.demo_expires_at <= datetime.now(timezone.utc),
            )
        )
    )


def supprimer_demo(db: Session, restaurant: Restaurant) -> None:
    """
    Efface un établissement de démonstration et tout ce qui pend dessous.

    L'ordre suit les clés étrangères, des feuilles vers la racine : les lignes
    de commande avant les commandes, tout ce qui référence une table ou un
    compte avant eux. Se tromper d'ordre ne corrompt rien — Postgres refuse —
    mais laisse la purge inachevée.

    Garde-fou volontairement redondant : cette fonction supprime un
    établissement entier, elle refuse de toucher autre chose qu'une démo.
    """
    if not restaurant.is_demo:
        raise ValueError(f"restaurant {restaurant.id} n'est pas une démo — suppression refusée")

    rid = restaurant.id
    commandes = select(Order.id).where(Order.restaurant_id == rid)
    formules_commandees = select(OrderFormula.id).where(OrderFormula.order_id.in_(commandes))
    db.query(OrderFormulaSelection).filter(
        OrderFormulaSelection.order_formula_id.in_(formules_commandees)
    ).delete(synchronize_session=False)
    db.query(OrderFormula).filter(OrderFormula.order_id.in_(commandes)).delete(synchronize_session=False)
    lignes_commande = select(OrderItem.id).where(OrderItem.order_id.in_(commandes))
    db.query(OrderItemOptionChoice).filter(
        OrderItemOptionChoice.order_item_id.in_(lignes_commande)
    ).delete(synchronize_session=False)
    db.query(OrderItem).filter(OrderItem.order_id.in_(commandes)).delete(synchronize_session=False)
    db.query(Order).filter(Order.restaurant_id == rid).delete(synchronize_session=False)
    db.query(WaiterCall).filter(WaiterCall.restaurant_id == rid).delete(synchronize_session=False)
    db.query(MenuSuggestion).filter(MenuSuggestion.restaurant_id == rid).delete(synchronize_session=False)

    # F5-A3 : les formules référencent des articles (table de liaison) —
    # à effacer avant les articles eux-mêmes, sinon la contrainte de clé
    # étrangère refuse la suppression de MenuItem.
    formules = select(MenuFormula.id).where(MenuFormula.restaurant_id == rid)
    etapes = select(MenuFormulaSlot.id).where(MenuFormulaSlot.formula_id.in_(formules))
    db.execute(delete(menu_formula_slot_items).where(menu_formula_slot_items.c.slot_id.in_(etapes)))
    db.query(MenuFormulaSlot).filter(MenuFormulaSlot.formula_id.in_(formules)).delete(synchronize_session=False)
    db.query(MenuFormula).filter(MenuFormula.restaurant_id == rid).delete(synchronize_session=False)

    # F5-A2 : idem pour les groupes d'options d'un article — aucun créé par
    # la démo aujourd'hui, mais un manager pourrait en ajouter pendant sa
    # session de 2h, et la purge doit rester valide dans ce cas.
    groupes = select(MenuItemOptionGroup.id).where(MenuItemOptionGroup.restaurant_id == rid)
    db.query(MenuItemOptionChoice).filter(MenuItemOptionChoice.group_id.in_(groupes)).delete(
        synchronize_session=False
    )
    db.query(MenuItemOptionGroup).filter(MenuItemOptionGroup.restaurant_id == rid).delete(
        synchronize_session=False
    )

    db.query(MenuItem).filter(MenuItem.restaurant_id == rid).delete(synchronize_session=False)
    db.query(LoyaltyMember).filter(LoyaltyMember.restaurant_id == rid).delete(synchronize_session=False)
    db.query(DashboardView).filter(DashboardView.restaurant_id == rid).delete(synchronize_session=False)
    db.query(Table).filter(Table.restaurant_id == rid).delete(synchronize_session=False)
    db.query(Staff).filter(Staff.restaurant_id == rid).delete(synchronize_session=False)
    db.query(Restaurant).filter(Restaurant.id == rid).delete(synchronize_session=False)
    db.commit()
    log_event(logger, "demo.supprimee", restaurant_id=rid)


def purger_demos_expirees(db: Session) -> int:
    """
    Supprime les démos échues. Appelée à chaque création — la démo se nettoie
    donc toute seule, sans dépendre d'un ordonnanceur qui pourrait ne jamais
    être installé. `scripts/purge_donnees_personnelles.py` l'appelle aussi,
    pour que la purge manuelle reste le point d'entrée unique documenté.
    """
    expirees = demos_expirees(db)
    for restaurant in expirees:
        supprimer_demo(db, restaurant)
    return len(expirees)


def creer_demo(db: Session) -> tuple[Restaurant, dict[StaffRole, Staff], Table]:
    """
    Monte un établissement complet : l'équipe, trois tables, une carte.

    Palier Pro et compte actif : la démonstration doit montrer le produit que
    l'on vend (paiement carte, fidélité, plan de salle), pas un écran
    d'activation. C'est le seul chemin qui crée un restaurant utilisable sans
    paiement — d'où `is_demo`, qui le distingue d'un vrai client à vie.

    Renvoie les trois comptes plutôt que le seul manager : `router.py` émet un
    jeton pour chacun, pour qu'un lien puisse ouvrir l'écran serveur ou
    cuisine, déjà connecté, sur un autre appareil que celui qui a ouvert la
    démo — les comptes serveur et cuisine ont un mot de passe généré
    aléatoirement ci-dessous, jamais révélé, donc jamais saisissable à la main.
    """
    purger_demos_expirees(db)

    nom_etablissement, carte, equipe = _profil_demo()
    suffixe = secrets.token_urlsafe(8).lower().replace("_", "").replace("-", "")
    expiration = datetime.now(timezone.utc) + DUREE_DEMO

    restaurant = Restaurant(
        name=f"{nom_etablissement} (démo)",
        slug=f"demo-{suffixe}",
        is_demo=True,
        demo_expires_at=expiration,
        subscription_tier=SubscriptionTier.PRO,
        is_active=True,
        # Jamais payé, et il ne faut pas laisser croire le contraire : le
        # rappel de paiement n'a pas de sens sur une démo, mais l'écran admin
        # ne doit pas la compter comme un client acquis.
        has_paid_for_subscription=False,
        subscription_period_end=expiration,
    )
    db.add(restaurant)
    db.flush()

    comptes = []
    for nom, role in equipe:
        compte = Staff(
            restaurant_id=restaurant.id,
            name=nom,
            role=role,
            # Adresse jetable et unique : `Staff.email` est unique sur toute
            # la base, deux démos simultanées ne doivent pas se télescoper.
            email=f"{role.value}@{restaurant.slug}.demo.tawla.tn",
            password_hash=hash_password(secrets.token_urlsafe(16)),
        )
        db.add(compte)
        comptes.append(compte)

    tables = [Table(restaurant_id=restaurant.id, label=f"Table {i}") for i in (1, 2, 3)]
    for table in tables:
        db.add(table)

    articles_par_nom: dict[str, MenuItem] = {}
    for nom, categorie, prix in carte:
        article = MenuItem(
            restaurant_id=restaurant.id,
            name=nom,
            category=categorie,
            price=prix,
            # Construit directement en ORM, donc PASSE À CÔTÉ du défaut
            # market-aware de MenuItemCreate (menu/schemas.py::_default_is_halal)
            # — sans cette ligne, une brasserie française (steak-frites, vin)
            # se retrouvait affichée "halal" par défaut (F5-A6).
            is_halal=_default_is_halal(),
        )
        db.add(article)
        articles_par_nom[nom] = article

    # F5-A3 : la formule du jour est, avec la carte des vins, le
    # différenciateur explicitement demandé pour la démo française
    # (MARCHE_FRANCE.md §3.2) — sans elle, un restaurateur français ne voit
    # jamais le produit qui vend le mieux sur son propre marché.
    if current_market().code == "fr":
        db.flush()
        formule = MenuFormula(
            restaurant_id=restaurant.id,
            name="Formule du jour",
            price=19.5,
            slots=[
                MenuFormulaSlot(
                    name="Entrée",
                    display_order=0,
                    items=[articles_par_nom["Salade César"], articles_par_nom["Soupe à l'oignon gratinée"]],
                ),
                MenuFormulaSlot(
                    name="Plat",
                    display_order=1,
                    items=[articles_par_nom["Steak-frites"], articles_par_nom["Poulet rôti, pommes grenaille"]],
                ),
                MenuFormulaSlot(
                    name="Dessert",
                    display_order=2,
                    items=[articles_par_nom["Tarte tatin"], articles_par_nom["Mousse au chocolat maison"]],
                ),
            ],
        )
        db.add(formule)

    db.commit()
    db.refresh(restaurant)
    for compte in comptes:
        db.refresh(compte)
    db.refresh(tables[0])

    par_role = {compte.role: compte for compte in comptes}
    log_event(logger, "demo.creee", restaurant_id=restaurant.id, table_id=tables[0].id)
    return restaurant, par_role, tables[0]


def expiration_restante(restaurant: Restaurant) -> datetime:
    return as_utc(restaurant.demo_expires_at)
