# Panier de table partagé : état en mémoire, serveur source de vérité

Plusieurs téléphones qui scannent le même QR de table doivent pouvoir
composer un panier ensemble et valider une seule commande — jusqu'ici
tranché dans l'autre sens, deux fois (`ROADMAP_ARCHIVE.md:73`, PR #7, Phase 4 ;
invariant encore présent dans `orders/models.py::OrderItem.is_shared`).
Override produit de Wassim (2026-09-06, `ROADMAP.md` §Override — Panier
synchronisé multi-appareils), sans déclencheur terrain : le chantier documente
son architecture au moment où il se construit, pas après coup.

Décision : le panier partagé vit **en mémoire côté backend**, indexé par
`table_id`, jamais en base — pas de nouvelle table SQL, pas de migration. Le
serveur est la source de vérité ; les navigateurs affichent l'état qu'il
diffuse sur le canal WebSocket par table déjà existant
(`/ws/table/{restaurant_id}/{qr_token}`, `notifications/manager.py::table_channel`,
jusqu'ici réservé à l'appel serveur) et n'importe quel appareil connecté peut
valider — la commande créée porte alors l'état tenu par le serveur, jamais un
état local potentiellement périmé. Aucun nouveau mécanisme d'appariement
entre appareils : la possession du `qr_token` reste la seule frontière de
sécurité pour « être à cette table », comme partout ailleurs dans le parcours
client. Si la connexion WebSocket tombe, l'appareil revient au panier local
actuel — pas de régression pour un client seul à sa table.

**Considered options** : persister le panier partagé en base (nouvelle table
`TableCart`/`TableCartItem`) aurait survécu à un redémarrage du backend et
suivi la discipline « toute donnée = migration » du reste du projet — mais un
panier avant validation est un état transitoire et à faible enjeu (perte au
pire = re-saisie, déjà le cas aujourd'hui si un onglet crashe avant de
valider), et le backend est déjà mono-instance avec un état en mémoire
équivalent pour le gestionnaire WebSocket et le limiteur de débit
(`ROADMAP.md`, Sous condition, ligne « Plusieurs instances backend »). Ajouter
une table pour un état qui n'a jamais besoin de survivre à un redémarrage
aurait été de la complexité sans bénéfice réel.

**Consequence** : ce panier partagé disparaît à tout redémarrage ou
déploiement backend — attendu, pas un bug. Si le projet passe un jour à
plusieurs instances backend (déclencheur déjà posé dans `ROADMAP.md`), cet
état en mémoire devra être revu en même temps que le gestionnaire WebSocket et
le limiteur de débit, pas isolément.
