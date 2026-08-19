"""
Installe un établissement pilote en une passe.

Avant ce script, installer un restaurant demandait une dizaine d'appels Swagger
enchaînés à la main, sur place, devant le patron. Il fait tout d'un coup :
restaurant, compte manager, comptes de l'équipe, tables et zones, carte importée
depuis un CSV, chevalets QR prêts à imprimer, et une fiche de remise des
identifiants.

Idempotent : relancer le script sur la même configuration ne duplique rien
(reprise par slug, e-mail et libellé de table). C'est ce qui permet de corriger
un fichier de carte et de relancer sans repartir de zéro.

Usage:
    cd backend
    python scripts/setup_restaurant.py --config pilote.json
    python scripts/setup_restaurant.py --config pilote.json --frontend-url https://tawla.tn

Le fichier de configuration est un JSON préparé à l'avance (modèle :
`scripts/pilote-exemple.json`).
"""
import argparse
import json
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal  # noqa: E402
from app.modules.menu.csv_import import apply_items, parse_menu_csv  # noqa: E402
from app.modules.staff.models import Staff, StaffRole  # noqa: E402
from app.modules.staff.security import hash_password  # noqa: E402
from app.modules.tables.models import Table  # noqa: E402
from app.modules.tables.qr_card import save_table_card  # noqa: E402
from app.modules.tenants.models import Restaurant, SubscriptionTier  # noqa: E402


def slugify(name: str) -> str:
    import re
    import unicodedata

    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-") or "restaurant"


def generated_password() -> str:
    """Assez court pour être dicté au téléphone, pas devinable."""
    return secrets.token_urlsafe(9)


def upsert_restaurant(db, name: str, slug: str, subscription_tier: SubscriptionTier) -> tuple[Restaurant, bool]:
    """
    Le palier vendu est celui du contrat signé sur place — pas de portail de
    changement de palier en self-service tant que la facturation reste
    manuelle (offre à trois paliers, 2026-08-18) : c'est en relançant ce
    script, avec la config mise à jour, qu'un pilote passe d'un palier à un
    autre après un appel avec Wassim.
    """
    existing = db.query(Restaurant).filter(Restaurant.slug == slug).first()
    if existing:
        if existing.subscription_tier != subscription_tier:
            existing.subscription_tier = subscription_tier
            db.commit()
        return existing, False
    restaurant = Restaurant(name=name, slug=slug, subscription_tier=subscription_tier)
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant, True


