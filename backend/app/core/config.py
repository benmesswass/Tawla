from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Config centralisée. Toute valeur sensible ou dépendante de
    l'environnement passe par ici, jamais en dur dans le code.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://postgres:postgres@localhost:5432/resto_qr"
    env: str = "development"

    # Défaut de dev uniquement — DOIT être surchargé en prod (variable
    # d'environnement JWT_SECRET). Signe les tokens d'auth staff.
    jwt_secret: str = "dev-only-secret-change-in-production"

    # Notifications push navigateur (Web Push standard, gratuit — pas de
    # service tiers payant comme un envoi SMS). Vides par défaut : la
    # fonctionnalité se désactive silencieusement (best-effort, ne bloque
    # jamais le flux de commande) tant qu'une paire de clés VAPID n'est pas
    # générée et injectée en variables d'environnement.
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_contact_email: str = "contact@tawla.tn"


settings = Settings()
