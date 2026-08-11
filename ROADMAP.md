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
- [x] Notifications SMS/push au client quand sa commande est prête — scope réduit délibérément au **push navigateur** (Web Push standard, gratuit, s'appuie sur le service worker déjà posé par la PWA) : l'envoi de SMS exige un service tiers payant (aucun n'existe gratuitement), hors de portée du reste du projet. Opt-in explicite sur l'écran de suivi client (`POST /orders/{id}/push-subscription`), clé VAPID exposée via `GET /notifications/vapid-public-key` (vide = fonctionnalité désactivée, aucune casse). Envoi best-effort à la transition "prête" (`orders/service.py::transition_status`) — une erreur d'envoi (clé absente, abonnement expiré) ne bloque jamais le passage de statut côté cuisine (PR #16)
- [x] Gestion des zones de salle (intérieur / terrasse / plage) pour les établissements concernés (ex. Hammamet, Sousse) — `Table.zone` en texte libre (comme `MenuItem.category`), pas un enum figé : tous les établissements n'ont pas les mêmes zones. Section « Tables & zones de salle » ajoutée au dashboard manager (liste + édition + création de table), qui n'existait sous aucune forme avant cette PR — sans elle, un manager onboardé via `/signup` (PR #15) n'aurait eu aucun moyen d'assigner de zone, ni même de créer une table, sans passer par Swagger (PR #17)
- [x] Export des statistiques (manager) — bouton « Exporter en CSV » sur `/dashboard/stats`, généré **côté client** (aucun nouvel endpoint : reformate en CSV les données déjà chargées par `GET /stats/dashboard/{id}` pour la journée affichée — commandes en cours, temps moyen par étape, performance serveurs, plats les plus vendus, heures de pointe), téléchargement via Blob + lien `download` (PR #18)

## Phase 7 — Idées à trancher plus tard (🧑 arbitrage produit de Wassim)

- [ ] Modèle de paiement : frais de service uniquement vs vrai paiement intégral en ligne (implication juridique/comptable à valider)
- [ ] Programme de fidélité : par établissement vs mutualisé entre plusieurs restaurants partenaires
- [ ] Gestion des grands groupes / événements (mariages, réservations de salle)
- [x] Nom de marque définitif — confirmé par Wassim le 2026-08-11 : **Tawla** reste le nom définitif. L'identité visuelle (logo, palette, typographie) est tracée en Phase 8.1, désormais débloquée
- [ ] Montée de version majeure Next.js (14 → 15/16) : breaking change réel, décision produit à part (signalé lors de l'audit du 2026-08-10)
- [ ] Vraie intégration imprimante cuisine (au-delà du filet de secours navigateur déjà en place)

## Phase 8 — Design & expérience

Ajoutée le 2026-08-11, à la suite de l'audit fonctionnel + design mené une fois les phases 0-6 complètes (18 PR mergées, 104 tests backend verts, aucune tâche non-bloquée restante). Rapport complet avec captures d'écran envoyé à Wassim en Artifact la même session. Constat : le fonctionnel est solide, le design reste au niveau prototype (aucune identité de marque, une seule couleur d'accent partout, zéro micro-interaction). Poids délibérément mis sur le design, à la demande explicite de Wassim ("trop simpliste", envie d'un rendu "attachant, pro, fun").

**8.1 — Identité de marque (fondation, bloque le reste de la phase)**
- [x] Nom de marque définitif — confirmé par Wassim le 2026-08-11 : **Tawla**
- [x] Logo + favicon + icônes PWA, lisibles de 32px à 512px — marque « Le Duo Encadré » (un seul cadre partagé en deux zones : lignes de commande + coche de validation, choisie par Wassim après plusieurs rondes d'options en Artifact) ; `favicon`/`pwa-icon-192`/`pwa-icon-512` régénérés, composants `TawlaMark`/`TawlaLogo` réutilisables (PR #21)
- [x] Palette de marque figée (primaire, secondaire, + couleurs sémantiques distinctes de la couleur d'action) en tokens CSS partagés client/staff — variables dans `frontend/app/globals.css` (`--harissa`, `--menthe`, `--laiton`, `--semoule`, `--encre`…) (PR #21)
- [x] Paire typographique (une police d'affichage avec du caractère + une police texte lisible en petit sur mobile) — Lalezar (affichage) + Hanken Grotesk (texte/UI) via `next/font/google`, `frontend/lib/fonts.ts` (PR #21)

Identité posée et appliquée à `/login` + `/signup` dans cette PR (captures avant/après dans la description de la PR). Le reste de l'app (dashboard, staff, cuisine, menu client) garde son style actuel — application progressive prévue en 8.2–8.5, un écran à la fois.

**8.2 — Système de design partagé**
- [x] Composants de base nommés (`Button`, `Card`, `Badge` de statut, `EmptyState`) pour remplacer les classes Tailwind dupliquées dans `dashboard/page.tsx`, `staff/page.tsx`, `kitchen/page.tsx` — `frontend/components/ui/`, chaque composant supportant un variant `dark` (écran cuisine resté volontairement sombre). Couleurs d'action et de statut consolidées sur la palette de marque (harissa = action, menthe = validation d'étape, ambre/sky/rose = alerte contextuelle), remplaçant la douzaine de teintes Tailwind ad hoc utilisées jusque-là. Corrige au passage un bug de config découvert pendant le test visuel : `tailwind.config.js` ne scannait que `./app/**/*`, jamais `./components/**/*` — les classes propres aux nouveaux composants (couleurs de marque en valeur arbitraire `bg-[var(--harissa)]`) n'étaient jamais générées, rendant les boutons invisibles (texte blanc sur fond transparent) (PR #22)
- [x] Iconographie cohérente pour remplacer les emoji dans les badges de statut et boutons d'action clés — 8 icônes SVG monochromes (`frontend/components/icons/`, `currentColor`, style trait cohérent) remplaçant 🌙/🍽️/🎁/🔔/☕/🌶️/🎂/📶 dans `dashboard`, `staff`, `kitchen`, le parcours client (`menu/[qrToken]`, `SplitBill`) et les dictionnaires fr/ar. Conservés volontairement : ✓/✕ (symboles monochromes déjà cohérents) et 🎉 (flourish festif, traité par la tâche dédiée « moment de célébration » ci-dessous plutôt qu'ici) ; les libellés de `<select><option>` (niveau de piment dans le dashboard) restent en texte brut — un `<option>` HTML ne peut pas afficher de composant icône (PR #23)
- [x] Skeletons de chargement — composant `Skeleton` (`frontend/components/ui/`, variant `dark` pour l'écran cuisine) remplaçant les écrans "Chargement…"/blancs sur `dashboard`, `staff`, `kitchen`, `dashboard/stats` et le menu client (PR #24)

**8.3 — Parcours client**
- [x] Moment de célébration à la validation de commande — `CelebrationOverlay` (confetti + coche animée, `frontend/components/`), déclenché uniquement sur une validation fraîche (pas sur une reprise de suivi après reload), auto-disparition après 1,8 s, `prefers-reduced-motion` respecté (PR #25)
- [x] Retour visuel à l'ajout au panier — animation de rebond sur le compteur de quantité + retour tactile (`active:scale-90`) sur le bouton "+" (PR #25)
- [x] Timeline de suivi redessinée — ligne de connexion verticale, étape courante mise en avant (anneau pulsant), étapes complétées cochées en menthe ; indication de délai ("généralement 10 à 20 minutes") affichée sous l'étape courante quand la commande est en cuisine/en préparation (PR #25)
- [x] Catégories de menu bilingues prédéfinies — `frontend/lib/menuCategories.ts` (liste fermée déjà proposée en `<select>` côté dashboard, traduction d'affichage uniquement, aucune migration de schéma) ; corrige le bug i18n relevé à l'audit : `MenuItem.category` s'affichait en français brut même en vue arabe (PR #26)
- [x] État vide du panier illustré — le vrai cas rencontré : un article du panier devient indisponible en temps réel (WS) et le panier se vide silencieusement sans aucune explication (bug UX découvert en implémentant cet item). `EmptyCartIllustration` + message explicite remplacent désormais ce silence (PR #25)

**8.4 — Dashboard manager**
- [ ] Vue liste compacte + édition en panneau (aujourd'hui : une carte-formulaire complète par plat/table, empilées — illisible sur mobile passé une poignée d'articles)
- [ ] Miniature photo dans la liste (`image_url` existe déjà en base, jamais utilisée côté dashboard)
- [ ] Recherche/filtre par catégorie
- [ ] Onglets (Menu / Tables & zones / Réglages) au lieu d'un défilement qui grandit sans fin

**8.5 — Écrans serveur & cuisine**
- [ ] Compteur du jour sur l'écran cuisine (l'état vide actuel est un écran noir sans aucune information)
- [ ] Distinction visuelle plus tranchée par statut côté serveur (à confirmer / prêtes à servir / demandes de paiement utilisent des teintes trop proches)
- [ ] Retour sonore optionnel à l'arrivée d'une commande en cuisine (activable par le manager)

**8.6 — Idées "fun" différenciantes** (après 8.1-8.2 : héritent d'une identité cohérente plutôt que d'être des gadgets isolés)
- [ ] Mini-fait culturel ou anecdote sur le plat pendant l'attente cuisine
- [ ] Carte de fidélité visuelle façon carte à tamponner (aujourd'hui : juste un texte "3 commandes, encore 7")
- [ ] Partage social du plat commandé (carte visuelle générée pour Instagram/WhatsApp Status — fort effet bouche-à-oreille pour le pilote)
