from dataclasses import dataclass
from uuid import uuid4

# Même borne que l'ancien `party.py` qu'il remplace : au-delà, c'est une
# saisie absurde (mauvais bouton, script) plutôt qu'une vraie tablée.
MAX_ROSTER_SIZE = 20


@dataclass
class RosterEntry:
    key: str
    name: str


class TableRosterStore:
    """
    Qui commande à une table, et sous quel prénom — même principe que
    `orders/table_cart.py::TableCartStore` : en mémoire, par table, purement
    déclaratif (n'affecte ni le prix ni le paiement).

    Remplace l'ancien `party.py` (nombre de convives + prénoms positionnels,
    déclarés d'un coup par un seul appareil). Ici chaque appareil annonce son
    propre prénom sous sa propre clé, sans jamais écraser celui des autres —
    l'ancien `party.set` remplaçait toute la liste à chaque appel, ce qui
    aurait fait perdre le prénom d'un convive si un second avait répondu au
    même instant. Un dict Python garde l'ordre d'insertion : la liste
    diffusée (`roster_message`) reste donc dans l'ordre où chacun a rejoint,
    comme les anciennes places 1..N.
    """

    def __init__(self) -> None:
        self._rosters: dict[int, dict[str, str]] = {}

    def snapshot(self, table_id: int) -> list[RosterEntry]:
        return [RosterEntry(key=key, name=name) for key, name in self._rosters.get(table_id, {}).items()]

    def set_name(self, table_id: int, device_key: str, name: str) -> None:
        roster = self._rosters.setdefault(table_id, {})
        # Une reconnexion (rafraîchissement de page) réutilise la même clé
        # déjà connue : ne compte pas comme une nouvelle place, donc n'entre
        # pas dans la borne ci-dessous.
        if device_key not in roster and len(roster) >= MAX_ROSTER_SIZE:
            return
        cleaned = name.strip()[:30]
        # Prénom laissé vide (modale passée) : "PersoN", N = la place que ce
        # téléphone occupe (avant son propre ajout, donc 1 pour le premier).
        roster[device_key] = cleaned or f"Perso{len(roster) + 1}"

    def add_guest(self, table_id: int, name: str) -> None:
        """Convive qui ne scanne pas — ajouté par un autre appareil de la
        table, sans clé d'appareil associée : il n'apparaîtra jamais comme
        auteur d'un plat, seulement dans la liste et la répartition."""
        roster = self._rosters.setdefault(table_id, {})
        if len(roster) >= MAX_ROSTER_SIZE:
            return
        cleaned = name.strip()[:30]
        roster[f"guest:{uuid4()}"] = cleaned or f"Perso{len(roster) + 1}"

    def clear(self, table_id: int) -> None:
        self._rosters.pop(table_id, None)


table_roster_store = TableRosterStore()


def roster_message(table_id: int) -> dict:
    people = table_roster_store.snapshot(table_id)
    return {"event": "roster.updated", "people": [{"key": p.key, "name": p.name} for p in people]}
