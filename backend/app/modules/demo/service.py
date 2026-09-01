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
from app.core.markets import Market, current_market
from app.modules.loyalty.models import LoyaltyMember
from app.modules.menu.models import MenuItem, MenuRegime, MenuSuggestion
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
# les mêmes plats. Un restaurateur français qui voit une carte tunisienne en
# démo comprend que le produit n'est pas pour lui, en trois secondes
# (MARCHE_FRANCE.md §3.2) — d'où une carte, une équipe et un nom d'établissement
# distincts par marché plutôt qu'une seule liste traduite.
NOM_DEMO = {"tn": "Dar Chaabane (démo)", "fr": "Brasserie du Vieux Marché (démo)"}

CARTE = [
    ("Salade méchouia", "Entrées", 6.0),
    ("Brik à l'œuf", "Entrées", 4.5),
    ("Couscous au poisson", "Plats", 22.0),
    ("Grillade mixte", "Plats", 26.0),
    ("Baklawa", "Desserts", 5.0),
    ("Thé à la menthe", "Boissons", 3.0),
]

# Brasserie française : formule du jour, structure entrée/plat/dessert, carte
# des vins — les deux catégories que la Tunisie n'a pas (étape 6, "Formules"
# et "Vins" dans lib/market.ts::menuCategories / core/markets.py équivalent).
CARTE_FR = [
    ("Soupe à l'oignon gratinée", "Entrées", 9.50),
    ("Terrine de campagne, cornichons", "Entrées", 8.50),
    ("Bavette à l'échalote, frites maison", "Plats", 19.50),
    ("Confit de canard, pommes sarladaises", "Plats", 22.00),
    ("Crème brûlée", "Desserts", 7.00),
    ("Tarte Tatin, crème fraîche", "Desserts", 7.50),
    ("Eau minérale", "Boissons", 3.50),
    ("Café gourmand", "Boissons", 6.50),
    ("Formule midi : entrée + plat, ou plat + dessert", "Formules", 18.90),
    ("Verre de côtes-du-rhône", "Vins", 5.50),
]

EQUIPE = [
    ("Amine (manager)", StaffRole.MANAGER),
    ("Sami (serveur)", StaffRole.WAITER),
    ("Karim (cuisine)", StaffRole.KITCHEN),
]

EQUIPE_FR = [
    ("Julie (manager)", StaffRole.MANAGER),
    ("Thomas (serveur)", StaffRole.WAITER),
    ("Nicolas (cuisine)", StaffRole.KITCHEN),
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
    # menu_item_regimes (la liaison) est en ondelete=CASCADE des deux côtés,
    # mais MenuRegime.restaurant_id ne l'est pas (menu/models.py) : sans cette
    # ligne, un régime créé pendant la démo (fonctionnalité Pro normalement
    # testée) bloque la suppression du restaurant à l'expiration, ce qui
    # bloque ensuite *toute* nouvelle démo derrière lui (purge à chaque
    # création, cf. `purger_demos_expirees`).
    db.query(MenuRegime).filter(MenuRegime.restaurant_id == rid).delete(synchronize_session=False)
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


def creer_demo(db: Session, market: Market = current_market) -> tuple[Restaurant, dict[StaffRole, Staff], Table]:
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

    `market` par défaut au marché du déploiement (`current_market`, France
    étape 7) — même patron que `format_money()` (`core/currency.py`) :
    l'appelant réel (`router.py`) ne le passe jamais, seuls les tests
    l'utilisent pour vérifier l'autre marché sans dépendre de `MARKET` au
    démarrage du process.
    """
    purger_demos_expirees(db)

    suffixe = secrets.token_urlsafe(8).lower().replace("_", "").replace("-", "")
    expiration = datetime.now(timezone.utc) + DUREE_DEMO
    carte = CARTE_FR if market.code == "fr" else CARTE
    equipe = EQUIPE_FR if market.code == "fr" else EQUIPE

    restaurant = Restaurant(
        name=NOM_DEMO[market.code],
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
            # Domaine par marché — jamais résolu ni envoyé nulle part (mot de
            # passe jamais révélé, cf. docstring), aucune dépendance à ce que
            # `tawla.fr` soit réellement réservé (F4, encore 🧑).
            email=f"{role.value}@{restaurant.slug}.demo.tawla.{market.code}",
            password_hash=hash_password(secrets.token_urlsafe(16)),
        )
        db.add(compte)
        comptes.append(compte)

    tables = [Table(restaurant_id=restaurant.id, label=f"Table {i}") for i in (1, 2, 3)]
    for table in tables:
        db.add(table)

    for nom, categorie, prix in carte:
        db.add(MenuItem(restaurant_id=restaurant.id, name=nom, category=categorie, price=prix))

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
