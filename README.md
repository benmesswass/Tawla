# Tawla (resto-qr-menu)

Plateforme de commande via QR code pour restaurants/cafés tunisiens.

**Flux** : le client scanne le QR de sa table → consulte le menu → ajoute au
panier → valide. La commande apparaît immédiatement dans un écran partagé
consulté par tous les serveurs (toutes les tables s'y empilent). Un serveur
la prend en charge, la confirme avec les clients à table, puis valide → elle
part alors sur l'écran cuisine en temps réel. Le manager suit l'activité
globale (temps par étape, charge par serveur — base des primes de
rendement). Paiement carte (pourboire optionnel) ou cash via l'app.

Toutes les fonctionnalités prévues, phase par phase, sont détaillées dans
[`ROADMAP.md`](./ROADMAP.md). Conventions du projet dans [`CLAUDE.md`](./CLAUDE.md).

## Architecture

Monolithe modulaire (pas de microservices — pas de besoin réel à ce stade) :

```
backend/app/
├── core/            # config, DB, logs structurés (transverse)
└── modules/
    ├── tenants/     # restaurants (multi-tenant-ready dès le MVP)
    ├── tables/      # tables + token QR opaque
    ├── staff/       # serveurs / cuisine / manager + auth
    ├── menu/        # items du menu
    ├── orders/      # cœur métier : commandes + transitions d'état
    └── notifications/  # WebSocket (temps réel serveur/cuisine)

frontend/app/
├── menu/[qrToken]/  # page client (scan QR → menu → panier)
├── staff/           # confirmation des commandes par le serveur
├── kitchen/         # écran cuisine (grand écran)
└── dashboard/       # manager
```

**États d'une commande** : `pending_confirmation → confirmed →
sent_to_kitchen → in_preparation → ready → served` (+ `cancelled`). Les
transitions interdites sont bloquées au niveau service (`orders/service.py`),
pas seulement côté UI.

## Lancer en local

```bash
cp backend/.env.example backend/.env
docker compose up --build
cd backend && python scripts/seed_demo.py
```

- Backend : http://localhost:8000/docs (Swagger auto-généré)
- Frontend : http://localhost:3000
- Comptes démo : voir `CREDENTIALS.md` (généré par le seed)

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest -q
```

Tests couvrant les vrais risques métier (pas de la couverture pour la
couverture) : cycle de vie complet d'une commande, impossibilité de sauter
l'étape de confirmation serveur, item indisponible rejeté, prix figé à la
commande, isolation stricte entre restaurants, tokens QR uniques et
non-devinables, authentification et prise en charge (claim) des commandes.
Base SQLite en mémoire, isolée par test — aucune dépendance à Postgres pour
lancer la suite.

## Générer le QR code d'une table

```bash
# 1. Créer la table via l'API (renvoie un qr_token)
curl -X POST http://localhost:8000/api/v1/tables \
  -H "Content-Type: application/json" \
  -d '{"restaurant_id": 1, "label": "Table 5"}'

# 2. Générer l'image à imprimer
python backend/scripts/generate_table_qr.py \
  --qr-token <token_renvoyé> --label "Table 5" \
  --frontend-url https://menu.monresto.tn
```
