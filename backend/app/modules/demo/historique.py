"""
L'historique de chiffres d'un établissement de démonstration.

Un tableau de bord manager est fait de chiffres : ventes du jour, temps
d'attente moyen, délai par étape, commandes par serveur, plats les plus
vendus, heures de pointe, et surtout la page de preuve qui compare une
semaine à la précédente. Ouvert sur un établissement créé à l'instant, il les
affiche tous à zéro — un restaurateur à qui l'on montre ça ne voit pas un
produit, il voit un écran vide, et aucune de ces fonctionnalités n'existe
pour lui.

Ce module pose donc, à la création de la démo, deux semaines de service :
sept jours affichés par défaut sur `/dashboard/preuve` et les sept jours de
comparaison juste avant.

**Deux garde-fous, à ne jamais lever :**

1. Ces chiffres ne sont écrits que sur un établissement `is_demo` (garde en
   tête de `poser_historique`). Un vrai restaurant ne doit jamais voir une
   commande qu'il n'a pas prise — c'est exactement le « chiffre inventé »
   que `ROADMAP.md` §23.2 interdit, et la mesure est la seule chose que
   Tawla a à vendre.
2. Ils sortent des agrégats de l'opérateur (`platform_admin/service.py`) :
   sans ça, le GMV et le taux d'annulation que Wassim lit sur `/admin`
   seraient ceux de visiteurs de passage.

Volontairement **sans aléa** : deux profils fixes, un cycle de paniers, et
une gigue calculée à partir du rang de la commande. Une démo tirée au hasard
peut sortir une semaine « après » moins bonne que la semaine « avant » — la
pastille d'écart passe alors au rouge devant le restaurateur, et le test qui
protège cette propriété devient instable. Ici l'écart est structurel : mêmes
paniers de base des deux côtés, des délais qui ne se chevauchent pas, et des
annulations comptées, pas tirées.
"""
from dataclasses import dataclass
from datetime import date as date_type
from datetime import datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.dates import service_day_start
from app.core.invoice_number import format_invoice_number
from app.core.markets import Market
from app.modules.menu.models import MenuItem, MenuSuggestion
from app.modules.orders.models import (
    InvoiceCounter,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.modules.staff.models import Staff
from app.modules.tables.models import Table
from app.modules.tenants.models import Restaurant

# Quatorze jours : les sept que `/dashboard/preuve` affiche par défaut, plus
# les sept de la période de comparaison qu'il place en face. En dessous, la
# colonne « avant » de la page de preuve reste vide, et c'est précisément la
# page qui se montre à un restaurateur.
JOURS_HISTORIQUE = 14

# Couverts servis un jour de semaine donné, lundi -> dimanche. Ordre de
# grandeur d'un établissement de quartier : creux en début de semaine, pic le
# vendredi et le samedi soir.
VOLUME_PAR_JOUR = (12, 11, 12, 14, 18, 22, 15)

SERVICE_MIDI = (time(11, 30), time(14, 15))
SERVICE_SOIR = (time(18, 45), time(22, 30))
PART_MIDI = 0.4

# Plancher de commandes pour la journée en cours quand la démo s'ouvre avant
# ou pendant le premier service : sans lui, « Ventes du jour » — le chiffre en
# gros caractères du tableau de bord — s'affiche à zéro selon l'heure à
# laquelle le restaurateur clique, ce qui est exactement ce qu'on cherche à
# éviter.
MINIMUM_AUJOURDHUI = 6

# Temps qu'une commande met à traverser tout le cycle, de la validation du
# panier à l'encaissement (majorant des étapes ci-dessous, profil APRES).
# La journée en cours s'arrête là : une commande passée il y a cinq minutes et
# déjà « servie et payée » porterait un `paid_at` dans le futur — invraisemblable
# sur l'écran serveur, et faux dans « Ventes du jour ». Les dernières minutes
# sont représentées par les commandes encore en cours (`_commandes_en_cours`),
# qui sont justement là pour ça.
DUREE_CYCLE = timedelta(minutes=45)


@dataclass(frozen=True)
class Profil:
    """
    Ce qui distingue la semaine de comparaison de la semaine affichée.

    Les trois délais sont ceux que le produit prétend réduire, et la page de
    preuve les additionne en un seul chiffre (commande -> cuisine). Les
    fourchettes des deux profils ne se chevauchent pas : l'amélioration est
    lisible sans dépendre d'un tirage.
    """

    facteur_volume: float
    # Une commande annulée toutes les N. Plus aucun écran ne montre ce
    # compteur au restaurateur (retiré du produit le 2026-09-09, voir
    # `stats/service.py::cancelled_orders`), mais un service sans la moindre
    # annulation n'existe pas : elles restent ici parce qu'elles sortent de la
    # recette et du panier moyen, exactement comme en production. Un pas
    # plutôt qu'une part : l'arrondi d'une part faible sur une journée de
    # quinze couverts donnerait zéro annulation toute la semaine.
    annulee_toutes_les: int
    # Secondes, de la validation du panier à la prise en charge par un serveur.
    prise_en_charge: tuple[int, int]
    # Secondes, de la prise en charge à la confirmation avec la table.
    confirmation: tuple[int, int]
    # Secondes, de la confirmation à l'envoi sur l'écran cuisine.
    envoi_cuisine: tuple[int, int]
    # Commandes sur treize où le client a accepté une suggestion « avec ce
    # plat » : c'est ce couple de chiffres qui produit l'argument « +X % de
    # panier moyen » sur la page de preuve. Treize parce que c'est premier
    # avec le cycle des six paniers (voir `_avec_suggestion`) : autrement les
    # suggestions retombent toujours sur les mêmes paniers, et l'écart affiché
    # mesure la composition du panier au lieu de la suggestion — jusqu'à
    # l'inverser sur la semaine de comparaison, où elles sont rares.
    suggestions_sur_treize: int


AVANT = Profil(
    facteur_volume=1.0,
    annulee_toutes_les=16,
    prise_en_charge=(110, 260),
    confirmation=(15, 45),
    envoi_cuisine=(30, 90),
    suggestions_sur_treize=1,
)

APRES = Profil(
    facteur_volume=1.2,
    annulee_toutes_les=55,
    prise_en_charge=(30, 80),
    confirmation=(8, 20),
    envoi_cuisine=(12, 35),
    suggestions_sur_treize=6,
)

# Un panier = des articles désignés par leur catégorie et un décalage dans
# cette catégorie, jamais par un nom : la carte tunisienne et la carte
# française n'ont ni les mêmes plats ni le même nombre d'articles, et une
# carte modifiée pendant la démo ne doit pas casser la génération.
PANIERS: tuple[tuple[tuple[str, int, int], ...], ...] = (
    (("Plats", 0, 1), ("Boissons", 0, 1)),
    (("Entrées", 0, 1), ("Plats", 1, 1), ("Boissons", 1, 2)),
    (("Plats", 0, 2), ("Boissons", 1, 2)),
    (("Entrées", 1, 1), ("Plats", 0, 1)),
    (("Plats", 1, 1), ("Desserts", 0, 1), ("Boissons", 0, 1)),
    (("Entrées", 0, 2), ("Plats", 1, 2), ("Boissons", 0, 2)),
)

# La ligne ajoutée quand le client accepte la suggestion affichée sous le plat.
SUGGESTION = ("Desserts", 0, 1)

# Étapes en cuisine, en secondes — communes aux deux profils : Tawla ne
# prétend pas faire cuire plus vite, seulement raccourcir le trajet de la
# commande jusqu'au piano.
PREPARATION = (30, 150)
CUISSON = (420, 900)
SERVICE = (60, 240)
ENCAISSEMENT = (180, 900)


def _entre(rang: int, bornes: tuple[int, int], variante: int = 0) -> int:
    """
    Une valeur reproductible dans une fourchette, dispersée par deux nombres
    premiers. Remplace `random` : voir l'en-tête du module — la démo doit
    raconter deux fois la même histoire.
    """
    mini, maxi = bornes
    if maxi <= mini:
        return mini
    return mini + (rang * 7919 + variante * 104729) % (maxi - mini + 1)


def _articles_par_categorie(articles: list[MenuItem]) -> dict[str, list[MenuItem]]:
    par_categorie: dict[str, list[MenuItem]] = {}
    for article in articles:
        par_categorie.setdefault(article.category or "Plats", []).append(article)
    return par_categorie


def _article(
    par_categorie: dict[str, list[MenuItem]], tous: list[MenuItem], categorie: str, decalage: int
) -> MenuItem:
    """L'article visé, ou n'importe lequel : une carte sans desserts ne doit
    pas empêcher une démo de s'ouvrir."""
    choix = par_categorie.get(categorie) or tous
    return choix[decalage % len(choix)]


def _creneaux(
    jour: date_type, debut: time, fin: time, nombre: int, market: Market, variante: int
) -> list[datetime]:
    """Horaires de commande étalés sur un service, en UTC."""
    if nombre <= 0:
        return []
    ouverture = datetime.combine(jour, debut, tzinfo=market.timezone)
    fermeture = datetime.combine(jour, fin, tzinfo=market.timezone)
    pas = (fermeture - ouverture) / nombre
    return [
        (ouverture + pas * rang + timedelta(seconds=_entre(rang, (0, 240), variante))).astimezone(timezone.utc)
        for rang in range(nombre)
    ]


def _horaires_du_jour(jour: date_type, volume: int, market: Market) -> list[datetime]:
    midi = round(volume * PART_MIDI)
    return sorted(
        _creneaux(jour, *SERVICE_MIDI, midi, market, variante=1)
        + _creneaux(jour, *SERVICE_SOIR, volume - midi, market, variante=2)
    )


def _horaires_aujourdhui(
    jour: date_type, volume: int, market: Market, maintenant: datetime
) -> list[datetime]:
    """
    La journée en cours s'arrête à l'heure qu'il est : une commande servie
    dans une heure ferait mentir « Ventes du jour » et l'histogramme des
    heures de pointe.

    Quand la démo s'ouvre avant le service (ou pendant le tout début du
    premier), les créneaux normaux ne suffisent pas : on replie sur les
    dernières heures écoulées de la journée de service. Un service à 6 h du
    matin n'a rien de réaliste, mais un tableau de bord à zéro devant un
    restaurateur est pire. À l'ouverture même de la journée de service (avant
    6 h du matin), il ne reste rien à replier : la journée est réellement
    vide, et ce sont les commandes en cours et l'historique de la veille qui
    portent la démonstration.
    """
    limite = maintenant - DUREE_CYCLE
    horaires = [heure for heure in _horaires_du_jour(jour, volume, market) if heure <= limite]
    if len(horaires) >= MINIMUM_AUJOURDHUI:
        return horaires

    debut = max(service_day_start(maintenant, market), maintenant - timedelta(hours=6))
    if limite <= debut:
        return horaires
    pas = (limite - debut) / MINIMUM_AUJOURDHUI
    return [debut + pas * rang for rang in range(MINIMUM_AUJOURDHUI)]


def _avec_suggestion(rang: int, profil: Profil) -> bool:
    """
    Réparti, jamais tiré : c'est ce qui rend l'écart entre les deux semaines
    structurel plutôt que chanceux (voir l'en-tête du module).

    Treize est premier avec le cycle des six paniers : les suggestions
    tournent donc sur tous les paniers, et l'écart de panier moyen affiché
    vaut le prix de la ligne suggérée — pas celui d'un panier plus cher.
    """
    return rang % 13 < profil.suggestions_sur_treize


def _numero_de_facture(
    compteurs: dict[int, InvoiceCounter], db: Session, restaurant_id: int, annee: int
) -> str:
    """
    Même format et même règle de continuité que `core/invoice_number.py`
    (séquence par restaurant et par millésime), mais posée en une passe : la
    fonction de production verrouille et `flush()` à chaque paiement, ce qui
    n'a pas de sens pour deux cents commandes écrites d'un bloc.
    """
    compteur = compteurs.get(annee)
    if compteur is None:
        compteur = InvoiceCounter(restaurant_id=restaurant_id, year=annee, last_number=0)
        db.add(compteur)
        compteurs[annee] = compteur
    compteur.last_number += 1
    return format_invoice_number(annee, compteur.last_number)


def poser_historique(
    db: Session,
    restaurant: Restaurant,
    tables: list[Table],
    serveurs: list[Staff],
    articles: list[MenuItem],
    market: Market,
    maintenant: datetime | None = None,
) -> int:
    """
    Écrit deux semaines de service sur un établissement de démonstration, et
    renvoie le nombre de commandes créées.

    Suppose que `restaurant`, `tables`, `serveurs` et `articles` ont déjà un
    identifiant (un `flush()` suffit) ; ne commite pas — l'appelant reste
    maître de sa transaction, comme partout ailleurs dans le module.
    """
    if not restaurant.is_demo:
        # Garde-fou volontairement redondant avec l'appelant : ces chiffres
        # n'ont jamais été mesurés. Sur un vrai restaurant ils seraient un
        # mensonge, et sur la page de preuve un mensonge signé.
        raise ValueError(f"restaurant {restaurant.id} n'est pas une démo — historique refusé")
    if not tables or not serveurs or not articles:
        return 0

    maintenant = maintenant or datetime.now(timezone.utc)
    par_categorie = _articles_par_categorie(articles)
    aujourdhui = maintenant.astimezone(market.timezone).date()
    compteurs: dict[int, InvoiceCounter] = {}

    commandes: list[Order] = []
    # Les lignes ne peuvent être construites qu'une fois les commandes
    # identifiées : on garde le panier de chacune de côté, et on écrit les
    # lignes après un seul flush.
    paniers: list[tuple[Order, list[tuple[MenuItem, int, bool]]]] = []
    rang_global = 0

    for anciennete in range(JOURS_HISTORIQUE - 1, -1, -1):
        jour = aujourdhui - timedelta(days=anciennete)
        profil = AVANT if anciennete >= JOURS_HISTORIQUE // 2 else APRES
        volume = max(1, round(VOLUME_PAR_JOUR[jour.weekday()] * profil.facteur_volume))
        horaires = (
            _horaires_aujourdhui(jour, volume, market, maintenant)
            if anciennete == 0
            else _horaires_du_jour(jour, volume, market)
        )
        if not horaires:
            continue

        for passee_a in horaires:
            rang_global += 1
            panier: list[tuple[MenuItem, int, bool]] = [
                (_article(par_categorie, articles, categorie, decalage), quantite, False)
                for categorie, decalage, quantite in PANIERS[rang_global % len(PANIERS)]
            ]
            if _avec_suggestion(rang_global, profil):
                categorie, decalage, quantite = SUGGESTION
                panier.append((_article(par_categorie, articles, categorie, decalage), quantite, True))

            # Trois commandes sur cinq au premier serveur : le manager ouvre
            # « commandes par serveur » pour voir un écart, pas deux colonnes
            # jumelles.
            serveur = serveurs[0] if rang_global % 5 < 3 else serveurs[-1]
            table = tables[rang_global % len(tables)]

            commande = Order(
                restaurant_id=restaurant.id,
                table_id=table.id,
                created_at=passee_a,
                taken_by_staff_id=serveur.id,
                taken_at=passee_a + timedelta(seconds=_entre(rang_global, profil.prise_en_charge)),
            )

            if rang_global % profil.annulee_toutes_les == 0:
                # Une commande annulée l'est avant la cuisine — sinon le plat
                # est parti, et l'annuler ne veut plus rien dire. Elle ne
                # porte donc ni envoi cuisine ni paiement, ce qui la sort de
                # la recette et du panier moyen, comme en production.
                commande.status = OrderStatus.CANCELLED
                commandes.append(commande)
                paniers.append((commande, panier))
                continue

            commande.confirmed_at = commande.taken_at + timedelta(
                seconds=_entre(rang_global, profil.confirmation)
            )
            commande.sent_to_kitchen_at = commande.confirmed_at + timedelta(
                seconds=_entre(rang_global, profil.envoi_cuisine)
            )
            commande.preparation_started_at = commande.sent_to_kitchen_at + timedelta(
                seconds=_entre(rang_global, PREPARATION)
            )
            commande.ready_at = commande.preparation_started_at + timedelta(
                seconds=_entre(rang_global, CUISSON)
            )
            commande.served_at = commande.ready_at + timedelta(seconds=_entre(rang_global, SERVICE))
            commande.paid_at = commande.served_at + timedelta(seconds=_entre(rang_global, ENCAISSEMENT))
            commande.status = OrderStatus.SERVED
            commande.payment_status = PaymentStatus.PAID
            commande.payment_method = (
                PaymentMethod.CARD,
                PaymentMethod.CASH,
                PaymentMethod.CARD_TERMINAL,
                PaymentMethod.CASH,
            )[rang_global % 4]

            total = sum(float(article.price) * quantite for article, quantite, _ in panier)
            if commande.payment_method == PaymentMethod.CARD:
                # Le pourboire n'existe que sur le paiement en ligne, seul
                # endroit où le client le saisit — c'est ce qui alimente la
                # colonne « pourboires » du rapport d'équipe.
                commande.tip_amount = round(total * 0.07, 2)
            if market.invoice_threshold is not None:
                commande.invoice_number = _numero_de_facture(
                    compteurs, db, restaurant.id, service_day_start(commande.paid_at, market).year
                )

            commandes.append(commande)
            paniers.append((commande, panier))

    for commande, panier in _commandes_en_cours(
        restaurant, tables, serveurs, articles, par_categorie, maintenant
    ):
        commandes.append(commande)
        paniers.append((commande, panier))

    db.add_all(commandes)
    db.flush()

    db.add_all(
        [
            OrderItem(
                order_id=commande.id,
                menu_item_id=article.id,
                menu_item_name=article.name,
                unit_price=article.price,
                vat_category=article.vat_category,
                quantity=quantite,
                from_suggestion=suggeree,
            )
            for commande, panier in paniers
            for article, quantite, suggeree in panier
        ]
    )
    return len(commandes)


def _commandes_en_cours(
    restaurant: Restaurant,
    tables: list[Table],
    serveurs: list[Staff],
    articles: list[MenuItem],
    par_categorie: dict[str, list[MenuItem]],
    maintenant: datetime,
) -> list[tuple[Order, list[tuple[MenuItem, int, bool]]]]:
    """
    Quatre commandes encore en vie à l'instant où la démo s'ouvre : une qui
    attend un serveur, une qui vient de partir en cuisine, une en préparation,
    une prête à servir — une étape du flux par commande.

    Sans elles, « Commandes en cours » et « Tables en charge en ce moment »
    restent à zéro sur le tableau de bord, l'écran serveur et l'écran cuisine
    s'ouvrent vides, et le visiteur doit d'abord passer une commande lui-même
    pour voir à quoi ressemble un service. Quatre suffisent : la démonstration
    consiste à en ajouter une cinquième depuis son téléphone, elle doit rester
    visible au milieu des autres.
    """
    en_cours: list[tuple[Order, list[tuple[MenuItem, int, bool]]]] = []
    scenarios = (
        (OrderStatus.PENDING_CONFIRMATION, 4, None),
        # Celle-ci alimente l'onglet « À préparer » de l'écran cuisine, celui
        # qui s'ouvre par défaut : sans elle, la cuisine accueille le
        # restaurateur sur « Rien en attente ».
        (OrderStatus.SENT_TO_KITCHEN, 8, serveurs[0]),
        (OrderStatus.IN_PREPARATION, 13, serveurs[-1]),
        (OrderStatus.READY, 21, serveurs[-1]),
    )

    for rang, (statut, minutes, serveur) in enumerate(scenarios):
        passee_a = maintenant - timedelta(minutes=minutes)
        commande = Order(
            restaurant_id=restaurant.id,
            table_id=tables[rang % len(tables)].id,
            created_at=passee_a,
            status=statut,
        )
        if serveur is not None:
            commande.taken_by_staff_id = serveur.id
            commande.taken_at = passee_a + timedelta(seconds=_entre(rang, APRES.prise_en_charge))
            commande.confirmed_at = commande.taken_at + timedelta(seconds=_entre(rang, APRES.confirmation))
            commande.sent_to_kitchen_at = commande.confirmed_at + timedelta(
                seconds=_entre(rang, APRES.envoi_cuisine)
            )
            if statut != OrderStatus.SENT_TO_KITCHEN:
                commande.preparation_started_at = commande.sent_to_kitchen_at + timedelta(seconds=90)
            if statut == OrderStatus.READY:
                commande.ready_at = commande.preparation_started_at + timedelta(seconds=480)

        panier = [
            (_article(par_categorie, articles, categorie, decalage), quantite, False)
            for categorie, decalage, quantite in PANIERS[rang % len(PANIERS)]
        ]
        en_cours.append((commande, panier))

    return en_cours


def poser_suggestions(db: Session, restaurant: Restaurant, articles: list[MenuItem]) -> None:
    """
    Deux suggestions « avec ce plat » sur la carte de démonstration.

    Les commandes de l'historique portent des lignes marquées
    `from_suggestion` : sans la suggestion correspondante sur la carte, le
    restaurateur lit « +X % de panier moyen » sur la page de preuve puis ne
    trouve nulle part la fonctionnalité qui produit ce chiffre.
    """
    par_categorie = _articles_par_categorie(articles)
    plats = par_categorie.get("Plats") or articles
    accompagnements = (par_categorie.get("Desserts") or []) + (par_categorie.get("Boissons") or [])
    if not accompagnements:
        return

    for rang, plat in enumerate(plats[:2]):
        suggere = accompagnements[rang % len(accompagnements)]
        if suggere.id == plat.id:
            continue
        db.add(
            MenuSuggestion(
                restaurant_id=restaurant.id, menu_item_id=plat.id, suggested_item_id=suggere.id
            )
        )
