from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import model_registry  # noqa: F401 — enregistre tous les modèles
from app.core.config import settings
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
def health():
    return {"status": "ok"}
