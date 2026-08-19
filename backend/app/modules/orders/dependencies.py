from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.orders.models import Order, PaymentStatus

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


def get_paid_order_by_query_token(
    order_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
) -> Order:
    """
    Facture PDF ouverte tel quel dans un navigateur (lien direct ou QR scanné
    depuis un autre appareil, voir confirmations de paiement 2026-08-19) :
    impossible d'y joindre l'en-tête `X-Order-Token`, le jeton voyage donc en
    paramètre — même principe que `orderWsUrl` côté frontend. 404 (jamais
    409) tant que non payée : une facture n'a de sens qu'une fois réglée, et
    différencier la réponse confirmerait l'existence de la commande.
    """
    order = db.get(Order, order_id)
    if not order or order.public_token != token or order.payment_status != PaymentStatus.PAID:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return order
