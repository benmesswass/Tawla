"""
Purge de rétention des données personnelles (Phase 16).

Quatre traitements, prévus par la politique de confidentialité publiée :

  1. les abonnements Web Push restés sur des commandes terminées — ils ne
     servent qu'à annoncer « votre commande est prête » ;
  2. les fiches fidélité sans commande depuis 24 mois — un numéro de téléphone
     conservé sans finalité est une conservation illégale au sens de la loi
     organique 2004-63 ;
  3. les établissements de démonstration échus — créés par « Voir la démo »
     sur le site, ils vivent deux heures et sont ensuite supprimés en entier.
     Ils se purgent déjà tout seuls à chaque nouvelle démo ; ce script les
     ramasse quand plus personne n'en lance ;
  4. les abonnements Web Push d'un membre du personnel désactivé (parti de
     l'établissement) — sans finalité une fois la personne partie.

Lancé à la main, pas par un ordonnanceur : le volume actuel ne le justifie pas
et une purge automatique mal réglée détruit des données irrécupérables. Par
défaut le script ne fait que compter ; il faut `--appliquer` pour supprimer.

Usage:
    python scripts/purge_donnees_personnelles.py              # simulation
    python scripts/purge_donnees_personnelles.py --appliquer  # supprime
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core import model_registry  # noqa: E402,F401 — sans lui, la ForeignKey
# `orders.restaurant_id` ne trouve pas la table `restaurants` et le premier
# commit lève NoReferencedTableError (constaté en lançant ce script).
from app.core.database import SessionLocal  # noqa: E402
from app.modules.demo import service as demo_service  # noqa: E402
from app.modules.loyalty import service as loyalty_service  # noqa: E402
from app.modules.orders import service as orders_service  # noqa: E402
from app.modules.staff import service as staff_service  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--appliquer",
        action="store_true",
        help="supprime réellement (sans ce drapeau, le script ne fait que compter)",
    )
    args = parser.parse_args()
    dry_run = not args.appliquer

    db = SessionLocal()
    try:
        pushes = orders_service.purge_terminal_push_subscriptions(db, dry_run=dry_run)
        members = loyalty_service.purge_inactive_members(db, dry_run=dry_run)
        # Une démo échue se supprime en entier — il n'y a rien à anonymiser
        # dedans, et rien à conserver : ce ne sont ni des commandes réelles ni
        # des clients réels.
        demos = len(demo_service.demos_expirees(db)) if dry_run else demo_service.purger_demos_expirees(db)
        staff_pushes = staff_service.purge_push_subscriptions_of_inactive_staff(db, dry_run=dry_run)
    finally:
        db.close()

    if dry_run:
        print(f"Abonnements push sur commandes terminées à supprimer : {pushes}")
        print(f"Fiches fidélité inactives depuis 24 mois à supprimer : {members}")
        print(f"Établissements de démonstration échus à supprimer : {demos}")
        print(f"Abonnements push de personnel désactivé à supprimer : {staff_pushes}")
    else:
        print(f"Abonnements push sur commandes terminées supprimés : {pushes}")
        print(f"Fiches fidélité inactives depuis 24 mois supprimées : {members}")
        print(f"Établissements de démonstration échus supprimés : {demos}")
        print(f"Abonnements push de personnel désactivé supprimés : {staff_pushes}")
    if dry_run:
        print("\nSimulation — rien n'a été supprimé. Relancer avec --appliquer.")


if __name__ == "__main__":
    main()
