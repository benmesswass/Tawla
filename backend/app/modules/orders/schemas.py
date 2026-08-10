from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.orders.models import OrderStatus


class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int = 1
    notes: str | None = None


class OrderCreate(BaseModel):
    restaurant_id: int
    table_id: int
    items: list[OrderItemCreate]


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    menu_item_id: int
    menu_item_name: str
    unit_price: float
    quantity: int
    notes: str | None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    restaurant_id: int
    table_id: int
    status: OrderStatus
    created_at: datetime
    confirmed_at: datetime | None
    sent_to_kitchen_at: datetime | None
    taken_by_staff_id: int | None
    taken_by_staff_name: str | None
    items: list[OrderItemOut]
