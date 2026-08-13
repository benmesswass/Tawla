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
    is_active: bool


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    staff: StaffOut


class StaffCreate(BaseModel):
    """
    Création d'un compte d'équipe par le manager. Pas de `restaurant_id` :
    il est toujours pris sur le JWT du manager, jamais sur le payload — c'est
    exactement la faille d'isolation corrigée en son temps sur
    `tables/router.py::assign_staff`, on ne la réintroduit pas ici.
    """

    name: str = Field(min_length=1, max_length=80)
    email: str
    role: StaffRole
    # Facultatif : sans mot de passe fourni, un mot de passe temporaire est
    # généré et renvoyé une seule fois (le manager le transmet de la main à
    # la main — il n'y a aucun service d'envoi d'e-mail dans le projet).
    password: str | None = Field(default=None, min_length=8)


class StaffUpdate(BaseModel):
    """Mise à jour partielle : seuls les champs fournis sont modifiés."""

    name: str | None = Field(default=None, min_length=1, max_length=80)
    role: StaffRole | None = None
    is_active: bool | None = None


class StaffCreatedOut(BaseModel):
    """
    Réponse de création / réinitialisation : le mot de passe temporaire n'est
    lisible qu'ici, une seule fois. Il n'est stocké que haché, donc il ne
    réapparaît dans aucune autre réponse.
    """

    staff: StaffOut
    temporary_password: str | None = None
