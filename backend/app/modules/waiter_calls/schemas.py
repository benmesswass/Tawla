from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WaiterCallCreate(BaseModel):
    """
    Le client n'envoie que le token du QR de sa table. La table et le
    restaurant en sont déduits — même règle que `OrderCreate` : aucun
    identifiant numérique n'est accepté du client, donc rien n'est devinable.

    Avant, cette route prenait `restaurant_id` et `table_id` bruts : deux
    boucles suffisaient à faire sonner en continu les écrans serveur de tous
    les établissements, depuis n'importe où.
    """

    qr_token: str


class WaiterCallOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    restaurant_id: int
    table_id: int
    table_label: str
    created_at: datetime
    resolved_at: datetime | None
    resolved_by_staff_id: int | None
