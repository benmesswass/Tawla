from datetime import date

from pydantic import BaseModel, ConfigDict, computed_field

from app.modules.loyalty.models import LOYALTY_REWARD_THRESHOLD


class LoyaltyLookup(BaseModel):
    restaurant_id: int
    phone_number: str
    birth_date: date | None = None


class LoyaltyMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    restaurant_id: int
    phone_number: str
    birth_date: date | None
    order_count: int
    reward_available: bool

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
        if not self.birth_date:
            return False
        today = date.today()
        return self.birth_date.month == today.month and self.birth_date.day == today.day
