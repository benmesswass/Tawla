import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import log_event
from app.core.rate_limit import rate_limit
from app.modules.demo import schemas, service
from app.modules.staff import security

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])
logger = logging.getLogger("demo")


@router.post(
    "/sessions",
    response_model=schemas.DemoSessionOut,
    status_code=201,
    # Trois par minute et par adresse : de quoi recommencer une démo ratée,
    # pas de quoi en scripter mille. C'est la seule route publique du produit
    # qui crée un établissement.
    dependencies=[Depends(rate_limit(max_requests=3))],
)
def create_demo_session(db: Session = Depends(get_db)):
    """
    Monte un établissement de démonstration jetable et connecte le visiteur
    dessus, en manager.

    Un établissement par visiteur, et non un compte de démo partagé : les
    canaux temps réel sont groupés par restaurant, deux démos simultanées sur
    le même établissement se verraient l'une l'autre (voir
    `demo/service.py`). Ici, deux visiteurs = deux restaurants = deux canaux.

    Tout est supprimé au bout de deux heures (`DUREE_DEMO`), purge déclenchée
    à chaque création — la démo se nettoie donc sans ordonnanceur.
    """
    if service.demos_vivantes(db) >= service.PLAFOND_DEMOS:
        # On refuse plutôt que de laisser la base enfler : la démo est un
        # outil de vente, pas un service à garantir.
        log_event(logger, "demo.plafond_atteint", plafond=service.PLAFOND_DEMOS)
        raise HTTPException(
            status_code=503,
            detail={
                "code": "DEMO_UNAVAILABLE",
                "message": "too many demos running right now, try again in a few minutes",
            },
        )

    restaurant, manager, table = service.creer_demo(db)
    token = security.create_access_token(manager.id, manager.restaurant_id, manager.role.value)
    return schemas.DemoSessionOut(
        access_token=token,
        staff=manager,
        restaurant_id=restaurant.id,
        restaurant_name=restaurant.name,
        qr_token=table.qr_token,
        expires_at=service.expiration_restante(restaurant),
    )
