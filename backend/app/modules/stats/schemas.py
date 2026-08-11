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
