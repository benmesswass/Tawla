"""
Crée ou met à jour un compte de l'opérateur de la plateforme (dashboard admin
cross-tenant, `/admin` côté frontend) — jamais une route d'inscription
publique, un seul canal de création : ce script, lancé à la main par Wassim.

Idempotent : relancer sur un e-mail déjà utilisé change le mot de passe, le
nom et réactive le compte, sans en créer un second.

Usage:
    cd backend && python scripts/create_platform_admin.py --email wassim@tawla.tn --name Wassim

Le mot de passe est demandé de façon interactive (jamais en argument de ligne
de commande, qui resterait en clair dans l'historique du shell).
"""
import argparse
import sys
from getpass import getpass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core import model_registry  # noqa: E402,F401 — sans lui, create_all()/l'ORM
# ignore les modèles jamais importés ailleurs (même piège que seed_demo.py)
from app.core.database import SessionLocal  # noqa: E402
from app.modules.platform_admin.models import PlatformAdmin  # noqa: E402
from app.modules.staff.security import hash_password  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()

    password = getpass("Mot de passe : ")
    confirm = getpass("Confirmer le mot de passe : ")
    if password != confirm:
        print("Les deux mots de passe ne correspondent pas.")
        raise SystemExit(1)
    if len(password) < 8:
        print("Mot de passe trop court (8 caractères minimum).")
        raise SystemExit(1)

    email = args.email.strip().lower()
    db = SessionLocal()
    try:
        admin = db.query(PlatformAdmin).filter(PlatformAdmin.email == email).first()
        if admin:
            admin.password_hash = hash_password(password)
            admin.name = args.name
            admin.is_active = True
            action = "mis à jour"
        else:
            admin = PlatformAdmin(email=email, name=args.name, password_hash=hash_password(password))
            db.add(admin)
            action = "créé"
        db.commit()
        print(f"Compte plateforme {action} : {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
