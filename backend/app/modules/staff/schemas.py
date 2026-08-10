from pydantic import BaseModel, ConfigDict

from app.modules.staff.models import StaffRole


class LoginRequest(BaseModel):
    email: str
    password: str


class StaffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    restaurant_id: int
    name: str
    role: StaffRole
    email: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    staff: StaffOut
