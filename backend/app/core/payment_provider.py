"""
Port de paiement carte (France, MARCHE_FRANCE.md §4, Phase F3 étape 4).

Abstrait le fournisseur derrière une interface commune pour qu'`orders/
service.py` ne connaisse plus Konnect directement — même raison que
`current_market` pour la devise ou le fuseau : protéger contre la
divergence quand un deuxième fournisseur (`StripeProvider`, Phase F6,
Connect — le restaurant reste le marchand) apparaîtra.

`KonnectProvider` est un pur adaptateur : toute la logique reste dans
`core/konnect.py`, inchangée, pour ne rien risquer sur le paiement carte
tunisien qui en dépend réellement aujourd'hui. `NullProvider` est **le**
mode du marché français tant que `StripeProvider` n'existe pas
(`current_market.payment_provider == "none"`) — pas un bouche-trou.

Volontairement hors de ce port : la vérification de signature du webhook
entrant (`orders/router.py::order_card_payment_webhook`). C'est un HMAC
global (dérivé de `JWT_SECRET`, jamais des identifiants d'un restaurant —
voir `konnect.py::_webhook_key`), pas un état par fournisseur/restaurant
comme le reste de cette interface ; le forcer ici aurait été une
abstraction pour une seule branche vivante. Seul `orders/service.py` est
visé par le critère de sortie de cette étape, pas `router.py`. Pour la
même raison, `init_payment()` ne prend pas d'URL de webhook en paramètre :
Konnect ne signe pas ses webhooks, donc l'URL de retour doit être
pré-signée (`sign_konnect_order_webhook`) — un détail Konnect que
l'appelant n'a plus à connaître, construit ici à partir du seul `order_id`.
"""
from dataclasses import dataclass
from typing import Protocol

from app.core import konnect
from app.core.config import settings
from app.core.markets import Market, current_market


class PaymentProviderError(Exception):
    """Erreur de fournisseur générique — `orders/service.py` n'attrape plus
    `KonnectError` directement (voir KonnectProvider ci-dessous)."""


@dataclass(frozen=True)
class PaymentInit:
    pay_url: str
    payment_ref: str


@dataclass(frozen=True)
class PaymentState:
    status: str
    reached_amount: int  # dans la plus petite unité du fournisseur — voir to_smallest_unit


class PaymentProvider(Protocol):
    def is_available(self) -> bool:
        """Faux si ce fournisseur ne peut pas être utilisé pour INITIER un
        nouveau paiement maintenant (clés manquantes, mode démo) —
        l'appelant retombe alors sur le paiement simulé, exactement comme
        aujourd'hui. Ne pas s'en servir pour RÉGLER un paiement déjà
        initié : voir la note dans settle_card_payment (orders/service.py)."""
        ...

    def init_payment(
        self,
        *,
        amount: float,
        order_id: str,
        description: str,
        success_url: str,
        fail_url: str,
        lifespan_minutes: int,
    ) -> PaymentInit: ...

    def get_payment(self, payment_ref: str) -> PaymentState: ...

    def to_smallest_unit(self, amount: float) -> int:
        """Convertit un montant (devise principale du marché) vers la plus
        petite unité que CE fournisseur attend — millimes pour Konnect/TND,
        centimes pour un futur StripeProvider/EUR. Jamais un
        `tnd_to_millimes` en dur ailleurs dans le code appelant."""
        ...

    def supports_refund(self) -> bool: ...


class KonnectProvider:
    """Adaptateur autour de `core/konnect.py` — identifiants (`api_key`,
    `wallet_id`) du restaurant, voir `Restaurant.konnect_credentials()`."""

    def __init__(self, api_key: str, wallet_id: str):
        self._api_key = api_key
        self._wallet_id = wallet_id

    def is_available(self) -> bool:
        return konnect.is_konnect_enabled()

    def init_payment(
        self,
        *,
        amount: float,
        order_id: str,
        description: str,
        success_url: str,
        fail_url: str,
        lifespan_minutes: int,
    ) -> PaymentInit:
        webhook = (
            f"{settings.backend_url}/api/v1/orders/{order_id}/pay/card/webhook"
            f"?sig={konnect.sign_konnect_order_webhook(int(order_id))}"
        )
        try:
            pay_url, payment_ref = konnect.init_konnect_payment(
                api_key=self._api_key,
                receiver_wallet_id=self._wallet_id,
                amount_tnd=amount,
                order_id=order_id,
                description=description,
                webhook=webhook,
                success_url=success_url,
                fail_url=fail_url,
                lifespan_minutes=lifespan_minutes,
            )
        except konnect.KonnectError as err:
            raise PaymentProviderError(str(err)) from err
        return PaymentInit(pay_url=pay_url, payment_ref=payment_ref)

    def get_payment(self, payment_ref: str) -> PaymentState:
        try:
            payment = konnect.get_konnect_payment(payment_ref, api_key=self._api_key)
        except konnect.KonnectError as err:
            raise PaymentProviderError(str(err)) from err
        return PaymentState(status=payment.status, reached_amount=payment.reached_amount)

    def to_smallest_unit(self, amount: float) -> int:
        return konnect.tnd_to_millimes(amount)

    def supports_refund(self) -> bool:
        return False


class NullProvider:
    """Mode S1 (§3.1 de MARCHE_FRANCE.md) : aucun encaissement dans Tawla
    pour ce marché/restaurant. `is_available()` toujours faux — l'appelant
    retombe sur le paiement simulé, comme aujourd'hui sans identifiants."""

    def is_available(self) -> bool:
        return False

    def init_payment(self, **_kwargs) -> PaymentInit:
        raise PaymentProviderError("NullProvider ne sait pas initier de paiement — vérifier is_available() d'abord")

    def get_payment(self, payment_ref: str) -> PaymentState:
        raise PaymentProviderError("NullProvider ne sait pas récupérer de paiement")

    def to_smallest_unit(self, amount: float) -> int:
        raise PaymentProviderError("NullProvider n'a pas de devise")

    def supports_refund(self) -> bool:
        return False


def get_payment_provider(
    credentials: tuple[str, str] | None, market: Market = current_market
) -> PaymentProvider:
    """
    Résout le fournisseur de paiement carte pour un restaurant.

    `credentials` : `(api_key, wallet_id)` Konnect du restaurant, ou `None`
    tant qu'il n'a rien connecté (voir `Restaurant.konnect_credentials()`)
    — un `NullProvider` dans les deux cas suivants : pas d'identifiants, ou
    marché dont `payment_provider != "konnect"` (la France aujourd'hui,
    volontairement, tant que `StripeProvider` n'existe pas).
    """
    if market.payment_provider == "konnect" and credentials is not None:
        api_key, wallet_id = credentials
        return KonnectProvider(api_key, wallet_id)
    return NullProvider()
