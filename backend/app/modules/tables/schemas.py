from pydantic import BaseModel, ConfigDict


class TableCreate(BaseModel):
    restaurant_id: int
    label: str
    zone: str | None = None


class TableOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    restaurant_id: int
    label: str
    qr_token: str
    assigned_staff_id: int | None
    zone: str | None


class TableAssignStaff(BaseModel):
    staff_id: int


class TableUpdate(BaseModel):
    label: str
    zone: str | None = None
