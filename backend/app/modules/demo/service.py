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

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dates import as_utc
from app.core.logging import log_event
from app.modules.loyalty.models import LoyaltyMember
from app.modules.menu.models import MenuItem, MenuSuggestion
from app.modules.orders.models import Order, OrderItem
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
CARTE = [
    ("Salade méchouia", "Entrées", 6.0),
    ("Brik à l'œuf", "Entrées", 4.5),
    ("Couscous au poisson", "Plats", 22.0),
    ("Grillade mixte", "Plats", 26.0),
    ("Baklawa", "Desserts", 5.0),
    ("Thé à la menthe", "Boissons", 3.0),
]

EQUIPE = [
    ("Amine (manager)", StaffRole.MANAGER),
    ("Sami (serveur)", StaffRole.WAITER),
    ("Karim (cuisine)", StaffRole.KITCHEN),
]


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
    db.query(OrderItem).filter(OrderItem.order_id.in_(commandes)).delete(synchronize_session=False)
    db.query(Order).filter(Order.restaurant_id == rid).delete(synchronize_session=False)
    db.query(WaiterCall).filter(WaiterCall.restaurant_id == rid).delete(synchronize_session=False)
    db.query(MenuSuggestion).filter(MenuSuggestion.restaurant_id == rid).delete(synchronize_session=False)
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


def creer_demo(db: Session) -> tuple[Restaurant, Staff, Table]:
    """
    Monte un établissement complet : l'équipe, trois tables, une carte.

    Palier Pro et compte actif : la démonstration doit montrer le produit que
    l'on vend (paiement carte, fidélité, plan de salle), pas un écran
    d'activation. C'est le seul chemin qui crée un restaurant utilisable sans
    paiement — d'où `is_demo`, qui le distingue d'un vrai client à vie.
    """
    purger_demos_expirees(db)

    suffixe = secrets.token_urlsafe(8).lower().replace("_", "").replace("-", "")
    expiration = datetime.now(timezone.utc) + DUREE_DEMO

    restaurant = Restaurant(
        name="Dar Chaabane (démo)",
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
    for nom, role in EQUIPE:
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

    for nom, categorie, prix in CARTE:
        db.add(MenuItem(restaurant_id=restaurant.id, name=nom, category=categorie, price=prix))

    db.commit()
    db.refresh(restaurant)
    for compte in comptes:
        db.refresh(compte)
    db.refresh(tables[0])

    manager = next(c for c in comptes if c.role is StaffRole.MANAGER)
    log_event(logger, "demo.creee", restaurant_id=restaurant.id, table_id=tables[0].id)
    return restaurant, manager, tables[0]


def expiration_restante(restaurant: Restaurant) -> datetime:
    return as_utc(restaurant.demo_expires_at)
