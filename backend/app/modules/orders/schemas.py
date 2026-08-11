from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.orders.models import OrderStatus, PaymentMethod, PaymentStatus


class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int = 1
    notes: str | None = None
    is_shared: bool = False


class OrderCreate(BaseModel):
    restaurant_id: int
    table_id: int
    items: list[OrderItemCreate]
    # Pré-commande mode Ramadan : optionnel, réglé côté client sur l'heure
    # d'iftar du resto quand il choisit "commander pour l'iftar".
    scheduled_for: datetime | None = None


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    menu_item_id: int
    menu_item_name: str
    unit_price: float
    quantity: int
    notes: str | None
    is_shared: bool


class PayCardRequest(BaseModel):
    tip_amount: float = Field(default=0, ge=0)


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    restaurant_id: int
    table_id: int
    status: OrderStatus
    created_at: datetime
    confirmed_at: datetime | None
    sent_to_kitchen_at: datetime | None
    ready_at: datetime | None
    served_at: datetime | None
    taken_by_staff_id: int | None
    taken_by_staff_name: str | None
    scheduled_for: datetime | None
    payment_method: PaymentMethod | None
    payment_status: PaymentStatus
    tip_amount: float
    total_amount: float
    items: list[OrderItemOut]
