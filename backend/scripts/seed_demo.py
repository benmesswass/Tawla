"""
Seed de démo : un restaurant, 3 comptes staff (manager/serveur/cuisine),
quelques tables et un menu de départ. Idempotent — relancer le script ne
duplique rien (upsert par slug/email).

Écrit aussi CREDENTIALS.md à la racine du repo pour que Wassim (ou une
session future) retrouve les comptes de démo sans fouiller le code.

Usage:
    cd backend && python scripts/seed_demo.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.modules.menu.models import MenuItem  # noqa: E402
from app.modules.staff.models import Staff, StaffRole  # noqa: E402
from app.modules.staff.security import hash_password  # noqa: E402
from app.modules.tables.models import Table  # noqa: E402
from app.modules.tenants.models import Restaurant  # noqa: E402

DEMO_PASSWORD = "tawla2026"


def upsert_restaurant(db, name: str, slug: str) -> Restaurant:
    restaurant = db.query(Restaurant).filter(Restaurant.slug == slug).first()
    if restaurant:
        return restaurant
    restaurant = Restaurant(name=name, slug=slug)
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant


def upsert_staff(db, restaurant_id: int, name: str, role: StaffRole, email: str) -> Staff:
    staff = db.query(Staff).filter(Staff.email == email).first()
    if staff:
        # Le mot de passe est remis à celui que documente CLAUDE.md, et le
        # compte réactivé. Sans ça, un compte de démo dont le mot de passe a
        # dérivé — changé à la main pendant un essai, réactivé après une
        # désactivation — reste inutilisable, et relancer le seed n'y change
        # rien : on cherche alors le bug dans l'authentification.
        staff.password_hash = hash_password(DEMO_PASSWORD)
        staff.is_active = True
        db.commit()
        db.refresh(staff)
        return staff
    staff = Staff(
        restaurant_id=restaurant_id, name=name, role=role, email=email, password_hash=hash_password(DEMO_PASSWORD)
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


def upsert_table(db, restaurant_id: int, label: str) -> Table:
    table = db.query(Table).filter(Table.restaurant_id == restaurant_id, Table.label == label).first()
    if table:
        return table
    table = Table(restaurant_id=restaurant_id, label=label)
    db.add(table)
    db.commit()
    db.refresh(table)
    return table


def upsert_menu_item(db, restaurant_id: int, name: str, category: str, price: float) -> MenuItem:
    item = db.query(MenuItem).filter(MenuItem.restaurant_id == restaurant_id, MenuItem.name == name).first()
    if item:
        return item
    item = MenuItem(restaurant_id=restaurant_id, name=name, category=category, price=price)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    restaurant = upsert_restaurant(db, "Dar Chaabane", "dar-chaabane")

    manager = upsert_staff(db, restaurant.id, "Amine (manager)", StaffRole.MANAGER, "manager@tawla.tn")
    waiter = upsert_staff(db, restaurant.id, "Sami (serveur)", StaffRole.WAITER, "sami@tawla.tn")
    kitchen = upsert_staff(db, restaurant.id, "Karim (cuisine)", StaffRole.KITCHEN, "cuisine@tawla.tn")

    tables = [upsert_table(db, restaurant.id, f"Table {i}") for i in range(1, 4)]

    upsert_menu_item(db, restaurant.id, "Salade méchouia", "Entrées", 6)
    upsert_menu_item(db, restaurant.id, "Couscous au poisson", "Plats", 22)
    upsert_menu_item(db, restaurant.id, "Baklawa", "Desserts", 5)
    upsert_menu_item(db, restaurant.id, "Thé à la menthe", "Boissons", 3)

    credentials = f"""# Comptes démo — Tawla

Restaurant : {restaurant.name} (id {restaurant.id}, slug `{restaurant.slug}`)
Mot de passe pour tous les comptes : `{DEMO_PASSWORD}`

| Rôle | E-mail | Nom |
|---|---|---|
| Manager | {manager.email} | {manager.name} |
| Serveur | {waiter.email} | {waiter.name} |
| Cuisine | {kitchen.email} | {kitchen.name} |

## Tables (QR codes)

{chr(10).join(f"- {t.label} : qr_token=`{t.qr_token}` → /menu/{t.qr_token}" for t in tables)}

Générer l'image QR à imprimer avec `scripts/generate_table_qr.py` (voir README.md).
"""
    db.close()

    Path(__file__).resolve().parent.parent.parent.joinpath("CREDENTIALS.md").write_text(credentials)

    print("Seed terminé.")
    print(credentials)


if __name__ == "__main__":
    main()
