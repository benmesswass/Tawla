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
- Nouveau modèle = l'ajouter dans `app/core/model_registry.py`, sinon
  `create_all()` casse silencieusement sur les foreign keys.
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

# Frontend — lint / typecheck / build
cd frontend && npm run lint && npx tsc --noEmit && npm run build

# Générer le QR d'une table (après création via API)
python backend/scripts/generate_table_qr.py --qr-token <token> --label "Table 5"
```

Comptes démo (fixes, mot de passe `tawla2026`) : `manager@tawla.tn` (manager),
`sami@tawla.tn` (serveur), `cuisine@tawla.tn` (cuisine). Les QR tokens des
tables, eux, changent à chaque reseed — voir `CREDENTIALS.md` local (généré
par le script, non commité).

## Roadmap

`ROADMAP.md` est le fichier unique de pilotage du projet (phases 0 à 7).
Prendre la première tâche non cochée en partant du haut, dans l'ordre des
phases. Une tâche cochée `[x]` doit mentionner la PR qui l'a livrée.

## Philosophie d'ingénierie (à appliquer par défaut)

KISS, YAGNI strict, complexité seulement si elle réduit un coût réel
(maintenance, bugs, scalabilité prouvée). Avant d'ajouter une abstraction :
est-ce que 80% du besoin est couvrable plus simplement ? QA pragmatique —
tester les risques métier réels (intégrité commande, isolation multi-tenant,
contrats API), pas la couverture pour la couverture.

## Workflow PR

Jamais de push direct sur `main` — toujours une branche feature + PR. CI
(lint/typecheck/tests backend+frontend) doit être verte avant merge.
