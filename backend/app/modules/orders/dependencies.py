from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.orders.models import Order

_NOT_FOUND = {"code": "ORDER_NOT_FOUND", "message": "order not found"}


def get_order_by_token(
    order_id: int,
    x_order_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Order:
    """
    Routes client d'une commande : suivi, paiement, abonnement push.

    Le parcours client reste sans compte — mais chaque appel doit être lié à la
    commande concernée par le `public_token` reçu à sa création. Toujours 404
    (jamais 401 ni 403) quand le token manque ou ne correspond pas : une
    réponse différenciée confirmerait l'existence de la commande et
    permettrait de la retrouver par énumération, ce qui est exactement le
    constat 1 de la revue.
    """
    if not x_order_token:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)

    order = db.get(Order, order_id)
    if not order or order.public_token != x_order_token:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return order
