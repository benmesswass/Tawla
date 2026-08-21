import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.dates import as_utc


class SubscriptionTier(str, enum.Enum):
    """
    Modèle économique décidé le 2026-08-12 : abonnement à 3 paliers, aucune
    commission sur les commandes (voir ROADMAP.md Phase 11). Le gating réel
    est en place depuis l'offre à trois paliers (2026-08-18, voir
    app/core/subscription.py) et le paiement en ligne du passage à un palier
    supérieur depuis app/core/konnect.py / subscription_payments.py.
    """
    ESSENTIEL = "essentiel"
    PRO = "pro"
    BUSINESS = "business"


class Restaurant(Base):
    """
    Un resto/café client. MVP = un seul enregistrement en pratique,
    mais tout le reste du modèle référence restaurant_id dès le départ
    pour permettre d'onboarder un 2e client sans migration lourde.
    """
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Mode Ramadan — pas de calcul astronomique/API externe (zéro service
    # payant obligatoire, zéro dépendance réseau) : le manager saisit
    # lui-même l'heure du jour, comme il le ferait sur un tableau au mur.
    ramadan_mode_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    iftar_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Mode café simplifié : un établissement qui ne sert que des boissons
    # n'a pas besoin de la structure entrées/plats/desserts — le menu
    # client s'affiche alors en liste unique, sans en-têtes de catégorie.
    cafe_mode_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Retour sonore optionnel à l'arrivée d'une commande en cuisine — désactivé
    # par défaut (une cuisine bruyante peut ne pas vouloir d'un bip de plus),
    # activable par le manager depuis le dashboard.
    kitchen_sound_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Palier d'abonnement — conditionne l'accès aux fonctionnalités Pro/Business,
    # voir app/core/subscription.py. Essentiel par défaut, mais un palier ne
    # dit rien de si le compte est UTILISABLE (voir `is_active`/`is_usable`
    # ci-dessous) : Essentiel reste un palier payant (50 DT), jamais gratuit.
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier), default=SubscriptionTier.ESSENTIEL
    )

    # Fin de la période payée en ligne (self-service, voir subscription_payments.py).
    # Null = pas de suivi d'expiration : soit jamais payé en ligne, soit palier
    # fixé à la main par setup_restaurant.py (relation commerciale directe avec
    # Wassim) — ce cas-là ne doit JAMAIS retomber tout seul à Essentiel. Ce n'est
    # que lorsque cette date est dépassée que effective_tier() (subscription.py)
    # ramène le palier effectif à Essentiel, sans jamais muter cette colonne.
    subscription_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Paiement Konnect d'abonnement en cours — même mécanique que
    # orders.payment_ref (mode simulé tant qu'aucune clé Konnect réelle
    # n'existe pour Tawla elle-même) : posé à l'initiation du paiement, remis à
    # null au règlement (settle_subscription_payment). Une référence encore
    # présente = paiement en attente, jamais deux fois réglée pour la même
    # référence (garde d'idempotence).
    subscription_payment_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Palier visé par le paiement en cours (subscription_payment_ref non nul) —
    # appliqué à subscription_tier seulement au règlement effectif, jamais à
    # l'initiation : tant que Konnect n'a pas confirmé, l'accès ne change pas.
    subscription_pending_tier: Mapped[SubscriptionTier | None] = mapped_column(
        Enum(SubscriptionTier), nullable=True
    )

    # A-t-il DÉJÀ payé au moins une fois (ou été onboardé à la main) — PAS "a
    # accès en ce moment" (voir `is_usable` ci-dessous, qui vérifie EN PLUS
    # `subscription_period_end`). Un établissement inscrit en self-service via
    # /auth/register démarre à `False` — jamais d'accès gratuit, y compris à
    # Essentiel (voir CLAUDE.md). Passe à `True` — définitivement, jamais remis
    # à `False` ensuite — au règlement du premier paiement, quel que soit le
    # palier payé (settle_subscription_payment). Essentiel EST un abonnement de
    # 30 jours comme Pro/Business (2026-08-20) : un compte qui ne renouvelle
    # pas reste `is_active=True` mais redevient inutilisable via
    # `subscription_period_end` expiré, exactement comme un palier Pro/Business
    # qui retombe à Essentiel dans `effective_tier()` — la seule différence
    # est qu'il n'y a plus de palier gratuit en dessous où retomber. Un
    # restaurant créé par setup_restaurant.py (pilote facturé à la main)
    # démarre à `True` — c'est le défaut de la colonne, seul /auth/register le
    # force explicitement à `False`.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Dérogation posée à la main par Wassim (écran admin, jamais un
    # restaurateur) : accès gratuit sans paiement, indépendamment de
    # `is_active` — voir `is_usable` ci-dessous. Distinct de `is_active` pour
    # ne jamais perdre la trace de "a réellement payé" sous la dérogation.
    promo_gratuit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Offre de lancement (2026-08-21, décidée par Wassim) : le premier mois
    # Essentiel gratuit, accordé AUTOMATIQUEMENT (pas une action admin, voir
    # promo_gratuit ci-dessus) aux 20 premiers établissements inscrits en
    # self-service — voir staff/router.py::register. Marqueur PERMANENT,
    # jamais remis à `False` (même après un vrai paiement) : c'est le
    # décompte des 20 places qui en dépend (`COUNT(*) WHERE
    # launch_promo_granted`), un historique, pas un état courant.
    launch_promo_granted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # A-t-il payé pour de vrai au moins une fois (Konnect réel OU mode démo,
    # peu importe — voir settle_subscription_payment et
    # tenants/router.py::start_subscription_checkout) — DISTINCT d'`is_active`
    # ci-dessus : un restaurant peut être `is_active=True` uniquement parce
    # que l'offre de lancement l'a activé, sans qu'aucun paiement n'ait
    # jamais eu lieu. Sert à savoir quand arrêter d'afficher le rappel de
    # paiement (frontend) — jamais à du gating (voir is_usable, qui n'en tient
    # pas compte). Défaut `True` : un restaurant onboardé par
    # setup_restaurant.py (pilote facturé à la main) ou un compte de démo/test
    # est une vraie relation payante, juste pas via Konnect — seul
    # /auth/register le force explicitement à `False` à l'inscription.
    has_paid_for_subscription: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Konnect propre au restaurant, pour le paiement carte du CLIENT — modèle
    # direct (connexion Konnect au paiement carte, 2026-08-19) : la promesse
    # commerciale de Tawla est "vos clients vous règlent directement", donc le
    # wallet qui reçoit ce paiement ne peut jamais être celui de Tawla (utilisé
    # uniquement pour l'abonnement, voir subscription_payment_ref ci-dessus).
    # Clé chiffrée au repos (app/core/crypto.py) : contrairement au wallet de
    # Tawla, c'est un secret appartenant à un tiers. Null tant que le
    # restaurant n'a rien connecté = paiement carte en mode démo.
    konnect_api_key_encrypted: Mapped[str | None] = mapped_column(String(500), nullable=True)
    konnect_wallet_id: Mapped[str | None] = mapped_column(String(120), nullable=True)

    @property
    def konnect_configured(self) -> bool:
        return bool(self.konnect_api_key_encrypted and self.konnect_wallet_id)

    @property
    def is_usable(self) -> bool:
        """
        Portail unique pour "ce restaurant a-t-il le droit d'utiliser Tawla
        MAINTENANT" — jamais lire `is_active` seul pour du gating.

        Essentiel est un abonnement de 30 jours comme Pro/Business
        (2026-08-20, voir CLAUDE.md) : `is_active` reste `True` à vie une fois
        payé une première fois, mais un compte qui ne renouvelle pas doit
        quand même redevenir bloqué — d'où la même vérification d'expiration
        que `effective_tier()` (core/subscription.py), dupliquée ici plutôt
        qu'importée pour éviter un import circulaire (staff.dependencies et
        core.subscription importent déjà `Restaurant`/`is_usable` DEPUIS ce
        module). `subscription_period_end = None` = palier fixé à la main par
        setup_restaurant.py (pilote, relation commerciale directe), jamais
        d'expiration — même convention que `effective_tier()`.
        """
        if self.promo_gratuit:
            return True
        if not self.is_active:
            return False
        if self.subscription_period_end is None:
            return True
        return as_utc(self.subscription_period_end) > datetime.now(timezone.utc)

    def konnect_credentials(self) -> tuple[str, str] | None:
        """`(api_key, wallet_id)` déchiffrés, ou `None` tant que ce restaurant
        n'a rien connecté (ou si la clé de chiffrement a changé depuis —
        `decrypt_field` renvoie `None` plutôt que de lever, voir crypto.py)."""
        if not self.konnect_api_key_encrypted or not self.konnect_wallet_id:
            return None
        from app.core.crypto import decrypt_field

        api_key = decrypt_field(self.konnect_api_key_encrypted)
        if not api_key:
            return None
        return api_key, self.konnect_wallet_id
