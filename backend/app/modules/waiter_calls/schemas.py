from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WaiterCallCreate(BaseModel):
    restaurant_id: int
    table_id: int


class WaiterCallOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    restaurant_id: int
    table_id: int
    created_at: datetime
    resolved_at: datetime | None
    resolved_by_staff_id: int | None