def upsert_staff(db, restaurant_id: int, name: str, role: StaffRole, email: str) -> tuple[Staff, str | None]:
    """Renvoie le compte et, s'il vient d'être créé, son mot de passe en clair —
    la seule occasion de le lire."""
    email = email.lower()
    existing = db.query(Staff).filter(Staff.email == email).first()
    if existing:
        return existing, None
    password = generated_password()
    staff = Staff(
        restaurant_id=restaurant_id,
        name=name,
        role=role,
        email=email,
        password_hash=hash_password(password),
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff, password


def upsert_table(db, restaurant_id: int, label: str, zone: str | None) -> tuple[Table, bool]:
    existing = (
        db.query(Table).filter(Table.restaurant_id == restaurant_id, Table.label == label).first()
    )
    if existing:
        # La zone peut avoir été corrigée entre deux passes ; le qr_token, lui,
        # ne change JAMAIS — les chevalets sont peut-être déjà imprimés et collés.
        if zone and existing.zone != zone:
            existing.zone = zone
            db.commit()
        return existing, False
    table = Table(restaurant_id=restaurant_id, label=label, zone=zone)
    db.add(table)
    db.commit()
    db.refresh(table)
    return table, True


def expand_tables(spec: list[dict]) -> list[tuple[str, str | None]]:
    """
    Deux écritures possibles, selon ce que le patron sait dire :
    - {"zone": "Terrasse", "count": 6}          -> Terrasse 1 … Terrasse 6
    - {"zone": "Salle", "labels": ["T1", "T2"]} -> libellés exacts
    """
    tables: list[tuple[str, str | None]] = []
    for group in spec:
        zone = group.get("zone")
        if group.get("labels"):
            tables.extend((str(label), zone) for label in group["labels"])
            continue
        count = int(group.get("count", 0))
        prefix = group.get("prefix") or zone or "Table"
        tables.extend((f"{prefix} {i}", zone) for i in range(1, count + 1))
    return tables


def import_menu(db, restaurant_id: int, csv_path: Path) -> tuple[str, list[str]]:
    """Même fusion par nom que l'import du dashboard (`menu/csv_import.py`) :
    relancer le script après avoir corrigé la carte met à jour les prix au lieu
    de créer des doublons."""
    result = parse_menu_csv(csv_path.read_text(encoding="utf-8"))
    applied = apply_items(db, restaurant_id, result.items)
    summary = f"{applied.created_count} créé(s), {applied.updated_count} mis à jour"
    return summary, result.errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path, help="JSON de configuration du pilote")
    parser.add_argument("--frontend-url", default="http://localhost:3000", help="URL encodée dans les QR")
    parser.add_argument("--qr-dir", type=Path, default=None, help="Dossier des chevalets (défaut : ./qr-<slug>)")
    parser.add_argument("--no-qr", action="store_true", help="Ne pas générer les images")
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    name = config["restaurant"]["name"]
    slug = config["restaurant"].get("slug") or slugify(name)
    # Essentiel par défaut si absent du fichier : c'est déjà le défaut du
    # modèle, pas une omission qui déverrouillerait Pro/Business par erreur.
    subscription_tier = SubscriptionTier(config["restaurant"].get("subscription_tier", "essentiel"))

    db = SessionLocal()
    restaurant, created_restaurant = upsert_restaurant(db, name, slug, subscription_tier)
    print(
        f"{'Créé' if created_restaurant else 'Existant'} : {restaurant.name} (id {restaurant.id}, "
        f"palier {restaurant.subscription_tier.value})"
    )

    # --- Comptes ---
    accounts: list[tuple[Staff, str | None]] = []
    manager_config = config["manager"]
    accounts.append(
        upsert_staff(db, restaurant.id, manager_config["name"], StaffRole.MANAGER, manager_config["email"])
    )
    for member in config.get("staff", []):
        accounts.append(
            upsert_staff(db, restaurant.id, member["name"], StaffRole(member["role"]), member["email"])
        )
    for staff, password in accounts:
        print(f"  {staff.role.value:<8} {staff.email:<32} {'mot de passe : ' + password if password else '(déjà créé)'}")

    # --- Tables ---
    tables: list[Table] = []
    for label, zone in expand_tables(config.get("tables", [])):
        table, was_created = upsert_table(db, restaurant.id, label, zone)
        tables.append(table)
        print(f"  table {label:<16} {'créée' if was_created else 'existante'}")

    # --- Carte ---
    menu_errors: list[str] = []
    if config.get("menu_csv"):
        csv_path = (args.config.parent / config["menu_csv"]).resolve()
        summary, menu_errors = import_menu(db, restaurant.id, csv_path)
        print(f"  carte ({csv_path.name}) : {summary}")
        for error in menu_errors:
            print(f"    ! {error}")

    # --- Chevalets ---
    qr_dir = args.qr_dir or Path(f"qr-{slug}")
    if not args.no_qr:
        for table in tables:
            url = f"{args.frontend_url.rstrip('/')}/menu/{table.qr_token}"
            path = save_table_card(
                qr_dir / f"{slugify(table.label)}.png",
                menu_url=url,
                table_label=table.label,
                restaurant_name=restaurant.name,
                zone=table.zone,
            )
            print(f"  chevalet {path}")

    # --- Fiche de remise ---
    lines = [
        f"# Installation — {restaurant.name}",
        "",
        "Fiche de remise des accès. **À imprimer ou à recopier, puis à supprimer de l'ordinateur** :",
        "les mots de passe ci-dessous ne sont plus lisibles ailleurs.",
        "",
        "## Comptes",
        "",
        "| Rôle | E-mail | Mot de passe |",
        "|---|---|---|",
    ]
    for staff, password in accounts:
        lines.append(f"| {staff.role.value} | {staff.email} | {password or '(inchangé)'} |")
    lines += [
        "",
        "Le manager peut créer d'autres comptes et régénérer un mot de passe depuis",
        "l'onglet « Équipe » du dashboard.",
        "",
        "## Tables",
        "",
        "| Table | Zone | Chevalet |",
        "|---|---|---|",
    ]
    for table in tables:
        card = "—" if args.no_qr else f"`{qr_dir}/{slugify(table.label)}.png`"
        lines.append(f"| {table.label} | {table.zone or '—'} | {card} |")
    if menu_errors:
        lines += ["", "## Lignes de carte à corriger", ""] + [f"- {e}" for e in menu_errors]
    lines += [
        "",
        "## Avant le premier service",
        "",
        "- Imprimer les chevalets (4 par page A4) et les poser sur les tables.",
        "- Vérifier un scan réel avec deux téléphones différents, dont un ancien.",
        "- Ouvrir l'écran cuisine sur son appareil et le laisser branché.",
        "- Relever la semaine de référence : commandes perdues et panier moyen,",
        "  avant d'activer la commande par QR (voir /dashboard/preuve).",
        "",
    ]

    handover = qr_dir / "INSTALLATION.md" if not args.no_qr else Path(f"INSTALLATION-{slug}.md")
    handover.parent.mkdir(parents=True, exist_ok=True)
    handover.write_text("\n".join(lines), encoding="utf-8")
    db.close()

    print(f"\nFiche de remise : {handover}")
    print("Les mots de passe ne sont lisibles que dans cette fiche et dans la sortie ci-dessus.")


if __name__ == "__main__":
    main()
