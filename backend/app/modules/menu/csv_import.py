"""
Import d'une carte depuis un CSV.

Saisir 30 plats un par un dans le dashboard est le premier abandon probable
d'un restaurateur (Phase 13.2). Ce module est le seul endroit où le format est
défini : il sert à la fois l'endpoint du dashboard et le script d'installation
`scripts/setup_restaurant.py`, pour qu'il n'existe jamais deux formats
divergents.

Le fichier attendu est celui qu'un patron produit réellement : un export Excel
ou LibreOffice, en français, avec des prix à virgule décimale et des colonnes
qu'il n'a pas nommées exactement comme nous. Le lecteur est donc tolérant sur
la casse, les accents et les alias — mais strict sur le prix, seule donnée qu'on
ne peut pas deviner sans risque de facturer un client au mauvais montant.
"""
import csv
import io
import unicodedata
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.markets import current_market
from app.modules.menu.models import MenuItem

# Colonnes reconnues -> alias acceptés (normalisés : minuscules, sans accent).
_COLUMNS: dict[str, tuple[str, ...]] = {
    "name": ("nom", "name", "plat", "article", "designation", "libelle"),
    "category": ("categorie", "category", "famille", "rubrique"),
    "price": ("prix", "price", "tarif", "prix ttc", "montant"),
    "description": ("description", "detail", "details", "commentaire"),
    "spice_level": ("piment", "spice", "spice level", "niveau de piment"),
    "allergens": ("allergenes", "allergens", "allergie", "allergies"),
    "is_halal": ("halal", "is halal"),
    # F5-A6 (MARCHE_FRANCE.md) : codes INCO séparés par une virgule, tels
    # qu'attendus par frontend/lib/allergens.ts — colonne distincte de
    # `allergens` (texte libre), pas une conversion automatique de l'un vers
    # l'autre : un patron qui remplit l'un ne remplit pas forcément l'autre.
    "allergen_codes": ("allergenes ue", "codes allergenes", "allergen codes", "inco"),
    "is_vegetarian": ("vegetarien", "vegetarian"),
    "is_vegan": ("vegan", "vegetalien"),
    "is_gluten_free": ("sans gluten", "gluten free"),
}

_TRUE_VALUES = {"1", "oui", "yes", "true", "vrai", "o", "y"}
_FALSE_VALUES = {"0", "non", "no", "false", "faux", "n"}

MAX_ROWS = 500


def _normalize(value: str) -> str:
    stripped = unicodedata.normalize("NFKD", value.strip().lower())
    return "".join(c for c in stripped if not unicodedata.combining(c))


@dataclass
class ParsedItem:
    name: str
    category: str
    price: float
    description: str | None = None
    spice_level: int = 0
    allergens: str | None = None
    is_halal: bool = field(default_factory=lambda: current_market().code != "fr")
    allergen_codes: str | None = None
    is_vegetarian: bool = False
    is_vegan: bool = False
    is_gluten_free: bool = False


@dataclass
class ParseResult:
    items: list[ParsedItem] = field(default_factory=list)
    # Une erreur par ligne fautive, en français et avec le numéro de ligne du
    # fichier : le manager doit pouvoir corriger son tableur sans nous appeler.
    errors: list[str] = field(default_factory=list)


def _detect_dialect(content: str) -> str:
    """
    Un export Excel en locale française utilise le point-virgule. Sniffer sur
    l'en-tête suffit et évite de dépendre de csv.Sniffer, qui se trompe quand
    une description contient une virgule.
    """
    header = content.splitlines()[0] if content.splitlines() else ""
    return ";" if header.count(";") > header.count(",") else ","


def _parse_price(raw: str) -> float:
    # « 12,500 » et « 12.5 » désignent le même prix : le dinar se note à trois
    # décimales en Tunisie, et un tableur français écrit la virgule.
    cleaned = raw.strip().replace(" ", "").replace(" ", "").replace(",", ".")
    if not cleaned:
        raise ValueError("prix manquant")
    try:
        price = float(cleaned)
    except ValueError:
        # Ne jamais laisser remonter le message de float() : ces lignes sont
        # lues par un restaurateur dans son dashboard, pas par un développeur.
        raise ValueError(f"prix illisible « {raw.strip()} »") from None
    if price < 0:
        raise ValueError("prix négatif")
    return price


def _parse_bool(raw: str, default: bool) -> bool:
    value = _normalize(raw)
    if not value:
        return default
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    raise ValueError(f"valeur oui/non attendue, reçu « {raw.strip()} »")


def _parse_spice(raw: str) -> int:
    value = raw.strip()
    if not value:
        return 0
    try:
        level = int(value)
    except ValueError:
        raise ValueError(f"niveau de piment illisible « {value} », attendu 0 à 3") from None
    if not 0 <= level <= 3:
        raise ValueError("le niveau de piment doit être entre 0 et 3")
    return level


