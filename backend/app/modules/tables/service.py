from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.tables.models import Table


def get_table_by_qr_token(db: Session, qr_token: str) -> Table:
    """
    Point d'entrée unique de tout le parcours client : c'est le scan du QR qui
    rattache un appel anonyme à une table, donc à un restaurant. Quatre routes
    le faisaient chacune de leur côté (menu, commande, appel serveur, fiche
    restaurant), et la fidélité en fait une cinquième.

    Le 404 est identique partout, et volontairement : un token inconnu ne doit
    jamais se distinguer d'un token valide sur une autre table, sinon la
    réponse elle-même dit lesquels existent.
    """
    table = db.query(Table).filter(Table.qr_token == qr_token).first()
    if not table:
        raise HTTPException(
            status_code=404,
            detail={"code": "INVALID_TABLE_CODE", "message": "invalid table code"},
        )
    return table
