# Mode de répartition de l'addition (« par plat » / « équitable ») : état en mémoire, lu au paiement

Chantier hiérarchie du paiement (Wassim, 2026-09-10) : le widget `SplitBill.tsx`
proposait un mode « Équitable » purement indicatif — son résultat n'alimentait
ni le roster ni le montant réellement facturé (`orders/split.py::compute_shares`
restait toujours en mode « par plat »). Demande explicite en revoyant le
mockup de la nouvelle hiérarchie : que ce mode devienne un vrai choix, pas un
second calcul à côté de celui qui facture.

Décision : le mode choisi vit **en mémoire côté backend**, indexé par
`table_id` (`app/modules/tables/split_mode.py::TableSplitModeStore`), même
principe que le roster et le panier partagé de table (`roster.py`,
`table_cart.py`, ADR 0005) — pas de nouvelle colonne, pas de migration. Diffusé
sur le canal WebSocket de table déjà existant (`identity.set`/`identity.add_guest`
en sont le précédent direct) via une nouvelle action `split_mode.set` et
l'événement `split_mode.updated`. Lu par `orders/service.py::_get_payable_share`
au moment de calculer ce que chaque convive doit payer
(`orders/split.py::compute_payable_amount`, paramètre `mode`) — donc, à la
différence du roster, cette valeur influence bien le montant débité.

**Considered options** : persister le mode sur `Order` (migration Alembic)
aurait survécu à un redémarrage backend, mais l'incohérence que ça évite est
déjà couverte par le filet existant de `compute_payable_amount` — le dernier
convive non réglé paie toujours exactement `amount_remaining`, jamais sa part
théorique, donc la somme perçue retombe sur le total quel que soit le mode en
mémoire au moment de chaque paiement (le roster lui-même peut déjà changer en
cours de paiement sans casser cette garantie). Perdre le mode au redémarrage
revient au pire à retomber sur le mode par défaut (« par plat ») pour les
convives pas encore payés — jamais une facturation incohérente.

**Consequence** : ce choix disparaît à tout redémarrage/déploiement backend et
à la libération de la table (`tables/service.py::release_table`), comme le
roster et le panier partagé. Si le projet passe un jour à plusieurs instances
backend, à revoir avec le reste de l'état en mémoire (ADR 0005).
