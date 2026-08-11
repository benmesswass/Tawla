# Tawla — Roadmap

Fichier unique de pilotage du projet. Une tâche cochée `[x]` doit mentionner la PR qui l'a livrée. Prendre la première tâche non cochée en partant du haut, dans l'ordre des phases.

## Vision produit

Un client s'assoit à table, scanne le QR code, commande depuis un menu digital et valide son panier. La commande part vers un écran partagé consulté par tous les serveurs du service (les commandes de toutes les tables s'y empilent). Un serveur la prend en charge, se déplace à la table pour confirmer avec les clients, puis valide sur l'app — ce qui envoie la commande en cuisine. Le manager suit en temps réel l'activité globale : temps passé à chaque étape, charge de travail par serveur (base pour les primes de rendement). Le paiement se fait depuis l'app : carte avec pourboire optionnel, ou demande d'addition pour payer cash à table.

North star : un service fluide en salle (zéro commande perdue ou oubliée) et une visibilité complète pour le manager sur la performance de l'équipe.

**Historique** : une première passe (audit QA/PO/Design du 2026-08-10, commit `e185995`) a livré directement le cœur du produit — flux de commande complet, temps réel WebSocket, isolation multi-tenant testée — avant même que cette roadmap ne soit formalisée en phases. Le détail de cet audit reste consultable dans l'historique git (`prototype/ROADMAP.md` avant sa fusion ici). Cette roadmap reflète l'état réel du code, pas l'ordre chronologique dans lequel il a été écrit.

---

## Phase 0 — Fondations

