from app.core.etat_partage import magasin
from app.modules.orders.split import DEFAULT_SPLIT_MODE, SplitMode

VALID_MODES: tuple[SplitMode, ...] = ("items", "equal")


class TableSplitModeStore:
    """
    Mode de répartition de l'addition choisi par la table (« par plat » ou
    « équitable ») — par table, même principe que
    `tables/roster.py::TableRosterStore` et `orders/table_cart.py::TableCartStore`,
    stocké dans `core/etat_partage.py::magasin` (P2.1).

    À la différence du roster (« purement déclaratif, jamais lu pour une
    règle métier »), CE choix est lu par `orders/split.py::compute_payable_amount`
    au moment de facturer chaque convive (décision Wassim du 2026-09-10) :
    perdre cette mémoire au redémarrage du serveur fait retomber le calcul sur
    le mode par défaut ("par plat"), jamais sur un montant incohérent — le
    filet d'arrondi de `compute_payable_amount` (le dernier convive paie
    exactement ce qu'il reste) absorbe la différence, comme il absorbe déjà
    un roster qui change en cours de paiement.
    """

    CHAMP = "mode"

    @staticmethod
    def _cle(table_id: int) -> str:
        return f"repartition:{table_id}"

    def get(self, table_id: int) -> SplitMode:
        stocke = magasin.lire(self._cle(table_id)).get(self.CHAMP)
        return stocke if stocke in VALID_MODES else DEFAULT_SPLIT_MODE  # type: ignore[return-value]

    def set_mode(self, table_id: int, mode: str) -> None:
        if mode in VALID_MODES:
            magasin.ecrire(self._cle(table_id), self.CHAMP, mode)

    def clear(self, table_id: int) -> None:
        magasin.vider(self._cle(table_id))


table_split_mode_store = TableSplitModeStore()


def split_mode_message(table_id: int) -> dict:
    return {"event": "split_mode.updated", "mode": table_split_mode_store.get(table_id)}
