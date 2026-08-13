from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core import model_registry  # noqa: F401 — enregistre tous les modèles
from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.modules.loyalty.router import router as loyalty_router
from app.modules.menu.router import router as menu_router
from app.modules.notifications.router import router as notifications_router
from app.modules.orders.router import router as orders_router
from app.modules.staff.router import management_router as staff_management_router
from app.modules.staff.router import router as staff_router
from app.modules.stats.router import router as stats_router
from app.modules.tables.router import router as tables_router
from app.modules.tenants.router import router as tenants_router
from app.modules.waiter_calls.router import router as waiter_calls_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Le schéma n'est plus créé au démarrage : Alembic est la seule voie depuis
    la Phase 12.2 (`alembic upgrade head`, lancé par le CMD du Dockerfile avant
    uvicorn).

    `create_all()` était acceptable tant qu'aucune donnée réelle n'existait,
    mais il ne sait pas faire évoluer un schéma déjà peuplé : il crée ce qui
    manque et ignore silencieusement toute colonne ajoutée à un modèle. Avec de
    vraies commandes en base, ça se traduit par une colonne absente et une
    erreur SQL en pleine soirée de service.

    La suite de tests, elle, continue de construire son schéma avec
    `create_all()` sur SQLite en mémoire (voir tests/conftest.py) : c'est un
    schéma jetable recréé à chaque test, aucune migration n'a de sens là.
    """
    yield


logger = get_logger("app")

app = FastAPI(title="resto-qr-menu API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tenants_router)
app.include_router(staff_router)
app.include_router(staff_management_router)
app.include_router(tables_router)
app.include_router(menu_router)
app.include_router(orders_router)
app.include_router(stats_router)
app.include_router(notifications_router)
app.include_router(waiter_calls_router)
app.include_router(loyalty_router)


@app.get("/health")
def health(response: Response, db: Session = Depends(get_db)):
    """
    Sonde destinée à un monitoring externe (Phase 12.3).

    Elle vérifie la base, et pas seulement que le processus répond : sans ça,
    un Postgres injoignable laisse cette route renvoyer « ok » pendant que
    chaque commande échoue en salle — le monitoring dirait « tout va bien »
    précisément quand il faut réveiller quelqu'un.

    En cas d'échec : 503 (un moniteur externe déclenche sur le code HTTP) et
    un code stable, jamais le message de l'exception — cette route est
    publique et l'erreur SQL nomme l'hôte et la base.
    """
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("health.database_unreachable")
        response.status_code = 503
        return {"status": "degraded", "code": "DATABASE_UNREACHABLE"}
    return {"status": "ok"}
