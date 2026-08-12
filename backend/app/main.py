from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import model_registry  # noqa: F401 — enregistre tous les modèles
from app.core.config import settings
from app.core.database import Base, engine
from app.modules.loyalty.router import router as loyalty_router
from app.modules.menu.router import router as menu_router
from app.modules.notifications.router import router as notifications_router
from app.modules.orders.router import router as orders_router
from app.modules.staff.router import router as staff_router
from app.modules.stats.router import router as stats_router
from app.modules.tables.router import router as tables_router
from app.modules.tenants.router import router as tenants_router
from app.modules.waiter_calls.router import router as waiter_calls_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # MVP : create_all suffit au démarrage. Alembic est configuré depuis
    # Phase 10 (`alembic/`, migration initiale `81067c492c21` qui reflète
    # exactement ce schéma — vérifié par diff de schéma contre une base
    # vierge) mais pas encore le mécanisme de migration actif : create_all
    # reste la voie utilisée tant qu'il n'y a pas de vraie prod avec des
    # données (bascule prévue au déploiement réel, cf. ROADMAP.md Phase 10).
    # Important : ça ne s'exécute qu'au vrai démarrage de l'app, jamais à
    # l'import du module — sinon les tests tentent de se connecter à la
    # vraie base Postgres au lieu de leur propre base de test.
    Base.metadata.create_all(bind=engine)
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
