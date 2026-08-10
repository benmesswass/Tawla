from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Config centralisée. Toute valeur sensible ou dépendante de
    l'environnement passe par ici, jamais en dur dans le code.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://postgres:postgres@localhost:5432/resto_qr"
    env: str = "development"

    # MVP mono-restaurant : on garde restaurant_id partout dans le modèle
    # de données pour ne pas avoir à migrer le jour où on ajoute un 2e resto,
    # mais on ne construit pas encore d'auth multi-tenant / billing (YAGNI).


settings = Settings()
