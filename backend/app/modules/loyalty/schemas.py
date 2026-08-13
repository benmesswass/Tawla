from datetime import date

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.modules.loyalty.models import LOYALTY_REWARD_THRESHOLD


class LoyaltyLookup(BaseModel):
    restaurant_id: int
    phone_number: str
    birth_date: date | None = None


class LoyaltyMemberPublicOut(BaseModel):
    """
    Vue **client** d'une fiche fidélité. `birth_date` n'en fait pas partie :
    l'endpoint de consultation est public (le client saisit son numéro au
    moment de commander), donc tout champ exposé ici est lisible par quiconque
    essaie un numéro de téléphone. Le bandeau anniversaire reste calculé côté
    serveur et renvoyé sous forme de booléen — la date elle-même ne sort pas.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    restaurant_id: int
    phone_number: str
    order_count: int
    reward_available: bool

    # Exclu du schéma de sortie (préfixe `_` impossible avec Pydantic : on
    # utilise l'exclusion explicite) mais nécessaire aux champs calculés.
    birth_date_internal: date | None = Field(default=None, exclude=True, alias="birth_date")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def orders_until_reward(self) -> int:
        if self.reward_available:
            return 0
        remaining = self.order_count % LOYALTY_REWARD_THRESHOLD
        return LOYALTY_REWARD_THRESHOLD - remaining

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_birthday_today(self) -> bool:
        if not self.birth_date_internal:
            return False
        today = date.today()
        return (
            self.birth_date_internal.month == today.month
            and self.birth_date_internal.day == today.day
        )


class LoyaltyMemberOut(LoyaltyMemberPublicOut):
    """Vue **staff** : ajoute la date de naissance, que le serveur peut avoir
    besoin de vérifier. Servie uniquement aux routes protégées par JWT."""

    birth_date: date | None
