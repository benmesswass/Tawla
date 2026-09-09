"""
Répartition de l'addition par personne (identité de table, ROADMAP.md
§Override, extension paiement par personne) — port côté serveur du
calculateur indicatif `SplitBill.tsx` (mode "par plat", son mode par défaut).

Jusqu'ici purement déclaratif : `OrderItem.is_shared`/`shared_with`/
`added_by_name` ne servaient qu'à préremplir un affichage, jamais lus pour
une règle métier. Le paiement par personne en fait maintenant la source du
montant réellement facturé à chacun — le serveur ne fait plus confiance à un
montant fourni par le client, il le recalcule lui-même à partir de ces mêmes
données et du roster courant de la table, exactement comme il refige déjà
les prix à la création de la commande (voir `_build_order_items`).
"""
from app.modules.orders.models import Order


def compute_shares(order: Order, names: list[str]) -> dict[str, float]:
    """
    `names` : le roster de la table, dans l'ordre où chacun l'a rejointe
    (voir `tables/roster.py::TableRosterStore.snapshot`) — position 1..N,
    même convention que `OrderItem.shared_with`. Renvoie {prénom: montant dû},
    une entrée par nom (des prénoms en double fusionnent leur montant sous la
    même clé — cas rare et purement cosmétique, déjà accepté côté
    `added_by_name`/`SplitBill.tsx`).
    """
    n = len(names)
    if n == 0:
        return {}
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
    order: Order, names: list[str], payer_name: str, already_paid_names: set[str]
) -> float:
    """
    Montant à faire payer à `payer_name` maintenant. Le DERNIER convive
    encore non réglé absorbe l'arrondi — il paie exactement ce qu'il reste
    (`order.amount_remaining`), jamais sa part théorique : sans ça, la somme
    des paiements individuels pourrait ne jamais retomber pile sur le total
    (centimes perdus à l'arrondi de chaque part).

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
    shares = compute_shares(order, names)
    return round(shares.get(payer_name, 0.0), 2)
