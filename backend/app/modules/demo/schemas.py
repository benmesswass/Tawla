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
    # Jetons pré-signés pour les deux autres rôles, avec la même mécanique
    # qu'un login normal (staff/security.py::create_access_token). Les comptes
    # serveur et cuisine d'une démo ont un mot de passe généré aléatoirement,
    # jamais révélé (voir demo/service.py::creer_demo) — sans ces jetons, il
    # n'existe aucun moyen de s'y connecter depuis un deuxième appareil, et
    # montrer l'écran serveur en direct pendant qu'un client commande sur son
    # téléphone n'avait aucun chemin possible.
    waiter_access_token: str
    kitchen_access_token: str
