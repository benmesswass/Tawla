from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.invoice import generate_invoice_pdf
from app.core.konnect import is_konnect_enabled, verify_konnect_order_webhook
from app.core.logging import get_logger, log_event
from app.core.rate_limit import ORDER_VOLUME_MAX_REQUESTS, rate_limit
from app.modules.orders import schemas, service
from app.modules.orders.dependencies import get_order_by_token, get_paid_order_by_query_token
from app.modules.orders.models import Order, OrderStatus
from app.modules.staff.dependencies import require_active_restaurant, require_role
from app.modules.staff.models import Staff, StaffRole
from app.modules.tenants.models import Restaurant

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])
logger = get_logger("orders")

_WAITER_OR_MANAGER = require_role(StaffRole.WAITER, StaffRole.MANAGER)
_KITCHEN_OR_MANAGER = require_role(StaffRole.KITCHEN, StaffRole.MANAGER)


@router.post(
    "",
    response_model=schemas.OrderCreatedOut,
    status_code=201,
    # Toute la salle commande depuis le même Wi-Fi, donc la même IP (S-2b).
    dependencies=[Depends(rate_limit(ORDER_VOLUME_MAX_REQUESTS))],
)
async def create_order(payload: schemas.OrderCreate, db: Session = Depends(get_db)):
    """
    Appelé par le client après validation du panier — sans compte, mais avec le
    `qr_token` de la table qu'il vient de scanner. La réponse contient le
    `public_token` de la commande : c'est la seule fois où il est renvoyé, le
    navigateur doit le garder pour suivre et payer sa commande.
    """
    return await service.create_order(db, payload)


@router.get("/by-restaurant/{restaurant_id}/active", response_model=list[schemas.OrderOutStaff])
async def list_active_orders(
    restaurant_id: int, db: Session = Depends(get_db), staff: Staff = Depends(require_active_restaurant)
):
    """
    Rechargement d'état pour les écrans serveur/cuisine au montage : le
    WebSocket seul ne rattrape jamais ce qui s'est passé avant la connexion.
    """
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    return await service.list_active_orders(db, restaurant_id)


@router.get("/{order_id}", response_model=schemas.OrderOut)
async def get_order(order: Order = Depends(get_order_by_token)):
    """
    Suivi de commande côté client, y compris après un rafraîchissement de page.
    Sans compte, mais lié : exige l'en-tête `X-Order-Token` reçu à la création.
    """
    return order


@router.get(
    "/by-restaurant/{restaurant_id}/pending-cash-payments", response_model=list[schemas.OrderOutStaff]
)
async def list_pending_cash_payments(
    restaurant_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)
):
    """Tables ayant demandé à payer en espèces, pas encore encaissées."""
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    return await service.list_pending_cash_payments(db, restaurant_id)


@router.post("/{order_id}/push-subscription", status_code=204)
async def save_push_subscription(
    payload: schemas.PushSubscriptionIn,
    order: Order = Depends(get_order_by_token),
    db: Session = Depends(get_db),
):
    """
    Opt-in du client pour être notifié quand SA commande passe « prête ».
    Lié au token : sans ça, n'importe qui pouvait remplacer l'abonnement push
    d'une commande et détourner sa notification.
    """
    service.save_push_subscription(db, order.id, payload)


@router.post("/{order_id}/pay/card", response_model=schemas.OrderOut)
async def pay_by_card(
    payload: schemas.PayCardRequest,
    order: Order = Depends(get_order_by_token),
    db: Session = Depends(get_db),
):
    """
    Paiement carte par le client. Lié au token : sans ça, n'importe qui
    pouvait marquer n'importe quelle commande « payée » sans régler un dinar
    (constat 2 de la revue). Réglé chez le restaurant s'il a connecté son
    propre Konnect (modèle direct, 2026-08-19), sinon mode démo — voir
    `service.start_card_payment`. `pay_url` non-null = rediriger le client.
    """
    order, pay_url = await service.start_card_payment(db, order.id, payload.tip_amount, payload.customer_email)
    return schemas.serialize_order(order, pay_url)


@router.get("/{order_id}/pay/card/webhook")
async def order_card_payment_webhook(
    order_id: int,
    sig: str,
    db: Session = Depends(get_db),
    _rate: None = Depends(rate_limit()),
):
    """
    Appelée en GET par Konnect (`?payment_ref=…` ajouté, non utilisé ici : le
    règlement relit toujours le paiement depuis l'API Konnect). `sig` signe
    `order_id` (voir sign_konnect_order_webhook) — sans elle, un id connu ne
    suffit pas à forger un règlement.

    En dev local, Konnect ne peut pas joindre localhost : le filet de
    sécurité est `POST /pay/card/check`, appelé par la page de retour.
    """
    if not is_konnect_enabled():
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "not found"})
    if not verify_konnect_order_webhook(order_id, sig):
        log_event(logger, "order.card_payment_webhook_bad_signature", order_id=order_id)
        raise HTTPException(status_code=401, detail={"code": "INVALID_SIGNATURE", "message": "invalid signature"})

    result = await service.settle_card_payment(db, order_id)
    return {"received": True, "result": result}


