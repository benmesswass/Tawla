"""
F-1 (audit de pré-lancement) : `scripts/seed_demo.py` créait le schéma avec
`Base.metadata.create_all()` sans importer `model_registry` — sur une base
neuve créée hors Docker, `orders`, `order_items`, `loyalty_members` et
`waiter_calls` n'existaient jamais, et la première commande répondait 500.

Le filet global (`tests/conftest.py`) importe `model_registry` avant même de
collecter les tests : dans ce même process, `Base.metadata` connaît déjà tous
les modèles, donc aucun test de ce process ne peut voir ce que produirait le
script seul. Ce test lance donc un process Python isolé qui exécute
exactement ce que fait `scripts/seed_demo.py`, sans ce filet.
"""
import subprocess
import sys
import textwrap
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_PATH = BACKEND_DIR.parent / "CREDENTIALS.md"


def test_le_script_de_seed_permet_de_passer_une_commande(tmp_path):
    # `seed_demo.main()` régénère CREDENTIALS.md à la racine du dépôt — un
    # fichier local de Wassim, pas un artefact de test. On restaure son
    # contenu d'origine après coup, quel que soit le résultat du test.
    original_credentials = CREDENTIALS_PATH.read_text() if CREDENTIALS_PATH.exists() else None

    db_path = tmp_path / "seed_demo_test.db"
    script = textwrap.dedent(f"""
        import os
        import sys

        sys.path.insert(0, {str(BACKEND_DIR)!r})
        os.environ["DATABASE_URL"] = "sqlite:///{db_path}"

        import scripts.seed_demo as seed_demo
        seed_demo.main()

        from app.core.database import SessionLocal
        from app.modules.menu.models import MenuItem
        from app.modules.tables.models import Table
        from app.modules.tenants.models import Restaurant

        db = SessionLocal()
        restaurant = db.query(Restaurant).first()
        table = db.query(Table).filter(Table.restaurant_id == restaurant.id).first()
        item = db.query(MenuItem).filter(MenuItem.restaurant_id == restaurant.id).first()
        db.close()

        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        response = client.post(
            "/api/v1/orders",
            json={{"qr_token": table.qr_token, "items": [{{"menu_item_id": item.id, "quantity": 1}}]}},
        )
        assert response.status_code == 201, response.text
        print("ORDER_OK")
    """)

    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            cwd=BACKEND_DIR,
            timeout=60,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "ORDER_OK" in result.stdout, result.stdout + result.stderr
    finally:
        if original_credentials is None:
            CREDENTIALS_PATH.unlink(missing_ok=True)
        else:
            CREDENTIALS_PATH.write_text(original_credentials)