- [x] Choix de la stack technique : FastAPI + SQLAlchemy/PostgreSQL (backend) + Next.js/Tailwind (frontend), WebSocket natif pour le temps réel (audit du 2026-08-10)
- [x] CI de base (lint, typecheck, tests backend + frontend) (PR #2)
- [x] Modèle de données initial : `Restaurant` (tenants), `Table`, `MenuItem`, `Order`/`OrderItem`, `Staff` (rôles waiter/kitchen/manager) — multi-tenant-ready dès le départ (audit du 2026-08-10)
- [x] Auth staff (serveurs, cuisine, manager) — JWT + rôles, le client lui n'a pas de compte (PR #2)
- [x] Génération des QR codes par table (token opaque non-devinable, script `generate_table_qr.py`) (audit du 2026-08-10)

## Phase 1 — MVP commande client

- [x] Menu digital consultable depuis le QR (catégories, plats, prix, photo, description) (audit du 2026-08-10)
- [x] Panier côté client + validation de la commande, note libre par article (audit du 2026-08-10)
- [x] Envoi de la commande vers le pool partagé des serveurs (broadcast WebSocket `order.pending_confirmation`) (audit du 2026-08-10)
- [x] État de la commande visible côté client, temps réel + persistant au rafraîchissement (audit du 2026-08-10)

## Phase 2 — Flux serveur & cuisine

- [x] Écran serveurs : pool de toutes les commandes en attente (toutes tables) (audit du 2026-08-10), prise en charge (« claim ») individuelle par un serveur (PR #2) — base des stats par serveur de la Phase 3
- [x] Confirmation à table : le serveur valide la commande sur l'app après l'avoir vérifiée avec les clients (audit du 2026-08-10)
- [x] Transmission automatique à la cuisine dès la confirmation (audit du 2026-08-10)
- [x] Écran cuisine : file d'attente des commandes confirmées, statuts (reçue / en préparation / prête) (audit du 2026-08-10)
- [x] Statut final « sortie vers le client » (servie), déclenché par le serveur (audit du 2026-08-10)

## Phase 3 — Dashboard manager

- [x] Vue temps réel de toutes les commandes en cours, par statut (PR #3)
- [x] Temps moyen passé à chaque étape (attente de confirmation, confirmée → envoyée en cuisine, cuisine → sortie) (PR #3)
- [x] Nombre de commandes prises en charge par serveur et par jour (base de calcul pour les primes de rendement) (PR #3)
- [x] Statistiques plats les plus vendus, répartition par heure (identification des pics de charge) (PR #3)

## Phase 4 — Paiement

- [x] Paiement carte depuis l'app, avec pourboire optionnel — Konnect ciblé, mode simulé pour l'instant (arbitrage Wassim), couvre le prix total (PR #4)
- [x] Demande de paiement cash depuis l'app (génère l'addition, prévient le serveur concerné) (PR #4)
- [x] Partage de l'addition (split bill) : par plat ou équitable — calculateur indicatif, le paiement reste unique pour la table (PR #5)

## Phase 5 — Spécificités culture tunisienne

- [x] Mode Ramadan : menu ftour dédié, pré-commande calée sur l'heure exacte de la rupture du jeûne (variable chaque jour), anticipation du pic de charge en cuisine (PR #6)
- [x] Commande groupée à table : plats marqués « à partager » (salades, mechouia...) visibles côté cuisine/serveur et pré-signalés dans le split bill de la Phase 4 — scope réduit délibérément : pas de panier temps réel synchronisé entre plusieurs téléphones (ambiguïté produit signalée, arbitrage retenu : un seul appareil compose/valide toujours la commande, cf. `CLAUDE.md` philosophie KISS/YAGNI) (PR #7)
- [x] Interface bilingue français / arabe (derja tunisienne), RTL natif — scope : parcours client (`/menu/[qrToken]` + split bill), écrans staff/cuisine/manager restent en français (back-office interne) ; anglais/italien non traités (marqués « option » dans la roadmap, à faire si un pilote resto touristique le demande) (PR #8)
- [x] Niveau de piment affiché par plat + mentions allergènes et halal — saisi par le manager dans le dashboard (piment 0-3, allergènes en texte libre, case halal — défaut `True`, la quasi-totalité des restos tunisiens l'étant), affiché au client (fr/ar) et sur le menu (PR #9)
- [x] Bouton « appeler le serveur », indépendant du passage de commande — nouveau modèle `WaiterCall` persisté (survit à une reconnexion, même logique que les demandes de paiement cash), diffusé en temps réel sur le canal "staff" existant, résolu par un serveur ou le manager ; bouton client avec cooldown 90s anti-spam, traduit fr/ar (PR #10)
- [x] Gestion de la rupture de stock en temps réel (un plat en rupture est désactivé instantanément côté client) — nouveau canal WebSocket public `/ws/menu/{restaurant_id}`, diffusé depuis la bascule manager déjà existante ; le client voit le plat disparaître du menu et être retiré automatiquement de son panier sans recharger la page (PR #11)
- [x] Mode café simplifié : commande de boissons seules, sans structure entrée/plat/dessert — toggle manager (`Restaurant.cafe_mode_enabled`, même pattern que le mode Ramadan), le menu client s'affiche alors en liste unique sans en-têtes de catégorie (PR #12)
- [x] PWA offline-first : file d'attente locale si la connexion mobile est instable, envoi différé automatique — manifest.ts + icônes + service worker minimal (réseau d'abord, secours cache) pour l'installabilité ; côté commande, un échec réseau (pas une erreur API) met la commande de côté en localStorage et la renvoie automatiquement à l'événement `online` ou au prochain chargement de page, avec un bouton « réessayer maintenant » (PR #13)
- [x] Carte de fidélité digitale (ex. Nème café/plat offert, réduction anniversaire) — identification par numéro de téléphone (arbitrage Wassim : pas de compte client dans l'app, en cohérence avec l'architecture anonyme existante), suivi côté serveur par restaurant (`LoyaltyMember`, seuil 10 commandes payées). Le compteur n'incrémente qu'au paiement confirmé (carte ou cash), jamais à la création de commande. Récompense = action manuelle du serveur (punch-card, jamais un rabais auto appliqué au prix — domaine paiement volontairement non touché), redemption possible via le badge sur une demande de paiement cash ou via une recherche manuelle par téléphone côté staff. Bandeau anniversaire si la date de naissance (facultative) correspond au jour même (PR #14)

## Phase 6 — Croissance / opérationnel

- [x] Multi-restaurants : le schéma est déjà multi-tenant-ready (`restaurant_id` partout, isolation testée — audit du 2026-08-10), reste l'auth/onboarding multi-établissement côté manager — nouvel endpoint public `POST /api/v1/auth/register` (self-service, pas de vérification e-mail, cohérent avec l'absence de service payant obligatoire) : crée le restaurant + son premier compte manager en une fois, slug dérivé automatiquement du nom (dédupliqué en cas de collision), connexion immédiate. Page `/signup` côté frontend, reliée depuis `/login`. L'ancien endpoint `POST /api/v1/restaurants` (non authentifié, jamais appelé par le frontend, utilisé uniquement comme fixture par la suite de tests) reste inchangé — le modifier aurait cassé ~9 fichiers de tests sans bénéfice pour cette tâche (PR #15)
- [ ] Notifications SMS/push au client quand sa commande est prête
- [ ] Gestion des zones de salle (intérieur / terrasse / plage) pour les établissements concernés (ex. Hammamet, Sousse)
- [ ] Export des statistiques (manager)

## Phase 7 — Idées à trancher plus tard (🧑 arbitrage produit de Wassim)

- [ ] Modèle de paiement : frais de service uniquement vs vrai paiement intégral en ligne (implication juridique/comptable à valider)
- [ ] Programme de fidélité : par établissement vs mutualisé entre plusieurs restaurants partenaires
- [ ] Gestion des grands groupes / événements (mariages, réservations de salle)
- [ ] Nom de marque définitif et identité visuelle (le nom de repo « Tawla » est provisoire)
- [ ] Montée de version majeure Next.js (14 → 15/16) : breaking change réel, décision produit à part (signalé lors de l'audit du 2026-08-10)
- [ ] Vraie intégration imprimante cuisine (au-delà du filet de secours navigateur déjà en place)
