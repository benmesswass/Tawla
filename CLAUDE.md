# Tawla — conventions du projet

## Identité git / GitHub (règle absolue)

Projet **personnel** de Wassim. Tout commit, push et opération GitHub se fait avec `benmesswass@gmail.com` / compte GitHub `benmesswass`. Avant tout push : vérifier `git config user.email`.

## Vision produit

Plateforme de commande via QR code pour restaurants/cafés tunisiens. Client scanne
le QR de sa table → menu → panier → valide. La commande part vers un écran
partagé consulté par tous les serveurs (les commandes de toutes les tables
s'y empilent) ; un serveur la prend en charge, confirme avec la table, puis
valide → elle part en temps réel sur l'écran cuisine. Le manager suit
l'activité globale (temps par étape, charge par serveur). Paiement carte
(pourboire optionnel) ou cash via l'app.

## Stack

- Backend : FastAPI + SQLAlchemy + PostgreSQL (`backend/`)
- Frontend : Next.js (app router) + Tailwind (`frontend/`)
- Temps réel : WebSocket natif FastAPI (`backend/app/modules/notifications/`)

## Architecture

Monolithe modulaire. Un module = un domaine métier, isolé sous
`backend/app/modules/<nom>/` avec `models.py`, `schemas.py`, `router.py`,
et `service.py` quand la logique métier le justifie (ex: `orders`).

Modules : `tenants` (restaurants), `tables`, `staff` (comptes + auth),
`menu`, `orders`, `notifications` (WebSocket manager).

Pas de microservices tant qu'il n'y a pas de preuve réelle de besoin
(plusieurs équipes, charge prouvée).

## Conventions à respecter

- Tout modèle porte `restaurant_id` (multi-tenant-ready dès le départ —
  pas de migration lourde plus tard).
- Statuts de commande explicites (`OrderStatus` dans `orders/models.py`) avec
  transitions contrôlées dans `orders/service.py::ALLOWED_TRANSITIONS`.
  Ne jamais ajouter de transition sans mettre à jour ce dict.
- Prix figé sur `OrderItem` au moment de la commande — ne jamais recalculer
  depuis `MenuItem.price` après coup.
- QR token de table = `secrets.token_urlsafe`, jamais un ID incrémental.
- Nouveau modèle = l'ajouter dans `app/core/model_registry.py`, sinon SQLAlchemy
  ignore le modèle et toute foreign key qui le vise casse (tests comme
  autogénération de migration).
- Nouveau champ ou nouveau modèle = une migration Alembic dans la même PR.
  `create_all()` ne tourne plus qu'en test : sans migration, la colonne
  n'existera pas en production. `tests/test_migrations.py` le vérifie en
  lançant `alembic upgrade head` et en comparant le schéma obtenu aux modèles —
  quand il échoue, la correction est de générer la migration, jamais de
  toucher au test.
- Routes client (scan QR, commande, suivi, paiement) : publiques par design,
  mais jamais **non liées**. Chacune exige soit le `qr_token` de la table, soit
  le `public_token` de la commande, et répond 404 — jamais 401/403 — quand il
  manque, pour ne pas confirmer l'existence de la ressource. Ne jamais exposer
  de donnée personnelle sur ces réponses : `loyalty_phone` vit dans
  `OrderOutStaff`, servi aux seules routes sous JWT.
- Nouvelle donnée personnelle collectée (ou durée de conservation modifiée) =
  mettre à jour `frontend/lib/i18n/privacy.ts` (fr **et** ar) dans la même PR.
  Une politique de confidentialité qui ne décrit plus ce que le code fait est
  pire que pas de politique. Même règle pour toute purge : elle vit dans le
  service du module concerné et passe par `scripts/purge_donnees_personnelles.py`.
- Logs via `app/core/logging.py::log_event(logger, message, **context)` —
  toujours avec `restaurant_id`/`order_id`/`table_id` en contexte.
- Routes staff/cuisine/manager protégées par `get_current_staff` (JWT) +
  vérification du rôle ; routes client (scan QR, création/suivi de
  commande) restent publiques par design.

## Commandes

```bash
# Backend — tests (SQLite en mémoire, pas besoin de Postgres)
cd backend && pip install -r requirements-dev.txt && pytest -q

# Environnement complet local
docker compose up --build

# Seed de démo (restaurant + comptes staff + tables + menu)
cd backend && python scripts/seed_demo.py

# Installer un établissement pilote en une passe (restaurant, équipe, tables,
# carte depuis CSV, chevalets QR à imprimer, fiche de remise des identifiants).
# Idempotent : relancer après correction du CSV met à jour, ne duplique pas.
cd backend && python scripts/setup_restaurant.py --config mon-pilote.json \
  --frontend-url https://tawla.tn
# Modèle de configuration : backend/scripts/pilote-exemple.json

# Frontend — lint / typecheck / build
cd frontend && npm run lint && npx tsc --noEmit && npm run build

# Générer le QR d'une table (après création via API)
python backend/scripts/generate_table_qr.py --qr-token <token> --label "Table 5"

# Purge de rétention des données personnelles (Phase 16) — à lancer à la main,
# simule par défaut, n'efface qu'avec --appliquer.
cd backend && python scripts/purge_donnees_personnelles.py [--appliquer]

# Migrations Alembic — seule voie d'évolution du schéma depuis la Phase 12.2.
# L'app ne crée plus les tables au démarrage ; le CMD du Dockerfile lance
# `alembic upgrade head` avant uvicorn. Tout nouveau champ de modèle exige donc
# une migration, sinon la colonne manque en prod.
cd backend && alembic revision --autogenerate -m "description"
cd backend && alembic upgrade head

# Compte du dashboard plateforme (vue admin cross-tenant, /admin côté
# frontend) — un seul canal de création, jamais une route d'inscription
# publique : POST /api/v1/platform-admin/admins, verrouillé par
# ADMIN_CREATION_SECRET (backend/.env, jamais commité, connu de Wassim
# seul — voir app/modules/platform_admin/router.py::create_admin).
# Idempotent par e-mail : rejouer met à jour le mot de passe/nom/réactive
# plutôt que d'en créer un second.
curl -X POST http://localhost:8000/api/v1/platform-admin/admins \
  -H "Content-Type: application/json" \
  -d '{"secret": "<ADMIN_CREATION_SECRET>", "email": "wassim@tawla.tn", "name": "Wassim", "password": "<mot-de-passe>"}'
```

Comptes démo (fixes, mot de passe `tawla2026`) : `manager@tawla.tn` (manager),
`sami@tawla.tn` (serveur), `cuisine@tawla.tn` (cuisine). Les QR tokens des
tables, eux, changent à chaque reseed — voir `CREDENTIALS.md` local (généré
par le script, non commité).

## Montrer le produit — deux aides distinctes

Aucune des deux ne démarre seule : un restaurateur qui arrive sur le site n'a
jamais rien à fermer.

**Établissement de démonstration jetable** — « Voir la démo » ouvre d'abord
`POST /api/v1/demo/sessions` : un restaurant complet (équipe, tables, carte),
palier Pro, actif, `is_demo=true`, effacé **en entier** deux heures plus tard.
**Un par visiteur, jamais un compte partagé** : les canaux temps réel sont
groupés par `(restaurant_id, channel)` (`notifications/manager.py`), donc deux
démos sur le même établissement se verraient l'une l'autre. La purge se
déclenche à chaque création (pas d'ordonnanceur nécessaire) et depuis
`scripts/purge_donnees_personnelles.py`. Plafond dur `PLAFOND_DEMOS` + limite
par IP : c'est la seule route publique qui écrit en base. Si elle échoue, le
bouton lance quand même la visite, en version visiteur.

La réponse porte aussi un jeton pour le serveur et pour la cuisine, pas
seulement pour le manager : ces deux comptes ont un mot de passe généré
aléatoirement, jamais révélé (`demo/service.py::creer_demo`). Le bandeau
`BandeauDemo` propose de copier, pour chaque rôle, un lien `?demo_token=…`
qui connecte l'appareil qui l'ouvre sans mot de passe (`lib/demoLien.ts`,
consommé par `useAccesDemoParLien` en tout premier hook de `/dashboard`,
`/staff` et `/kitchen` — avant `useCurrentStaff`, dont l'ordre d'appel des
hooks garantit qu'il pose le jeton avant que la garde ne le vérifie). Sans ce
mécanisme, montrer l'écran serveur en direct sur un deuxième appareil pendant
qu'un client commande sur le sien n'avait aucun chemin possible.

**Chaque lien doit s'ouvrir sur un appareil ou un navigateur différent**,
jamais un deuxième onglet du même navigateur : `localStorage` est partagé
entre tous les onglets d'une même origine, donc ouvrir le lien cuisine dans
un onglet à côté du lien serveur écrase silencieusement le jeton serveur, qui
finit éjecté vers `/login` à la prochaine reconnexion WebSocket. Vérifié :
avec deux contextes de navigateur réellement séparés, une commande passée
côté client apparaît en direct sur l'écran serveur ouvert par lien, sans
rechargement.

- **Visite guidée** (`?visite=1`, ou le lien « Voir la visite guidée » en bas de
  l'accueil) — s'adresse au **restaurateur**. Bulles pas à pas ancrées sur les
  vrais éléments de l'écran, façon Stonly, sans dépendance ni service payant :
  moteur dans `frontend/components/visite/`, contenu dans
  `frontend/lib/visite/etapes.ts`. Chaque étape désigne sa cible par un attribut
  `data-visite="…"` posé sur la page — déplacer une section ne casse rien, la
  bulle se recentre (et le dit en console hors production). Ajouter une étape =
  une entrée dans `etapes.ts` et l'attribut correspondant, rien d'autre.
  **Deux parcours qui ne se croisent jamais**, parce qu'ils ne se jouent pas
  sur le même appareil (`Parcours` dans `etapes.ts`) :
  - **vente** — sur l'ordinateur de celui qui montre : accueil, paliers,
    inscription, connexion, tableau de bord, pool serveur, cuisine. Les deux
    écrans de service sont accessibles au manager connecté, aucun second
    compte n'est nécessaire. **Le parcours s'adapte au visiteur** (champ
    `acces` dans `etapes.ts`) : connecté, 20 étapes ; sans compte, les sept
    écrans derrière la connexion sortent de la liste et une étape de clôture
    les remplace — 14 étapes, et un compteur qui ne ment pas. Sans ça la
    visite marchait droit sur `/dashboard`, l'application la renvoyait sur
    `/login`, et elle restait plantée sur une pastille à 14/20.
  - **client** (6 étapes) — sur le téléphone, en ouvrant
    `…/menu/<qr_token>?visite=1` : la carte, un plat, le panier, l'appel
    serveur, le hors-ligne, le suivi. La visite ne peut pas y aller seule
    (elle ne connaît aucun `qr_token`), d'où le parcours séparé.

  Sur `/menu/…`, **seules** les étapes du parcours client s'affichent : une
  visite de vente en cours ailleurs n'y laisse même pas sa pastille.
  **Ouvrir à une étape précise** : `?visite=tarif-pro` (identifiant, à préférer
  dans un lien qu'on envoie — il survit à l'insertion d'une étape, et désigne
  son parcours) ou `?visite=6` (rang affiché dans le parcours de l'écran).
- **Aide-mémoire de démo** (`?demo=1`, `frontend/components/DemoGuide.tsx`) —
  s'adresse à **Wassim** pendant la démo : le script des gestes à faire
  (« coupez le réseau du téléphone, puis… »). S'efface tant que la visite
  guidée tourne.

## Roadmap

`ROADMAP.md` est le fichier unique de pilotage du projet (phases 19 à 24 depuis
l'audit final du 2026-08-15). Prendre la première tâche non cochée en partant du
haut, dans l'ordre des phases. Une tâche cochée `[x]` doit mentionner la PR qui
l'a livrée ; si le scope a été réduit, écrire pourquoi sur la ligne.

**Règle qui prime sur tout ajout de code** : après la Phase 20, toute
proposition de fonctionnalité doit nommer le restaurateur qui l'a demandée.
Sans nom, elle va dans la section « Sous condition » de `ROADMAP.md` et n'est
pas construite. Le produit ne manque pas de fonctionnalité, il manque un client.

- `AUDIT_COUTS_PRODUCTION.md` — audit du 2026-08-18 : ce que coûte réellement
  en argent la mise en production de Tawla (infrastructure, services tiers,
  domaine, conformité technique), chiffré et sourcé, obligatoire vs
  conditionnel clairement séparés.
- `AUDIT_FINAL.md` — audit du 2026-08-15 qui fonde la roadmap actuelle : code
  exécuté, 42 fonctionnalités notées, trois défauts à fermer, note recalculée.
- `ROADMAP_ARCHIVE.md` — historique des phases 0 à 11. Lecture seule, ne rien y
  ajouter : les décisions et renoncements qu'il documente restent la
  justification de l'état du code.
- `MARCHE_FRANCE.md` — dossier de cadrage du marché français (2026-08-24, F0
  tranchée le même jour — scénario C, les deux marchés en parallèle) :
  différences produit/légales/techniques avec la Tunisie, architecture à deux
  marchés, sélecteur de pays, phases F0 à F8. **Ce n'est PAS une seconde
  roadmap et ça ne remet pas en cause « `ROADMAP.md` est le fichier unique de
  pilotage »** : une session qui cherche la prochaine tâche **codable** prend
  `ROADMAP.md` en priorité ; `MARCHE_FRANCE.md` pilote le chantier France en
  parallèle, jamais à la place de `ROADMAP.md`.
- `REVUE_INVESTISSEURS.md` — revue d'investissement du 2026-08-13 (grille de
  notation, failles vérifiées, plafond de revenus).
- `PREMIERES_VENTES.md` — audit orienté vente et les dix recommandations pour
  les premiers clients.
- `terrain/` — documents de terrain, pas du code. Point d'entrée :
  `terrain/PARCOURS.md`, qui ordonne les 31 tâches 🧑 de la roadmap et renvoie
  vers le mode d'emploi de chacune (`MISE_EN_LIGNE.md` pour la production,
  `GUIDE_ENTRETIEN.md` pour obtenir et mener les entretiens, `RELEVE_AVANT.md`
  pour la semaine de référence, `FORMATION_10MIN.md` et `PRISE_EN_MAIN.md` pour
  l'installation, `ENTRETIENS.md` et `PILOTES.md` pour les relevés). Ils se
  tiennent à jour à la main, sur place ; ne jamais les remplir depuis une
  session — un chiffre de terrain inventé détruit la seule chose que Tawla a à
  vendre.

Objectif en cours : passer de 5,3/10 à 8/10 au prochain jury. Le tableau en tête
de `ROADMAP.md` dit quelle dimension chaque phase déplace — le recalculer à la
clôture de chaque phase. Une tâche qui ne déplace aucune note est une tâche qui
n'aurait pas dû être faite.

**Cadrage produit (Wassim, 2026-08-13)** : Tawla est une entreprise rentable et
non diluée, pas un dossier de levée. Conséquences : un prix unique élevé avec
service inclus plutôt qu'un alignement sur les 19-49 DT du marché, cible
restaurants de 6 tables et plus, et pas d'expansion régionale.

## Philosophie d'ingénierie (à appliquer par défaut)

KISS, YAGNI strict, complexité seulement si elle réduit un coût réel
(maintenance, bugs, scalabilité prouvée). Avant d'ajouter une abstraction :
est-ce que 80% du besoin est couvrable plus simplement ? QA pragmatique —
tester les risques métier réels (intégrité commande, isolation multi-tenant,
contrats API), pas la couverture pour la couverture.

## Workflow PR

Jamais de push direct sur `main` — toujours une branche feature + PR. CI
(lint/typecheck/tests backend+frontend) doit être verte avant merge.
