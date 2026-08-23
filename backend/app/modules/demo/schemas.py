from datetime import datetime

from pydantic import BaseModel

from app.modules.staff.schemas import StaffOut


class DemoSessionOut(BaseModel):
    """
    Tout ce qu'il faut au navigateur pour jouer la visite guidée complète :
    la session manager (mêmes champs qu'une connexion normale), le QR d'une
    table pour le parcours client, et l'échéance à afficher.
    """

    access_token: str
    staff: StaffOut
    restaurant_id: int
    restaurant_name: str
    # Le parcours client de la visite guidée vit sur /menu/<qr_token> : sans
    # ce jeton, la page d'accueil n'a aucun moyen de l'atteindre.
    qr_token: str
    expires_at: datetime
