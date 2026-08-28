from datetime import date as date_type

from pydantic import BaseModel

from app.modules.staff.models import StaffRole


class TimingStats(BaseModel):
    """Moyennes en secondes — None si aucune commande n'a franchi cette étape ce jour-là."""

    avg_wait_confirmation_seconds: float | None
    avg_confirmation_to_kitchen_seconds: float | None
    avg_kitchen_to_served_seconds: float | None


class StaffPerformance(BaseModel):
    staff_id: int
    staff_name: str
    role: StaffRole
    orders_taken: int


class StaffActiveLoad(BaseModel):
    """
    Charge d'un serveur **en ce moment**, pas son cumul du jour
    (`StaffPerformance.orders_taken`) — combien de tables il a actuellement sur
    les bras (commandes prises en charge, pas encore servies ni annulées).

    Demande de Wassim (2026-08-28), à la place de « Commandes perdues » en tête
    du tableau de bord : le signal utile au quotidien n'est pas un compteur de
    ventes ratées, c'est de voir tout de suite qui est en train de se noyer.
    """

    staff_id: int
    staff_name: str
    role: StaffRole
    tables_count: int


class TopMenuItem(BaseModel):
    menu_item_name: str
    quantity: int


class HourlyCount(BaseModel):
    hour: int
    count: int


class DashboardStats(BaseModel):
    date: date_type
    # Les deux chiffres de tête (Phase 17.1, remaniés le 2026-08-28). La
    # recette est ce que le patron vient chercher tous les soirs ; le temps
    # d'attente moyen est posé juste à côté (voir `RecetteDuJour.tsx`) — un
    # signal opérationnel du jour même, pas un compteur de ventes ratées.
    # `cancelled_orders_today` a la même définition que `PeriodProof`, par
    # construction, mais n'est plus mis en avant en tête du tableau de bord.
    revenue_today: float
    cancelled_orders_today: int
    active_orders_count: int
    timing: TimingStats
    staff_performance: list[StaffPerformance]
    # Charge actuelle par serveur (2026-08-28) : combien de tables chacun a
    # sur les bras **en ce moment**, distinct de `staff_performance` qui
    # cumule la journée entière. Ne liste que les serveurs avec au moins une
    # commande active — pas de ligne à zéro pour toute l'équipe.
    staff_active_load: list[StaffActiveLoad]
    top_items: list[TopMenuItem]
    orders_by_hour: list[HourlyCount]


class KitchenTodayCount(BaseModel):
    date: date_type
    count: int


class PeriodProof(BaseModel):
    """
    Les trois seuls chiffres qui valent quelque chose devant un restaurateur ou
    un jury (Phase 13.3) : combien de commandes ont été annulées, combien de
    temps s'écoule entre la commande du client et son arrivée en cuisine, et
    quel est le panier moyen.

    Volontairement pas un quatrième indicateur. Le reste est du confort.
    """

    start: date_type
    end: date_type  # inclus

    orders_count: int

    # « Commande perdue » = commande annulée (`stats/service.py::
    # cancelled_orders`, décision de Wassim du 2026-08-28). Une commande
    # restée longtemps sans être prise en charge n'est plus comptée ici : elle
    # peut toujours aboutir, contrairement à une annulation. Ce délai reste
    # mesuré ailleurs (`TimingStats.avg_wait_confirmation_seconds`).
    cancelled_orders_count: int

    # Du panier validé par le client à l'arrivée sur l'écran cuisine. C'est le
    # délai que le produit prétend réduire — donc celui qu'il faut mesurer.
    avg_order_to_kitchen_seconds: float | None

    # Sur les commandes non annulées : une commande annulée n'a jamais été un
    # panier réel et tirerait la moyenne vers le bas sans rien dire du service.
    avg_basket_amount: float | None

    # Effet mesuré de la vente incitative (Phase 14.1) : le panier moyen des
    # commandes où le client a accepté au moins une suggestion, comparé à celui
    # des autres. C'est ce couple de chiffres qui produit l'argument
    # commercial — « +X % de panier moyen » — au lieu d'une intuition.
    orders_with_suggestion_count: int = 0
    avg_basket_with_suggestion: float | None = None
    avg_basket_without_suggestion: float | None = None


class StaffPeriodReport(BaseModel):
    """
    Ligne de rapport d'un membre de l'équipe sur une période.

    Sert à asseoir une prime de rendement, donc les chiffres doivent être ceux
    que le serveur peut reconnaître comme siens : les commandes qu'il a prises
    en charge, sa réactivité à les confirmer, et le montant qu'il a traité.
    Aucun classement, aucune note : le manager arbitre, l'outil compte.
    """

    staff_id: int
    staff_name: str
    role: StaffRole
    orders_taken: int
    # De la commande du client à sa prise en charge : c'est la part du délai qui
    # dépend réellement du serveur, contrairement au temps de cuisson.
    avg_seconds_to_claim: float | None
    total_amount_handled: float


class TeamReport(BaseModel):
    start: date_type
    end: date_type
    staff: list[StaffPeriodReport]


class ProofStats(BaseModel):
    """
    La période demandée et la période de même longueur qui la précède
    immédiatement : sans « avant », les trois chiffres ne prouvent rien.
    """

    current: PeriodProof
    previous: PeriodProof


class MyShift(BaseModel):
    """
    Ce qu'un serveur voit de sa propre soirée (Phase 17.3).

    Ne porte **que** ses chiffres : aucun nom de collègue, aucun classement,
    aucun total d'équipe. Ce qui n'est pas envoyé ne peut pas fuiter dans une
    future interface — et un serveur qui se découvre comparé publiquement à ses
    collègues contourne l'outil dès le service suivant.
    """

    date: date_type
    orders_taken: int
    total_amount_handled: float
    # `None` = aucune commande prise, ce qui n'est pas la même chose que zéro
    # seconde d'attente.
    avg_seconds_to_claim: float | None
