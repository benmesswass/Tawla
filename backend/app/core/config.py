from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_JWT_SECRET = "dev-only-secret-change-in-production"
_DEV_ADMIN_CREATION_SECRET = "dev-only-admin-secret-change-in-production"


class Settings(BaseSettings):
    """
    Config centralisée. Toute valeur sensible ou dépendante de
    l'environnement passe par ici, jamais en dur dans le code.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://postgres:postgres@localhost:5432/resto_qr"
    env: str = "development"

    # Défaut de dev uniquement — DOIT être surchargé en prod (variable
    # d'environnement JWT_SECRET). Signe les tokens d'auth staff. Le
    # garde-fou ci-dessous empêche de démarrer en prod avec cette valeur
    # par erreur.
    jwt_secret: str = _DEV_JWT_SECRET

    # Verrou de création d'un compte `PlatformAdmin` (2026-08-21ter,
    # remplace `scripts/create_platform_admin.py`) — aucune route ne crée
    # d'admin sans ce secret (voir platform_admin/router.py::create_admin),
    # exactement comme JWT_SECRET : DOIT être surchargé en prod, connu de
    # Wassim seul (gestionnaire de mots de passe), jamais commité. Le
    # garde-fou ci-dessous empêche de démarrer en prod avec la valeur de dev.
    admin_creation_secret: str = _DEV_ADMIN_CREATION_SECRET

    # Origine(s) autorisées en CORS, séparées par une virgule (ex:
    # "https://tawla.tn,https://www.tawla.tn"). Défaut = port du frontend
    # en dev local.
    frontend_origin: str = "http://localhost:3000"

    # Notifications push navigateur (Web Push standard, gratuit — pas de
    # service tiers payant comme un envoi SMS). Vides par défaut : la
    # fonctionnalité se désactive silencieusement (best-effort, ne bloque
    # jamais le flux de commande) tant qu'une paire de clés VAPID n'est pas
    # générée et injectée en variables d'environnement.
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_contact_email: str = "contact@tawla.tn"

    # URLs canoniques (une seule valeur chacune, contrairement à
    # `frontend_origin` qui peut lister plusieurs origines CORS) — utilisées
    # pour construire les URLs de retour/webhook du paiement d'abonnement
    # (app/core/konnect.py) : là où rediriger le manager après paiement, et
    # l'adresse à laquelle Konnect doit rappeler ce backend.
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    @model_validator(mode="after")
    def _refuse_dev_secret_in_production(self) -> "Settings":
        if self.env == "production" and self.jwt_secret == _DEV_JWT_SECRET:
            raise ValueError(
                "JWT_SECRET est encore la valeur de dev alors que ENV=production. "
                "Générer une vraie valeur (voir backend/.env.example) avant de démarrer."
            )
        if self.env == "production" and self.admin_creation_secret == _DEV_ADMIN_CREATION_SECRET:
            raise ValueError(
                "ADMIN_CREATION_SECRET est encore la valeur de dev alors que ENV=production. "
                "Générer une vraie valeur (voir backend/.env.example) avant de démarrer."
            )
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]


settings = Settings()
