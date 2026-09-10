"""
Répartition de l'addition par personne (identité de table, ROADMAP.md
§Override, extension paiement par personne) — port côté serveur du bloc
Répartition affiché au paiement (`frontend/app/menu/[qrToken]/page.tsx`).

`OrderItem.is_shared`/`shared_with`/`added_by_name` sont la source du montant
réellement facturé à chacun en mode "par plat" — le serveur ne fait pas
confiance à un montant fourni par le client, il le recalcule lui-même à
partir de ces mêmes données et du roster courant de la table, exactement
comme il refige déjà les prix à la création de la commande (voir
`_build_order_items`). Le mode "équitable" (décision Wassim du 2026-09-10,
chantier hiérarchie du paiement) diffuse le total à parts identiques et
ignore l'attribution par plat — les deux modes restent un choix RÉEL, pas un
affichage : c'est `mode` qui détermine ce qui est débité, jamais une
simulation à part (voir `tables/split_mode.py` pour où ce choix est mémorisé
et diffusé aux appareils de la table).
"""
from typing import Literal

from app.modules.orders.models import Order

SplitMode = Literal["items", "equal"]
DEFAULT_SPLIT_MODE: SplitMode = "items"


def compute_shares(order: Order, names: list[str], mode: SplitMode = DEFAULT_SPLIT_MODE) -> dict[str, float]:
    """
    `names` : le roster de la table, dans l'ordre où chacun l'a rejointe
    (voir `tables/roster.py::TableRosterStore.snapshot`) — position 1..N,
    même convention que `OrderItem.shared_with`. Renvoie {prénom: montant dû},
    une entrée par nom (des prénoms en double fusionnent leur montant sous la
    même clé — cas rare et purement cosmétique, déjà accepté côté
    `added_by_name`).
    """
    n = len(names)
    if n == 0:
        return {}
    if mode == "equal":
        part = float(order.total_amount) / n
        return {name: part for name in names}
    totals = [0.0] * n
    for item in order.items:
        line_total = float(item.unit_price) * item.quantity
        if item.is_shared:
            places = [int(p) for p in (item.shared_with or "").split(",") if p.strip().isdigit()]
            targets = [p for p in places if 1 <= p <= n] or list(range(1, n + 1))
        elif item.added_by_name in names:
            targets = [names.index(item.added_by_name) + 1]
        else:
            # Pas d'auteur connu (commande d'avant ce chantier, ou identité
            # perdue depuis) : reparti par défaut sur toute la table, jamais
            # oublié dans le calcul.
            targets = list(range(1, n + 1))
        part = line_total / len(targets)
        for p in targets:
            totals[p - 1] += part
    shares: dict[str, float] = {}
    for name, total in zip(names, totals):
        shares[name] = shares.get(name, 0.0) + total
    return shares


def compute_payable_amount(
    order: Order,
    names: list[str],
    payer_name: str,
    already_paid_names: set[str],
    mode: SplitMode = DEFAULT_SPLIT_MODE,
) -> float:
    """
    Montant à faire payer à `payer_name` maintenant. Le DERNIER convive
    encore non réglé absorbe l'arrondi — il paie exactement ce qu'il reste
    (`order.amount_remaining`), jamais sa part théorique : sans ça, la somme
    des paiements individuels pourrait ne jamais retomber pile sur le total
    (centimes perdus à l'arrondi de chaque part). Ce filet reste valable même
    si `mode` change entre deux paiements d'une même commande (quelqu'un
    bascule "équitable" après qu'un premier convive a déjà payé en "par
    plat") : la somme collectée retombe toujours sur le total, seule la
    répartition théorique entre convives non encore payés en tient compte.

    `payer_name` absent du roster (identité perdue, ou convive ajouté après
    coup) : ajouté à la volée pour ce calcul, plutôt que de lui facturer 0 —
    sans ça, un roster périmé laisserait quelqu'un payer sa part gratuitement.
    """
    names = list(names)
    if payer_name not in names:
        names.append(payer_name)
    remaining_names = [n for n in names if n not in already_paid_names]
    if len(remaining_names) <= 1:
        return round(order.amount_remaining, 2)
    shares = compute_shares(order, names, mode)
    return round(shares.get(payer_name, 0.0), 2)
