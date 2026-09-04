# Tawla — Domaine

Plateforme de commande via QR code pour restaurants/cafés, en Tunisie et
bientôt en France (voir `MARCHE_FRANCE.md`). Ce glossaire capture le
vocabulaire du domaine tel qu'il existe dans le code aujourd'hui — pas les
intentions non encore codées.

## Cycle de vie de la commande

**Commande (Order)** :
Ce qu'un client compose sur son téléphone après avoir scanné le QR de sa
table, jusqu'à ce qu'elle soit servie ou annulée. Identifiée pour le client
par un `public_token` opaque (jamais par son id numérique) — aucun compte
client n'existe, le token est le seul lien entre un navigateur et sa commande.
_Avoid_: Ticket, Ticket de caisse

**Statut de commande (OrderStatus)** :
L'état d'avancement d'une commande, avec des transitions explicitement
contrôlées plutôt qu'un champ libre : `PENDING_CONFIRMATION` (envoyée par le
client, en attente d'un serveur) → `CONFIRMED` (un serveur a confirmé avec la
table) → `SENT_TO_KITCHEN` (visible à l'écran cuisine) → `IN_PREPARATION` →
`READY` → `SERVED`. `CANCELLED` n'est atteignable que depuis les trois
premiers états, et devient impossible une fois la commande payée.

**Modification de commande** :
Deux fenêtres distinctes, jamais une troisième voie. Tant que la commande est
`PENDING_CONFIRMATION`, le client la modifie lui-même, sans validation
(`PUT /orders/{id}/items`). Passé ce point (`CONFIRMED`/`SENT_TO_KITCHEN`/
`IN_PREPARATION`), il envoie une **Demande de modification
(OrderModificationRequest)** — le service compare le panier envoyé aux
`OrderItem` actuels et n'en garde que les écarts, une **Ligne de demande
(OrderModificationLine)** par article dont la quantité change
(`previous_quantity` à 0 pour un ajout, `requested_quantity` à 0 pour un
retrait complet). Le serveur répond ligne par ligne, jamais tout ou rien : une
ligne acceptée s'applique à la vraie commande, une ligne refusée n'y touche
pas. Une seule demande non résolue à la fois par commande. Un ajout refusé
peut repartir comme commande séparée (flux normal de création) ; un retrait
refusé n'a aucune suite, l'article reste tel quel.
_Avoid_: Édition de commande (trop large — ne dit pas laquelle des deux
fenêtres), Avenant

**Prise en charge (Claim)** :
L'action par laquelle un serveur retire une commande du pool partagé (visible
de tous les serveurs) pour se l'attribuer. Se produit explicitement (bouton
dédié) ou implicitement à la confirmation si personne ne l'a encore prise.
Base des statistiques par serveur.

**Commande perdue (Lost order)** :
Une commande annulée — définition unique (`stats/service.py::cancelled_orders`),
partagée par le tableau de bord, la page de preuve et l'agrégat
multi-restaurants. La métrique centrale de l'argument de vente du produit.
Jusqu'au 2026-08-28, une commande restée `PENDING_CONFIRMATION` au-delà de dix
minutes comptait aussi comme perdue ; Wassim a tranché que ça confondait une
vente lente avec une vente ratée — elle peut toujours être prise en charge, ce
qu'une annulation ne permet plus. Ce délai reste mesuré, sous un autre nom :
voir **Temps d'attente** et **Charge active** ci-dessous.

**Temps d'attente (`TimingStats.avg_wait_confirmation_seconds`)** :
Délai moyen entre la validation du panier par le client et sa prise en charge
par un serveur, sur la journée affichée. Chiffre de tête du tableau de bord
depuis le 2026-08-28, à la place de « Commandes perdues ».

**Charge active (`StaffActiveLoad`)** :
Nombre de tables qu'un serveur a actuellement sur les bras — commandes prises
en charge, pas encore servies ni annulées, évalué à l'instant présent plutôt
que sur la journée affichée (comme `active_orders_count`). Distinct de
`StaffPerformance.orders_taken`, qui cumule la journée entière.

**Ligne de commande (OrderItem)** :
Un article commandé, avec son nom et son prix unitaire **figés** au moment de
la commande — jamais recalculés depuis la carte si le restaurant change ses
prix après coup.

**Option choisie (OrderItemOption)** :
Un choix fait dans un groupe d'options d'un article (ex. cuisson, sauce) —
nom et supplément de prix figés au moment de la commande, comme pour une
ligne de commande.

## Multi-tenant

**Restaurant** :
Un établissement client de Tawla (resto, café) — le tenant du système :
toute donnée métier lui est rattachée. Un seul enregistrement en pratique
aujourd'hui, mais le modèle est multi-tenant depuis l'origine (voir
ADR-0002).
_Avoid_: Tenant, Établissement (utilisé dans la prose, le terme de code fait
foi), Client (voir ci-dessous — sens différent)

**Client** :
Le convive attablé qui commande depuis son téléphone. N'a aucun compte :
identifié uniquement, et temporairement, par le token de sa commande.
_Avoid_: Utilisateur, Convive (réservé au partage d'une commande entre
plusieurs personnes attablées ensemble)

**Table** :
Un emplacement physique du restaurant, identifié par un token QR opaque et
non-devinable (jamais un id séquentiel). Porte un libellé, une zone
facultative, une position sur le plan de salle, une forme et un nombre de
couverts.

**Palier d'abonnement (SubscriptionTier)** :
Le niveau payant d'un Restaurant — `ESSENTIEL` / `PRO` / `BUSINESS`, chacun
incluant les fonctionnalités du précédent. Distinct du **palier effectif**,
qui retombe à `ESSENTIEL` si la période payée a expiré sans renouvellement —
jamais lu directement depuis la colonne pour du gating.

## Personnel

**Staff** :
Un compte membre de l'équipe d'un Restaurant, avec un rôle : serveur,
manager, ou cuisine. Désactivé plutôt que supprimé au départ d'un salarié,
pour préserver l'historique des commandes qu'il a prises en charge.

## Marché — ce qui diverge déjà entre la Tunisie et la France

**Marché (Market)** :
Un objet de configuration unique par pays (`tn` | `fr`) — devise, fuseau
horaire, langues, prix des paliers, taux de TVA, fournisseur de paiement —
chargé une fois au démarrage du processus. Un déploiement sert un seul
marché, jamais les deux (voir ADR-0003).

**Journée de service (Service day)** :
La période de service d'un restaurant, qui commence à une heure fixe dans le
fuseau du marché (5h du matin aujourd'hui) plutôt qu'à minuit calendaire —
pour ne pas couper un service de nuit en cours, et pour que les écrans de
service et les statistiques bornent leurs journées de la même façon.

**Taux de TVA** :
Les taux de TVA applicables dans un marché, par catégorie (en France : sur
place, à emporter, alcool). Présents dans la configuration du marché
français ; sans objet en Tunisie.

**Seuil de note obligatoire** :
Le montant TTC au-delà duquel une note détaillée devient légalement
obligatoire pour un marché (25 € en France ; sans objet en Tunisie).

**Fournisseur de paiement (PaymentProvider)** :
L'interface qu'un marché doit satisfaire pour encaisser une commande —
initier un paiement, le consulter, savoir s'il est disponible, convertir un
montant dans sa plus petite unité. `KonnectProvider` (Tunisie) est le seul
fournisseur réel aujourd'hui ; `NullProvider` (aucun encaissement) est le
mode courant du marché français tant qu'un fournisseur français n'existe pas.
_Avoid_: Passerelle de paiement (utilisé dans la prose pour Konnect
spécifiquement, pas pour l'abstraction)
