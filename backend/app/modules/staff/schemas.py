from pydantic import BaseModel, ConfigDict, Field

from app.modules.staff.models import StaffRole


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    restaurant_name: str = Field(min_length=1, max_length=120)
    manager_name: str = Field(min_length=1, max_length=80)
    email: str
    password: str = Field(min_length=8)


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
