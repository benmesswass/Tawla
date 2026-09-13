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

    # Défaut **"production"**, et c'est délibérément l'inverse de l'intuition.
    #
    # Ce réglage n'étiquette pas un environnement : c'est lui qui arme le
    # garde-fou du bas de ce fichier. Tant qu'il valait "development" par
    # défaut, ce garde-fou ne s'armait que sur les déploiements qui pensaient à
    # poser `ENV` — c'est-à-dire jamais sur celui qui l'avait oublié, le seul
    # qu'il fallait protéger.
    #
    # Ce n'est pas théorique : découvert le 2026-09-11 sur `tawla-backend-fr`,
    # en ligne avec six variables au lieu de douze. Sans `ENV`, sans
    # `JWT_SECRET`, sans `ADMIN_CREATION_SECRET` — donc en train de signer les
    # jetons du personnel avec `_DEV_JWT_SECRET`, une constante lisible par
    # tous dans un dépôt public. Le garde-fou existait, il dormait.
    #
    # Avec ce défaut, une variable oubliée fait **échouer le démarrage** au
    # lieu de faire tourner un service en mode dev sans que personne ne le
    # voie. Le dev local et `docker compose` posent déjà `ENV=development`
    # dans `backend/.env` ; la suite de tests le pose dans `conftest.py`.
    env: str = "production"

    # Dimensionnement du pool de connexions (ROADMAP_PRODUCTION.md §P1.3).
    # Laissés au défaut de SQLAlchemy (5 + 10, attente 30 s) jusqu'au
    # 2026-09-10, ces réglages étaient devenus le plafond de capacité du
    # produit entier : mesuré, 15 connexions saturées faisaient tomber TOUS
    # les restaurants à la fois, et l'attente de 30 s à l'intérieur d'un
    # handler `async def` gelait la boucle d'événements au lieu de faire
    # échouer une seule requête.
    #
    # Configurables plutôt qu'en dur : le bon dimensionnement dépend du plan
    # Postgres et du nombre d'instances backend, qui changeront (§P3.1). La
    # règle à respecter en les changeant : `nb_instances × (pool_size +
    # max_overflow)` doit rester sous le plafond de connexions du plan
    # Postgres, sinon c'est la base qui refuse au lieu du pool.
    db_pool_size: int = 10
    db_max_overflow: int = 20
    # Volontairement COURT (5 s, contre 30 s par défaut) : une requête qui
    # n'obtient pas de connexion doit échouer franchement plutôt que de
    # pendre une demi-minute. Un 503 rapide est récupérable — un serveur qui
    # ne répond plus ne l'est pas.
    db_pool_timeout: int = 5
    # Recycle les connexions inactives avant que l'hébergeur ne les coupe
    # lui-même sans prévenir (comportement courant des Postgres managés).
    db_pool_recycle: int = 1800

    # État partagé entre instances (ROADMAP_PRODUCTION.md §P2.1). Vide par
    # défaut : le backend garde alors ses dicts en mémoire et se comporte
    # exactement comme avant — aucune dépendance, aucun service à payer, rien à
    # lancer pour `pytest`. La renseigner fait basculer le panier de table, le
    # roster, le mode de répartition, le limiteur de débit et la diffusion
    # temps réel sur Redis, ce qui est la condition pour faire tourner plus
    # d'une instance backend. Un pilote à un restaurant n'en a pas besoin.
    redis_url: str = ""

    # Stockage objet des photos (ROADMAP_PRODUCTION.md §P2.2) — plats,
    # bannière de couverture, logo. Les QUATRE doivent être renseignées pour
    # basculer ; sinon les photos restent en base, exactement comme avant, et
    # rien n'est à installer ni à payer. Cloudflare R2 en production :
    # l'endpoint ressemble à https://<account>.r2.cloudflarestorage.com, et
    # `photos_public_base_url` est le domaine public du bucket (ou le domaine
    # personnalisé branché dessus) — jamais l'endpoint S3, qui exige une
    # signature et n'est donc pas lisible par le navigateur d'un client.
    photos_s3_endpoint: str = ""
    photos_s3_bucket: str = ""
    photos_s3_access_key: str = ""
    photos_s3_secret_key: str = ""
    photos_public_base_url: str = ""

    # Marché servi par cette instance ("tn" | "fr") — un déploiement par
    # marché (MARCHE_FRANCE.md §4, option B retenue), jamais les deux dans le
    # même processus. Lu une fois au démarrage par app/core/markets.py.
    # Défaut "tn" : une instance existante qui ne pose jamais cette variable
    # ne change pas de comportement.
    market: str = "tn"

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

    # Analytics produit (PostHog) — événements de facturation d'abonnement
    # émis côté serveur (voir app/core/analytics.py). Dégradation gracieuse :
    # sans posthog_api_key, aucun envoi n'est tenté. Host EU par défaut : le
    # projet Tawla est hébergé sur eu.posthog.com, pas le défaut US du SDK.
    posthog_api_key: str = ""
    posthog_host: str = "https://eu.i.posthog.com"

    # Lecture des mêmes données depuis le dashboard admin plateforme (voir
    # app/core/posthog_query.py) — clé personnelle distincte de
    # `posthog_api_key` ci-dessus (celle-ci est en écriture seule, prévue
    # pour être publique côté client ; celle-ci est en lecture seule, scope
    # insight:read + query:read, ne doit jamais partir au frontend).
    # Dégradation gracieuse : sans elle, la section analytics du dashboard
    # admin reste vide au lieu de planter. `posthog_app_host` est l'API web
    # (eu.posthog.com), distinct de `posthog_host` qui est l'endpoint
    # d'ingestion (eu.i.posthog.com) — les deux ne sont pas interchangeables.
    posthog_personal_api_key: str = ""
    posthog_app_host: str = "https://eu.posthog.com"
    posthog_project_id: str = "263083"

    # Étiquette `env` posée sur chaque événement émis par ce backend (voir
    # analytics.py) — délibérément SÉPARÉE de `env` ci-dessus, qui contrôle les
    # garde-fous de sécurité. Les deux backends sont "production" au sens
    # sécurité, mais pas encore le vrai site public (juste les URLs Vercel
    # actuelles) — donc "staging" ici tant que le vrai domaine n'est pas
    # branché. Défaut "development" : une instance qui ne pose jamais cette
    # variable ne se fait jamais passer pour du trafic réel.
    #
    # Ce commentaire affirmait jusqu'au 2026-09-11 que `ENV` valait « déjà
    # production sur tawla-backend-fr/tawla-backend.onrender.com ». C'était
    # vrai pour le tunisien, faux pour le français, et personne n'avait de
    # raison d'aller vérifier : un commentaire avait tenu lieu de preuve. D'où
    # le défaut inversé plus haut — désormais c'est le démarrage qui vérifie.
    posthog_env: str = "development"

    @property
    def stockage_objet_configure(self) -> bool:
        """
        Tout ou rien : une configuration à moitié posée enverrait les photos
        vers un bucket inaccessible et les rendrait invisibles chez le client,
        sans erreur au démarrage. Le garde-fou ci-dessous refuse ce cas.
        """
        return all(
            (
                self.photos_s3_endpoint,
                self.photos_s3_bucket,
                self.photos_s3_access_key,
                self.photos_s3_secret_key,
                self.photos_public_base_url,
            )
        )

    @model_validator(mode="after")
    def _refuse_un_stockage_photos_incomplet(self) -> "Settings":
        """
        Même esprit que le garde-fou du JWT : une variable oubliée doit
        empêcher le démarrage, pas produire une carte sans photos que personne
        ne comprend. Vérifié au boot parce que c'est le seul moment où
        quelqu'un regarde encore les logs de déploiement.
        """
        posees = [
            nom
            for nom, valeur in (
                ("PHOTOS_S3_ENDPOINT", self.photos_s3_endpoint),
                ("PHOTOS_S3_BUCKET", self.photos_s3_bucket),
                ("PHOTOS_S3_ACCESS_KEY", self.photos_s3_access_key),
                ("PHOTOS_S3_SECRET_KEY", self.photos_s3_secret_key),
                ("PHOTOS_PUBLIC_BASE_URL", self.photos_public_base_url),
            )
            if valeur
        ]
        if posees and len(posees) != 5:
            raise ValueError(
                "Configuration du stockage photos incomplète : "
                f"{', '.join(posees)} posée(s), il en faut les cinq. "
                "Les laisser toutes vides garde les photos en base (comportement par défaut)."
            )
        return self

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
