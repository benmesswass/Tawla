"""
Déplace vers le stockage objet les photos déjà en base
(ROADMAP_PRODUCTION.md §P2.2).

Les routes de dépôt basculent d'elles-mêmes dès que `PHOTOS_S3_*` est
renseignée, mais **seulement pour les nouvelles photos** : une carte déjà
remplie resterait servie par le backend indéfiniment, et l'intérêt du chantier
— sortir ces transferts du processus applicatif et de son pool — ne se
réaliserait qu'au fil des remplacements, c'est-à-dire jamais.

Trois familles de photos, les trois `LargeBinary` du schéma : les plats, la
bannière de couverture et le logo. La bannière est la plus lourde et la plus
chargée du parcours client — elle s'ouvre sur le téléphone de chaque table.

**Idempotent** : une photo dont l'URL pointe déjà sur le stockage objet est
sautée. Relancer après une coupure reprend là où ça s'était arrêté.

**Simule par défaut**, comme `purge_donnees_personnelles.py` : il faut
`--appliquer` pour écrire quoi que ce soit. Une migration de photos n'est pas
destructrice (les octets ne sont retirés de la base qu'après un dépôt réussi),
mais elle écrit sur un service payant, et se tromper de bucket doit rester
rattrapable.

Usage:
    python scripts/migrer_photos.py              # simulation
    python scripts/migrer_photos.py --appliquer  # déplace pour de vrai
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal  # noqa: E402
from app.core.stockage_photos import stockage_photos  # noqa: E402
from app.modules.menu.models import MenuItem  # noqa: E402
from app.modules.tenants.models import Restaurant  # noqa: E402


def _a_migrer(url: str | None, octets: bytes | None) -> bool:
    """
    Une photo reste à migrer tant que ses octets sont en base. L'URL relative
    est le signe qu'elle est encore servie par le backend ; une URL absolue
    pointe déjà sur le CDN.
    """
    return bool(octets) and (not url or url.startswith("/"))


def _deplacer(db, proprietaire, prefixe: str, champ_url: str, champ_octets: str,
              champ_type: str, appliquer: bool) -> bool:
    url = getattr(proprietaire, champ_url)
    octets = getattr(proprietaire, champ_octets)
    if not _a_migrer(url, octets):
        return False
    if not appliquer:
        return True

    depot = stockage_photos.deposer(
        prefixe, octets, getattr(proprietaire, champ_type) or "image/jpeg", url or ""
    )
    # Les octets ne quittent la base qu'APRÈS un dépôt réussi : si le dépôt
    # lève, la ligne est intacte et le script peut être relancé.
    setattr(proprietaire, champ_url, depot.url)
    setattr(proprietaire, champ_octets, depot.octets)
    setattr(proprietaire, champ_type, depot.type_mime)
    db.commit()
    return True


def migrer(appliquer: bool) -> dict[str, int]:
    if not stockage_photos.hors_base:
        raise SystemExit(
            "Aucun stockage objet configuré : renseigner les cinq variables PHOTOS_S3_* "
            "(voir backend/.env.example) avant de lancer ce script."
        )

    comptes = {"plats": 0, "couvertures": 0, "logos": 0}
    db = SessionLocal()
    try:
        for plat in db.query(MenuItem).filter(MenuItem.image_data.isnot(None)).all():
            if _deplacer(db, plat, f"menu-items/{plat.id}", "image_url", "image_data",
                         "image_content_type", appliquer):
                comptes["plats"] += 1

        for restaurant in db.query(Restaurant).all():
            if _deplacer(db, restaurant, f"restaurants/{restaurant.id}/couverture",
                         "cover_photo_url", "cover_photo_data", "cover_photo_content_type", appliquer):
                comptes["couvertures"] += 1
            if _deplacer(db, restaurant, f"restaurants/{restaurant.id}/logo",
                         "logo_url", "logo_data", "logo_content_type", appliquer):
                comptes["logos"] += 1
    finally:
        db.close()
    return comptes


def main() -> None:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--appliquer", action="store_true",
                         help="déplace réellement les photos (sinon : simulation)")
    arguments = parseur.parse_args()

    comptes = migrer(arguments.appliquer)
    verbe = "déplacées" if arguments.appliquer else "à déplacer"
    print(f"Photos de plats {verbe}       : {comptes['plats']}")
    print(f"Bannières de couverture {verbe} : {comptes['couvertures']}")
    print(f"Logos {verbe}                 : {comptes['logos']}")
    if not arguments.appliquer:
        print("\nSimulation — rien n'a été écrit. Relancer avec --appliquer.")


if __name__ == "__main__":
    main()