@router.post("/{order_id}/pay/card/check", response_model=schemas.OrderOut)
async def check_card_payment(order: Order = Depends(get_order_by_token), db: Session = Depends(get_db)):
    """
    Filet de sécurité appelé par la page de retour (`?konnect=success`) — en
    dev local le webhook ci-dessus ne peut jamais être atteint. Sans effet si
    rien n'est en attente (idempotent, voir settle_card_payment), donc sans
    risque à appeler même quand Konnect est désactivé.
    """
    await service.settle_card_payment(db, order.id)
    db.refresh(order)
    return schemas.serialize_order(order)


@router.post("/{order_id}/pay/cash", response_model=schemas.OrderOut)
async def request_cash_payment(
    payload: schemas.PayCashRequest = schemas.PayCashRequest(),
    order: Order = Depends(get_order_by_token),
    db: Session = Depends(get_db),
):
    """Le client demande à payer en espèces — prévient le serveur en temps réel."""
    return await service.request_cash_payment(db, order.id, payload.tip_amount, payload.customer_email)


@router.post("/{order_id}/pay/cash/confirm", response_model=schemas.OrderOutStaff)
async def confirm_cash_payment(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)):
    """Le serveur confirme avoir encaissé le cash à table."""
    return await service.confirm_cash_payment(db, order_id, staff)


@router.post("/{order_id}/pay/card-terminal", response_model=schemas.OrderOut)
async def request_card_terminal_payment(
    payload: schemas.PayCardTerminalRequest = schemas.PayCardTerminalRequest(),
    order: Order = Depends(get_order_by_token),
    db: Session = Depends(get_db),
):
    """
    Carte physique : le client demande, un serveur apporte le terminal —
    même mécanique que le paiement en espèces (carte physique / en ligne /
    espèces, 2026-08-19).
    """
    return await service.request_card_terminal_payment(db, order.id, payload.tip_amount, payload.customer_email)


@router.post("/{order_id}/pay/card-terminal/confirm", response_model=schemas.OrderOutStaff)
async def confirm_card_terminal_payment(
    order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)
):
    """Le serveur confirme avoir encaissé la carte physique à table."""
    return await service.confirm_card_terminal_payment(db, order_id, staff)


@router.get(
    "/by-restaurant/{restaurant_id}/pending-card-terminal-payments", response_model=list[schemas.OrderOutStaff]
)
async def list_pending_card_terminal_payments(
    restaurant_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)
):
    """Tables ayant demandé à payer par carte physique, pas encore encaissées."""
    if staff.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not your restaurant"})
    return await service.list_pending_card_terminal_payments(db, restaurant_id)


@router.get("/{order_id}/invoice")
async def get_order_invoice(order: Order = Depends(get_paid_order_by_query_token), db: Session = Depends(get_db)):
    """
    Facture PDF — ouverte directement dans un navigateur (lien ou QR affiché
    après paiement, éventuellement sur un autre appareil que celui qui a
    commandé), jamais depuis l'app elle-même : pas de X-Order-Token en
    en-tête possible, voir get_paid_order_by_query_token.
    """
    restaurant = db.get(Restaurant, order.restaurant_id)
    pdf_bytes = generate_invoice_pdf(order, restaurant)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="facture-commande-{order.id}.pdf"'},
    )


@router.post("/{order_id}/claim", response_model=schemas.OrderOutStaff)
async def claim_order(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)):
    """Un serveur prend en charge une commande en attente depuis le pool partagé."""
    return await service.claim_order(db, order_id, staff)


@router.post("/{order_id}/confirm", response_model=schemas.OrderOutStaff)
async def confirm_order(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)):
    """Le serveur confirme la commande APRÈS l'avoir vérifiée avec la table."""
    return await service.transition_status(db, order_id, OrderStatus.CONFIRMED, staff)


@router.post("/{order_id}/send-to-kitchen", response_model=schemas.OrderOutStaff)
async def send_to_kitchen(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)):
    """Validation finale du serveur -> part sur l'écran cuisine."""
    return await service.transition_status(db, order_id, OrderStatus.SENT_TO_KITCHEN, staff)


@router.post("/{order_id}/cancel", response_model=schemas.OrderOutStaff)
async def cancel_order(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)):
    return await service.transition_status(db, order_id, OrderStatus.CANCELLED, staff)


@router.post("/{order_id}/start-preparation", response_model=schemas.OrderOutStaff)
async def start_preparation(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_KITCHEN_OR_MANAGER)):
    """Bouton côté écran cuisine."""
    return await service.transition_status(db, order_id, OrderStatus.IN_PREPARATION, staff)


@router.post("/{order_id}/mark-ready", response_model=schemas.OrderOutStaff)
async def mark_ready(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_KITCHEN_OR_MANAGER)):
    return await service.transition_status(db, order_id, OrderStatus.READY, staff)


@router.post("/{order_id}/mark-served", response_model=schemas.OrderOutStaff)
async def mark_served(order_id: int, db: Session = Depends(get_db), staff: Staff = Depends(_WAITER_OR_MANAGER)):
    return await service.transition_status(db, order_id, OrderStatus.SERVED, staff)
