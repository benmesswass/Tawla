"""
Chiffrement au repos des identifiants de paiement propres à un restaurant
(clé API Konnect — modèle direct, connexion Konnect au paiement carte,
2026-08-19) : contrairement au wallet de Tawla elle-même (une simple
variable d'environnement, jamais en base), la clé d'un restaurant tiers est
stockée en base et ne doit jamais y être lisible en clair.

Clé dédiée `FIELD_ENCRYPTION_KEY` (Fernet, base64) si fournie, sinon dérivée
de `JWT_SECRET` avec séparation de domaine — même principe que
`konnect._webhook_key()`.
"""
import base64
import os
from hashlib import sha256

from cryptography.fernet import Fernet, InvalidToken


def _fernet() -> Fernet:
    dedicated = os.environ.get("FIELD_ENCRYPTION_KEY")
    if dedicated:
        return Fernet(dedicated.encode("utf-8"))

    from app.core.config import settings

    derived = sha256(f"{settings.jwt_secret}:field-encryption".encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(derived))


def encrypt_field(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_field(value: str) -> str | None:
    """`None` sur une valeur illisible (mauvaise clé, donnée corrompue)
    plutôt qu'une exception : appelant traité comme "non configuré", jamais
    un 500 sur un restaurant dont la clé de chiffrement aurait changé."""
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None
