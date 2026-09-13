"""
Où vivent les photos du produit (ROADMAP_PRODUCTION.md §P2.2, F8).

**Le problème.** Les photos — plats, bannière de couverture, logo — sont des
colonnes `LargeBinary` dans Postgres. Le choix d'origine était bon et assumé
(`menu/models.py`) : chez Render comme chez Railway le système de fichiers est
éphémère, et un disque local aurait vidé toutes les cartes au premier
redéploiement, un soir, en plein service.

Il ne tient plus à l'échelle visée, pour une raison qui n'est **pas** le coût
de stockage — `AUDIT_COUTS_PRODUCTION.md` §4.4 a montré que c'était quelques
dinars par mois, et il avait raison. La vraie raison est celle que P1 vient de
passer un palier entier à protéger : **chaque photo servie traverse le
processus applicatif et immobilise une connexion du pool** le temps de
transférer 150 à 300 Ko. C'est la ressource rare, pas l'argent. Arbitrage de
Wassim du 2026-09-11.

**Deux modes, comme partout ailleurs dans ce projet.** Sans configuration, les
photos restent en base et **rien ne change** : aucune dépendance à installer,
aucun compte à ouvrir, `pytest -q` sans prérequis, et un pilote à un
restaurant n'a aucune raison de payer un stockage objet. Dès que les quatre
variables `PHOTOS_S3_*` sont renseignées, les nouvelles photos partent sur le
stockage objet (**Cloudflare R2**, chiffré et sourcé par l'audit des coûts :
palier gratuit de 10 Go, et surtout **pas de frais de sortie**, ce qui est
l'avantage structurel sur S3 quand on ressert les mêmes images en boucle).

**Ce qui change pour le client : rien à écrire côté frontend.** `image_url`
devient une URL absolue vers le CDN au lieu d'un chemin relatif, et
`mediaUrl()` (`frontend/lib/api.ts`) sait déjà distinguer les deux. La photo
n'est alors plus servie par le backend **du tout** — pas même une redirection.

**Clés adressées par contenu, préfixées par l'objet propriétaire.** L'empreinte
rend `Cache-Control: immutable` aussi sûr qu'aujourd'hui ; le préfixe
(`menu-items/42/…`) évite que deux plats qui portent la même photo partagent
un objet, ce qui ferait disparaître la photo de l'un quand l'autre la retire.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from hashlib import sha256

from app.core.config import settings
from app.core.logging import get_logger, log_event

logger = get_logger("photos")

EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}

# Un an, immuable : l'URL porte l'empreinte du contenu, donc une photo
# remplacée change d'adresse. Même en-tête que celui déjà servi par le backend
# aujourd'hui — il déménage simplement sur l'objet.
CACHE_PHOTOS = "public, max-age=31536000, immutable"


@dataclass(frozen=True)
class PhotoDeposee:
    """
    Ce qu'il reste à écrire en base après un dépôt.

    `octets` vaut `None` quand la photo vit hors base : c'est ce qui vide la
    colonne `LargeBinary` au passage au stockage objet, sans code de migration
    dans les routes.
    """

    url: str
    octets: bytes | None
    type_mime: str | None


class StockagePhotos(ABC):
    @abstractmethod
    def deposer(self, prefixe: str, contenu: bytes, type_mime: str, url_backend: str) -> PhotoDeposee:
        """
        `prefixe` identifie l'objet propriétaire (`menu-items/42`).
        `url_backend` est l'URL que le backend servirait lui-même — utilisée
        telle quelle en mode base, ignorée en mode objet.
        """

    @abstractmethod
    def retirer(self, url: str | None) -> None:
        """Supprime l'objet derrière cette URL. Sans effet en mode base, où
        c'est la colonne qui porte la photo."""

    @property
    @abstractmethod
    def hors_base(self) -> bool:
        """`True` quand les photos ne transitent plus par le backend."""


class StockageEnBase(StockagePhotos):
    """Le comportement d'avant P2.2, à l'identique. C'est le défaut."""

    def deposer(self, prefixe: str, contenu: bytes, type_mime: str, url_backend: str) -> PhotoDeposee:
        return PhotoDeposee(url=url_backend, octets=contenu, type_mime=type_mime)

    def retirer(self, url: str | None) -> None:
        return None

    @property
    def hors_base(self) -> bool:
        return False


class StockageObjet(StockagePhotos):
    """
    Stockage compatible S3 — Cloudflare R2 en production.

    Le client boto3 n'est importé qu'ici : sans configuration, le paquet n'est
    jamais chargé, et le mode par défaut ne dépend de rien.
    """

    def __init__(self) -> None:
        import boto3

        self._bucket = settings.photos_s3_bucket
        self._base_publique = settings.photos_public_base_url.rstrip("/")
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.photos_s3_endpoint,
            aws_access_key_id=settings.photos_s3_access_key,
            aws_secret_access_key=settings.photos_s3_secret_key,
            # R2 n'a pas de régions au sens AWS, mais la signature en exige
            # une ; « auto » est la valeur que Cloudflare documente.
            region_name="auto",
        )

    def deposer(self, prefixe: str, contenu: bytes, type_mime: str, url_backend: str) -> PhotoDeposee:
        cle = f"{prefixe}/{sha256(contenu).hexdigest()[:32]}.{EXTENSIONS.get(type_mime, 'jpg')}"
        self._client.put_object(
            Bucket=self._bucket,
            Key=cle,
            Body=contenu,
            ContentType=type_mime,
            CacheControl=CACHE_PHOTOS,
        )
        log_event(logger, "photo.deposee", cle=cle, octets=len(contenu))
        # `octets=None` : la colonne `LargeBinary` est vidée par le même
        # chemin de code, sans traitement spécial dans les routes.
        return PhotoDeposee(url=f"{self._base_publique}/{cle}", octets=None, type_mime=None)

    def retirer(self, url: str | None) -> None:
        cle = self.cle_de(url)
        if not cle:
            return
        try:
            self._client.delete_object(Bucket=self._bucket, Key=cle)
            log_event(logger, "photo.retiree", cle=cle)
        except Exception:
            # Best-effort : un objet qui survit à la suppression de sa ligne
            # coûte quelques centimes, une exception ici priverait le manager
            # de retirer une photo ratée de sa carte.
            logger.exception("photo.retrait_echoue")

    def cle_de(self, url: str | None) -> str | None:
        """La clé d'objet derrière une URL publique, ou `None` si cette URL
        n'en vient pas (photo encore en base, URL d'un autre domaine)."""
        if not url or not url.startswith(f"{self._base_publique}/"):
            return None
        return url[len(self._base_publique) + 1:]

    @property
    def hors_base(self) -> bool:
        return True


def _construire() -> StockagePhotos:
    if not settings.stockage_objet_configure:
        return StockageEnBase()
    stockage = StockageObjet()
    log_event(logger, "photos.stockage_objet_actif", bucket=settings.photos_s3_bucket)
    return stockage


stockage_photos: StockagePhotos = _construire()
