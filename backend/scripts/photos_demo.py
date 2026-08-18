"""
Pose une photo sur chaque plat du jeu de démo (scripts/seed_demo.py).

Sans photos, la carte client ne montre ni ses vignettes ni le halo coloré qui
les détache du fond : la démo donne une impression fausse de ce que voit un
vrai client. Ce script n'existe que pour ça — un établissement réel reçoit ses
photos par le glisser-déposer du dashboard, jamais par un script.

Les images viennent de Wikimedia Commons, sous licence libre et vérifiables :
chaque entrée cite son fichier d'origine et sa licence. Elles sont téléchargées
puis écrites en base comme le ferait un dépôt manuel, donc servies ensuite par
`GET /api/v1/menu-items/{id}/image`.

Usage :
    cd backend && python scripts/photos_demo.py
"""
import sys
import urllib.request
from hashlib import sha256
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core import model_registry  # noqa: F401,E402 — enregistre tous les modèles
from app.core.database import SessionLocal  # noqa: E402
from app.modules.menu.models import MenuItem  # noqa: E402

# nom du plat -> (fichier Commons, licence, URL de la vignette 1280 px)
PHOTOS = {
    "Salade méchouia": (
        "Salade Mechouwya, Tunisie, juin 2021.jpg",
        "CC BY-SA 4.0",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7f/"
        "Salade_Mechouwya%2C_Tunisie%2C_juin_2021.jpg/1280px-Salade_Mechouwya%2C_Tunisie%2C_juin_2021.jpg",
    ),
    "Couscous au poisson": (
        "Couscous aux poissons, Tunisie, 22 juin 2019.jpg",
        "CC BY 4.0",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9b/"
        "Couscous_aux_poissons%2C_Tunisie%2C_22_juin_2019.jpg/"
        "1280px-Couscous_aux_poissons%2C_Tunisie%2C_22_juin_2019.jpg",
    ),
    "Baklawa": (
        "Baklava - Turkish special, 80-ply.JPEG",
        "Domaine public",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/"
        "Baklava_-_Turkish_special%2C_80-ply.JPEG/1280px-Baklava_-_Turkish_special%2C_80-ply.JPEG",
    ),
    "Thé à la menthe": (
        "Moroccan mint tea on a traditional tray.jpg",
        "CC BY-SA 4.0",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/7/72/"
        "Moroccan_mint_tea_on_a_traditional_tray.jpg/1280px-Moroccan_mint_tea_on_a_traditional_tray.jpg",
    ),
}


def telecharger(url: str) -> bytes:
    # Wikimedia refuse les requêtes sans agent identifiable.
    requete = urllib.request.Request(url, headers={"User-Agent": "Tawla-demo/1.0 (contact@tawla.tn)"})
    with urllib.request.urlopen(requete, timeout=30) as reponse:
        return reponse.read()


def main() -> None:
    db = SessionLocal()
    try:
        for nom, (fichier, licence, url) in PHOTOS.items():
            plat = db.query(MenuItem).filter(MenuItem.name == nom).first()
            if not plat:
                print(f"— {nom} : absent de la base, ignoré")
                continue

            contenu = telecharger(url)
            plat.image_data = contenu
            plat.image_content_type = "image/jpeg"
            plat.image_url = f"/api/v1/menu-items/{plat.id}/image?v={sha256(contenu).hexdigest()[:12]}"
            db.commit()
            print(f"✓ {nom} : {len(contenu) // 1024} Ko — {fichier} ({licence})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
