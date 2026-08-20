from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DashboardView(Base):
    """
    Une ligne = une ouverture du tableau de bord manager. Instrumentation
    minimale pour la rétention (ROADMAP.md Phase 24) : « le produit sait dire
    ce qu'un restaurant encaisse, pas si son patron l'a regardé — or c'est ce
    signal qui précède une résiliation de deux mois ».

    Enregistrée à chaque appel de `stats/service.py::get_dashboard_stats`,
    donc à chaque ouverture de `/dashboard` ou `/dashboard/stats` — un manager
    qui navigue entre plusieurs journées passées produit donc plusieurs
    lignes pour une seule visite. Signal volontairement approximatif (pas de
    déduplication de session, pas d'infra analytics séparée) : suffisant pour
    repérer un restaurant qui a cessé de regarder, pas pour compter des
    sessions uniques.
    """

    __tablename__ = "dashboard_views"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), nullable=False, index=True)
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
