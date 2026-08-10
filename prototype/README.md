# resto-qr-menu

Plateforme de commande via QR code pour restaurants/cafés tunisiens.

**Flux** : le client scanne le QR de sa table → consulte le menu → ajoute au
panier → valide. La commande part au serveur assigné à cette table, qui la
confirme avec les clients avant validation finale → la commande part alors
sur l'écran cuisine en temps réel.

## Architecture

Monolithe modulaire (pas de microservices — pas de besoin réel à ce stade) :

```
backend/app/
├── core/            # config, DB, logs structurés (transverse)
└── modules/
    ├── tenants/     # restaurants (multi-tenant-ready dès le MVP)
    ├── tables/      # tables + token QR opaque
    ├── staff/       # serveurs / cuisine
    ├── menu/        # items du menu
    ├── orders/      # cœur métier : commandes + transitions d'état
    └── notifications/  # WebSocket (temps réel serveur/cuisine)

frontend/app/
├── menu/[qrToken]/  # page client (scan QR → menu → panier)
├── staff/           # confirmation des commandes par le serveur
└── kitchen/         # écran cuisine (grand écran)
```

**États d'une commande** : `pending_confirmation → confirmed →
sent_to_kitchen → in_preparation → ready → served` (+ `cancelled`). Les
transitions interdites sont bloquées au niveau service (`orders/service.py`),
pas seulement côté UI.

**MVP mono-restaurant** : tout le modèle de données porte déjà
`restaurant_id`, donc pas de migration lourde le jour où on ajoute un 2e
client. Pas d'auth multi-tenant / billing pour l'instant — à construire
seulement si le besoin est prouvé.

## Lancer en local

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

- Backend : http://localhost:8000/docs (Swagger auto-généré)
- Frontend : http://localhost:3000

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest -q
```

8 tests couvrant les vrais risques métier (pas de la couverture pour la
couverture) : cycle de vie complet d'une commande, impossibilité de sauter
l'étape de confirmation serveur, item indisponible rejeté, prix figé à la
commande, isolation stricte entre restaurants (table/menu d'un resto A
inutilisables par un resto B), tokens QR uniques et non-devinables. Base
SQLite en mémoire, isolée par test — aucune dépendance à Postgres pour
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

## À faire avant un vrai pilote resto

- [ ] Auth basique pour le staff (login serveur/cuisine)
- [x] Génération des QR codes par table (`scripts/generate_table_qr.py`)
- [ ] Gestion des ajouts de commande sur une table déjà servie
- [ ] Fallback impression cuisine si l'écran/réseau tombe
- [ ] Dashboard resto pour gérer le menu (CRUD + upload photos)
- [x] Tests : intégrité commande, isolation par restaurant, contrat API