def parse_menu_csv(content: str) -> ParseResult:
    """
    Lit le CSV et renvoie les articles valides ET les erreurs ligne par ligne.

    Ne lève jamais sur une ligne fautive : un fichier de 40 plats dont un a un
    prix mal saisi doit importer les 39 autres et dire précisément lequel
    corriger. Tout ou rien ferait recommencer la saisie pour une faute de frappe.
    """
    result = ParseResult()
    content = content.lstrip("﻿")  # BOM des exports Excel
    if not content.strip():
        result.errors.append("Le fichier est vide.")
        return result

    reader = csv.DictReader(io.StringIO(content), delimiter=_detect_dialect(content))
    if not reader.fieldnames:
        result.errors.append("Le fichier n'a pas de ligne d'en-tête.")
        return result

    # En-tête réel -> nom de champ interne.
    mapping: dict[str, str] = {}
    for raw_header in reader.fieldnames:
        normalized = _normalize(raw_header or "")
        for field_name, aliases in _COLUMNS.items():
            if normalized in aliases:
                mapping[raw_header] = field_name
                break

    missing = {"name", "price"} - set(mapping.values())
    if missing:
        result.errors.append(
            "Colonnes obligatoires absentes : "
            + ", ".join("nom" if m == "name" else "prix" for m in sorted(missing))
            + ". Colonnes trouvées : "
            + ", ".join(h for h in reader.fieldnames if h)
            + "."
        )
        return result

    for line_number, row in enumerate(reader, start=2):  # ligne 1 = en-tête
        values = {mapping[h]: (row.get(h) or "") for h in mapping}
        name = values.get("name", "").strip()
        if not name and not any(v.strip() for v in values.values()):
            continue  # ligne vide en fin de fichier
        if not name:
            result.errors.append(f"Ligne {line_number} : nom du plat manquant.")
            continue
        if len(result.items) >= MAX_ROWS:
            result.errors.append(
                f"Fichier tronqué à {MAX_ROWS} articles — importez le reste dans un second fichier."
            )
            break

        try:
            item = ParsedItem(
                name=name[:120],
                category=(values.get("category") or "").strip()[:60] or "Autre",
                price=_parse_price(values.get("price", "")),
                description=((values.get("description") or "").strip() or None),
                spice_level=_parse_spice(values.get("spice_level", "")),
                allergens=((values.get("allergens") or "").strip() or None),
                is_halal=_parse_bool(values.get("is_halal", ""), default=current_market().code != "fr"),
                allergen_codes=((values.get("allergen_codes") or "").strip()[:200] or None),
                is_vegetarian=_parse_bool(values.get("is_vegetarian", ""), default=False),
                is_vegan=_parse_bool(values.get("is_vegan", ""), default=False),
                is_gluten_free=_parse_bool(values.get("is_gluten_free", ""), default=False),
            )
        except ValueError as exc:
            result.errors.append(f"Ligne {line_number} ({name}) : {exc}.")
            continue

        result.items.append(item)

    if not result.items and not result.errors:
        result.errors.append("Aucun article trouvé dans le fichier.")
    return result


@dataclass
class ApplyResult:
    created_count: int = 0
    updated_count: int = 0
    disabled_count: int = 0


def apply_items(
    db: Session, restaurant_id: int, items: list[ParsedItem], *, disable_missing: bool = False
) -> ApplyResult:
    """
    Écrit la carte lue en base, **en fusionnant par nom**.

    Le geste réel d'un restaurateur n'est pas « importer une fois » : c'est
    « j'ai corrigé mon fichier, remets-le ». Créer systématiquement lui
    donnerait sa carte en double à la deuxième passe — c'est exactement ce qui
    s'est produit au premier test en navigateur. Un article déjà connu est donc
    mis à jour (prix, catégorie, description…) et redevient disponible.

    `disable_missing` traite le cas « ce fichier est ma carte complète » : les
    articles absents du fichier sont rendus indisponibles. Jamais supprimés —
    une commande passée référence son `menu_item_id`, et le prix figé sur la
    ligne de commande doit rester rattachable à un article existant.

    Partagé par l'endpoint du dashboard et `scripts/setup_restaurant.py`, pour
    que l'installation sur place et l'import par le patron se comportent
    identiquement.
    """
    result = ApplyResult()
    existing = {
        item.name.strip().lower(): item
        for item in db.query(MenuItem).filter(MenuItem.restaurant_id == restaurant_id).all()
    }
    seen: set[str] = set()

    for parsed in items:
        key = parsed.name.strip().lower()
        seen.add(key)
        current = existing.get(key)
        if current is None:
            db.add(MenuItem(restaurant_id=restaurant_id, **vars(parsed)))
            result.created_count += 1
            continue
        for attribute, value in vars(parsed).items():
            setattr(current, attribute, value)
        current.is_available = True
        result.updated_count += 1

    if disable_missing:
        for key, item in existing.items():
            if key not in seen and item.is_available:
                item.is_available = False
                result.disabled_count += 1

    db.commit()
    return result
