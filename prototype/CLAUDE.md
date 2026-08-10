# resto-qr-menu

Plateforme de commande QR code pour restaurants/cafés tunisiens. Client scanne
le QR de sa table → menu → panier → valide. Le serveur assigné à la table
confirme avec les clients → valide → la commande part en temps réel sur
l'écran cuisine.

## Stack

- Backend : FastAPI + SQLAlchemy + PostgreSQL (`backend/`)
- Frontend : Next.js 14 (app router) + Tailwind (`frontend/`)
- Temps réel : WebSocket natif FastAPI (`backend/app/modules/notifications/`)

## Architecture

Monolithe modulaire. Un module = un domaine métier, isolé sous
`backend/app/modules/<nom>/` avec `models.py`, `schemas.py`, `router.py`,
et `service.py` quand la logique métier le justifie (ex: `orders`).

Modules : `tenants` (restaurants), `tables`, `staff`, `menu`, `orders`,
`notifications` (WebSocket manager).

Pas de microservices tant qu'il n'y a pas de preuve réelle de besoin
(plusieurs équipes, charge prouvée). Voir `README.md` pour le détail.

## Conventions à respecter

- Tout modèle porte `restaurant_id` (MVP mono-resto mais schéma
  multi-tenant-ready dès le départ — pas de migration lourde plus tard).
- Statuts de commande explicites (`OrderStatus` dans `orders/models.py`) avec
  transitions contrôlées dans `orders/service.py::ALLOWED_TRANSITIONS`.
  Ne jamais ajouter de transition sans mettre à jour ce dict.
- Prix figé sur `OrderItem` au moment de la commande — ne jamais recalculer
  depuis `MenuItem.price` après coup.
- QR token de table = `secrets.token_urlsafe`, jamais un ID incrémental.
- Nouveau modèle = l'ajouter dans `app/core/model_registry.py`, sinon
  `create_all()` casse silencieusement sur les foreign keys (déjà arrivé une
  fois avec `Staff`).
- Logs via `app/core/logging.py::log_event(logger, message, **context)` —
  toujours avec `restaurant_id`/`order_id`/`table_id` en contexte.

## Commandes

```bash
# Tests (SQLite en mémoire, pas besoin de Postgres)
cd backend && pip install -r requirements-dev.txt && pytest -q

# Environnement complet local
docker compose up --build

# Générer le QR d'une table (après création via API)
python backend/scripts/generate_table_qr.py --qr-token <token> --label "Table 5"
```

## Philosophie d'ingénierie (à appliquer par défaut)

KISS, YAGNI strict, complexité seulement si elle réduit un coût réel
(maintenance, bugs, scalabilité prouvée). Avant d'ajouter une abstraction :
est-ce que 80% du besoin est couvrable plus simplement ? QA pragmatique —
tester les risques métier réels (intégrité commande, isolation multi-tenant,
contrats API), pas la couverture. Voir `README.md` → section "À faire avant
un vrai pilote resto" pour le backlog priorisé.
