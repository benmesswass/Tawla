# Montant de paiement choisi par le convive : une proposition, plafonnée par le serveur

Demande de Wassim, 2026-09-11. Les deux modes de répartition (« par plat » /
« équitable », ADR 0006) répondaient à la place du convive à la seule question
qui compte au moment de payer : **combien je paie ?** Deux cas réels n'avaient
aucun chemin — régler pour toute la table (l'invitation, le patron qui paie
pour ses convives) et payer un montant exact convenu de vive voix.

Décision : `PayShareRequest.amount` (facultatif) porte le montant **choisi** par
le convive, sur les trois moyens de paiement. Le serveur le **plafonne à ce qui
reste dû** (`orders/service.py::_get_payable_share`) puis le fige sur la part
comme n'importe quel autre montant.

Ça renverse un invariant écrit noir sur blanc dans `PayShareRequest` (« le
montant réellement facturé n'est JAMAIS lu ici ») — d'où cet ADR plutôt qu'un
commentaire. Ce qui est conservé de cet invariant : **le client ne fixe jamais
ce qui est débité**, il propose une valeur que le serveur borne. Ce qui est
abandonné : « un client ne peut jamais se facturer moins que sa part réelle ».

**Pourquoi le plafond seul suffit.** Payer *plus* que l'addition obligerait à
rembourser, ce que le produit ne sait pas faire : c'est la seule borne dure.
Payer *moins* est le but même de la fonctionnalité, et n'ouvre aucun trou :
chaque part encaissée diminue `amount_remaining`, la commande ne passe `PAID`
que lorsqu'il tombe à zéro (`_after_share_paid`), et le reliquat reste affiché à
la table comme en salle. Un convive qui règle 1 DT sur 40 ne « vole » rien — il
laisse 39 DT visibles sur l'écran du serveur.

**Considered options.** Interdire tout montant inférieur à la part calculée
aurait gardé l'invariant intact, mais retirait le cas « je paie un montant
exact », c'est-à-dire la demande. Enregistrer le choix côté table (comme le mode
de répartition, ADR 0006) aurait imposé le choix d'un convive à tous les autres
appareils : ce montant est personnel, il ne quitte pas l'appareil qui paie et
n'est diffusé à personne.

**Conséquence.** Une commande peut rester `PARTIALLY_PAID` plus longtemps, avec
plus de parts que de convives. Rien à migrer : `OrderPayment.amount` portait
déjà un montant par part, `amount_remaining` était déjà la somme à couvrir.
