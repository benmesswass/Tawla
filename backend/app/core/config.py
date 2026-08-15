from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_JWT_SECRET = "dev-only-secret-change-in-production"


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

    # Pairs TCP autorisés à parler au nom d'un client via `X-Forwarded-For`,
    # séparés par une virgule, ou `*` pour tout pair. Vide par défaut : en
    # local il n'y a pas de proxy, et croire cet en-tête sans proxy déclaré
    # reviendrait à laisser n'importe qui se donner une IP neuve à chaque
    # requête — donc à supprimer le limiteur de débit.
    #
    # À renseigner au déploiement (Phase 20) : derrière l'hébergeur, le seul
    # pair TCP est son proxy, et sans ce réglage tout le parc partage un unique
    # compteur de 20 requêtes par minute.
    forwarded_allow_ips: str = ""

    @model_validator(mode="after")
    def _refuse_dev_secret_in_production(self) -> "Settings":
        if self.env == "production" and self.jwt_secret == _DEV_JWT_SECRET:
            raise ValueError(
                "JWT_SECRET est encore la valeur de dev alors que ENV=production. "
                "Générer une vraie valeur (voir backend/.env.example) avant de démarrer."
            )
        return self

    @property
    def trusted_proxy_ips(self) -> set[str]:
        return {ip.strip() for ip in self.forwarded_allow_ips.split(",") if ip.strip()}

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]


settings = Settings()
