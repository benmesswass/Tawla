from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    # Dimensionné explicitement depuis le 2026-09-10 (ROADMAP_PRODUCTION.md
    # §P1.3) : les défauts de SQLAlchemy (5 + 10, attente 30 s) n'étaient pas
    # un choix, et ils fixaient le plafond de capacité de toute la
    # plateforme. Les valeurs vivent dans `Settings` — le bon dimensionnement
    # dépend du plan Postgres et du nombre d'instances, qui changeront.
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_recycle=settings.db_pool_recycle,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency FastAPI : une session DB par requête, fermée proprement."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
