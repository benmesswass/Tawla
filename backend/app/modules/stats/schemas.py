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


class TopMenuItem(BaseModel):
    menu_item_name: str
    quantity: int


class HourlyCount(BaseModel):
    hour: int
    count: int


class DashboardStats(BaseModel):
    date: date_type
    active_orders_count: int
    timing: TimingStats
    staff_performance: list[StaffPerformance]
    top_items: list[TopMenuItem]
    orders_by_hour: list[HourlyCount]


class KitchenTodayCount(BaseModel):
    date: date_type
    count: int


class PeriodProof(BaseModel):
    """
    Les trois seuls chiffres qui valent quelque chose devant un restaurateur ou
    un jury (Phase 13.3) : combien de commandes ont été perdues, combien de
    temps s'écoule entre la commande du client et son arrivée en cuisine, et
    quel est le panier moyen.

    Volontairement pas un quatrième indicateur. Le reste est du confort.
    """

    start: date_type
    end: date_type  # inclus

    orders_count: int

    # « Perdue » = annulée, ou restée en attente de confirmation au-delà du
    # seuil défini dans orders/service.py::ABANDONED_PENDING_AFTER. Le détail
    # est renvoyé séparément parce que les deux causes n'appellent pas la même
    # action : une annulation est une décision, un abandon est un oubli.
    lost_orders_count: int
    cancelled_count: int
    abandoned_count: int

    # Du panier validé par le client à l'arrivée sur l'écran cuisine. C'est le
    # délai que le produit prétend réduire — donc celui qu'il faut mesurer.
    avg_order_to_kitchen_seconds: float | None

    # Sur les commandes non annulées : une commande annulée n'a jamais été un
    # panier réel et tirerait la moyenne vers le bas sans rien dire du service.
    avg_basket_amount: float | None


class ProofStats(BaseModel):
    """
    La période demandée et la période de même longueur qui la précède
    immédiatement : sans « avant », les trois chiffres ne prouvent rien.
    """

    current: PeriodProof
    previous: PeriodProof
