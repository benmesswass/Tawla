from app.modules.orders.split import DEFAULT_SPLIT_MODE, SplitMode

VALID_MODES: tuple[SplitMode, ...] = ("items", "equal")


class TableSplitModeStore:
    """
    Mode de répartition de l'addition choisi par la table (« par plat » ou
    « équitable ») — en mémoire, par table, même principe que
    `tables/roster.py::TableRosterStore` et `orders/table_cart.py::TableCartStore`.

    À la différence du roster (« purement déclaratif, jamais lu pour une
    règle métier »), CE choix est lu par `orders/split.py::compute_payable_amount`
    au moment de facturer chaque convive (décision Wassim du 2026-09-10) :
    perdre cette mémoire au redémarrage du serveur fait retomber le calcul sur
    le mode par défaut ("par plat"), jamais sur un montant incohérent — le
    filet d'arrondi de `compute_payable_amount` (le dernier convive paie
    exactement ce qu'il reste) absorbe la différence, comme il absorbe déjà
    un roster qui change en cours de paiement.
    """

    def __init__(self) -> None:
        self._modes: dict[int, SplitMode] = {}

    def get(self, table_id: int) -> SplitMode:
        return self._modes.get(table_id, DEFAULT_SPLIT_MODE)

    def set_mode(self, table_id: int, mode: str) -> None:
        if mode in VALID_MODES:
            self._modes[table_id] = mode  # type: ignore[assignment]

    def clear(self, table_id: int) -> None:
        self._modes.pop(table_id, None)


table_split_mode_store = TableSplitModeStore()


def split_mode_message(table_id: int) -> dict:
    return {"event": "split_mode.updated", "mode": table_split_mode_store.get(table_id)}
