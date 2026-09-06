from dataclasses import dataclass, field

# Bornes larges mais réelles : au-delà, c'est une saisie absurde (mauvais
# bouton, script) plutôt qu'une vraie tablée — pas de raison de la refuser
# avec une erreur, juste de ne pas la laisser gonfler l'état en mémoire.
MIN_PARTY_SIZE = 1
MAX_PARTY_SIZE = 20


@dataclass
class TableParty:
    size: int
    # Longueur toujours égale à `size` — une case vide (`None`) veut dire
    # "prénom non donné", affiché comme "Personne N" côté client, jamais une
    # erreur : le prénom est facultatif par construction (ROADMAP.md
    # §Override — Panier synchronisé multi-appareils).
    names: list[str | None] = field(default_factory=list)


class TablePartyStore:
    """
    Combien de convives à une table, et leurs prénoms facultatifs — même
    principe que `orders/table_cart.py::TableCartStore` : en mémoire, par
    table, purement déclaratif (n'affecte ni le prix ni le paiement). Sert
    uniquement à l'affichage (panier partagé, calculateur d'addition
    `SplitBill`), jamais à une règle métier.
    """

    def __init__(self) -> None:
        self._parties: dict[int, TableParty] = {}

    def get(self, table_id: int) -> TableParty | None:
        return self._parties.get(table_id)

    def set(self, table_id: int, size: int, names: list[str | None]) -> TableParty:
        size = max(MIN_PARTY_SIZE, min(MAX_PARTY_SIZE, size))
        # Tronqué/complété à `size` plutôt que rejeté : un nom en trop après
        # avoir baissé le nombre de couverts ne doit pas planter la mise à
        # jour, juste être oublié.
        trimmed = [((n or "").strip() or None) for n in names[:size]]
        trimmed += [None] * (size - len(trimmed))
        party = TableParty(size=size, names=trimmed)
        self._parties[table_id] = party
        return party

    def clear(self, table_id: int) -> None:
        self._parties.pop(table_id, None)


table_party_store = TablePartyStore()


def party_message(table_id: int) -> dict:
    party = table_party_store.get(table_id)
    if not party:
        return {"event": "party.updated", "size": None, "names": []}
    return {"event": "party.updated", "size": party.size, "names": party.names}
