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
```

Comptes démo (fixes, mot de passe `tawla2026`) : `manager@tawla.tn` (manager),
`sami@tawla.tn` (serveur), `cuisine@tawla.tn` (cuisine). Les QR tokens des
tables, eux, changent à chaque reseed — voir `CREDENTIALS.md` local (généré
par le script, non commité).

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
