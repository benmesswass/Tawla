# Audit de pré-lancement — Tawla

Réalisé le 2026-08-18 sur `main` au commit `31f0bff` (PR #52). **La PR #53 est
ouverte, non fusionnée** : les photos de carte, le glisser-déposer, `UtcDatetime`,
le pourboire en espèces et l'ardoise de table n'existent pas dans le code audité
et ne sont comptés nulle part ici.

Chaque constat porte sa preuve : un `fichier:ligne`, ou la commande exécutée et
sa sortie. Ce qui n'a pas pu être vérifié est écrit comme tel.

---

## 1. Décision

**Non — on ne met pas en ligne.** Bloquants, dans l'ordre où il faut les traiter :
(1) la Phase 20 n'a été exécutée à **aucun** de ses 9 points — rien n'est hébergé,
aucune sauvegarde n'a jamais été restaurée, et la déclaration INPDP, préalable
légal au premier client réel, n'est pas déposée ; (2) `scripts/seed_demo.py` livre
une base sans les tables de commandes — toute installation neuve hors Docker
répond **HTTP 500** à la première commande ; (3) le tableau de bord manager
s'auto-contredit à l'écran (« Commandes en cours **5** » au-dessus d'une liste qui
en compte **4**).

Rien dans cette liste ne demande plus d'une journée de travail. Le produit lui-même
tient : 299 tests verts, parcours complet rejoué de bout en bout, et **aucune** des
attaques tentées n'a abouti.

---

## 2. Ce qui a été vérifié

### Suites exécutées

| Commande | Résultat |
|---|---|
| `cd backend && .venv/bin/pytest -q` | **299 passed** en 129,73 s — 0 échec, 0 ignoré |
| `cd frontend && npm run lint` | **1 avertissement**, 0 erreur (`@next/next/no-img-element`, `app/menu/[qrToken]/page.tsx:1087`) |
| `cd frontend && npx tsc --noEmit` | **aucune sortie** — 0 erreur de typage |
| `cd frontend && npm run build` | **succès**, 17 routes générées, 87,3 kB de JS partagé |

Environnement : venv Python 3.11.15 (3.12 attendu, sans incidence constatée),
`DATABASE_URL=sqlite:///./tawla.db`, schéma créé par `alembic upgrade head`
(11 migrations), seed par `scripts/seed_demo.py`. Le build a été lancé **avant**
tout `next dev`, jamais en parallèle.

### Parcours rejoués (Playwright, Chromium)

Backend `uvicorn` sur `:8000`, frontend `next dev` sur `:3000`, comptes de démo
(`manager@tawla.tn`, `sami@tawla.tn`, `cuisine@tawla.tn` / `tawla2026`).

| # | Parcours | Résultat |
|---|---|---|
| 1 | Client : scan QR → carte → panier → validation | OK — commande #1 créée, 0 erreur JS |
| 2 | Serveur : pool partagé → « Prendre en charge » → « Confirmé avec la table → cuisine » | OK, 0 erreur JS |
| 3 | Cuisine : « Commencer » → « Prêt » | OK, 0 erreur JS |
| 4 | Manager : tableau de bord, suivi d'activité, page de preuve | OK, 0 erreur JS |
| 5 | Paiement **carte** (simulé) | OK — « Payé ✓ par carte » |
| 6 | Paiement **espèces** : demande client → écran serveur | OK — la demande remonte |
| 7 | **Appel serveur** | OK — « ✓ Serveur prévenu, il arrive » |
| 8 | **Hors ligne** : panier composé → réseau coupé → validation → réseau rétabli | OK — mise en file locale, envoi automatique, **une seule** commande (#7), file vidée |
| 9 | **Double validation** (double-clic sur « Valider ») | OK — **une seule** commande (#8) : l'idempotence de la Phase 19.2 tient |

### Attaques tentées, et code HTTP obtenu

Toutes les tentatives ci-dessous ont été exécutées contre l'instance locale.

| Tentative | Obtenu | Verdict |
|---|---|---|
| `GET /orders/{id}` **sans** `X-Order-Token` | **404** `ORDER_NOT_FOUND` | bloqué |
| `GET /orders/{id}` avec un token faux | **404** (identique) | bloqué |
| Énumération séquentielle `GET /orders/1..5` | **404** sur les 5, réponse identique | bloqué |
| `GET /orders/{id}` avec le bon token | 200, **aucun `loyalty_phone`** dans la réponse | conforme |
| JWT d'un autre resto → `/orders/by-restaurant/1/active` | **403** | bloqué |
| JWT d'un autre resto → `/restaurants/1` | **404** | bloqué |
| JWT d'un autre resto → `/orders/{id}/confirm` | **404** | bloqué |
| JWT d'un autre resto → `/orders/{id}/pay/cash/confirm` | **404** | bloqué |
| JWT d'un autre resto → `/staff/by-restaurant/1` | **403** | bloqué |
| JWT d'un autre resto → `/stats/dashboard/1`, `/stats/preuve/1`, `/stats/equipe/1`, `/stats/kitchen-today-count/1` | **403** sur les 4 | bloqué |
| JWT d'un autre resto → `/loyalty/by-restaurant/1/member` | **403** | bloqué |
| JWT d'un autre resto → `/tables/by-restaurant/1` | **403** | bloqué |
| Rôle **serveur** → `PATCH /menu-items/1` | **403** `insufficient role` | bloqué |
| Rôle **serveur** → `POST /staff` | **403** | bloqué |
| Rôle **serveur** → `POST /menu-items/import-csv` | **403** | bloqué |
| `POST /orders` sans `qr_token` | **422** | bloqué |
| `POST /orders` avec `restaurant_id`+`table_id` devinés | **422** (champs ignorés) | bloqué |
| `POST /orders` avec un `qr_token` inventé | **404** `INVALID_TABLE_CODE` | bloqué |
| `POST /orders` sur un plat d'un autre resto | **404** `ITEM_NOT_FOUND` | bloqué |
| WS `/ws/staff/1` sans token · token bidon · JWT d'un autre resto | **fermé 4401** dans les 3 cas | bloqué |
| WS `/ws/kitchen/1` sans token · JWT d'un autre resto | **fermé 4401** | bloqué |
| WS `/ws/order/1/{id}` sans token · token faux | **fermé 4401** | bloqué |
| WS `/ws/table/1/{qr_token faux}` | **fermé 4401** | bloqué |
| WS `/ws/menu/{id}` (resto existant **et** inexistant) | connecté dans les 2 cas | ouvert **par conception**, sans signal d'énumération |
| Dépôt de photo par un rôle serveur | **403**, et **aucune route d'upload n'existe** (53 routes, 0 photo/image/upload) | sans objet sur `main` |
| SVG à script en `image_url`, puis `javascript:` en `image_url` | stockés (**200**), mais **aucun script exécuté** dans le navigateur | non exploitable |
| Balayage `/loyalty/lookup` | **200** sur un numéro connu, **404** sur un inconnu | voir S-3 |
| Énumération publique `GET /menu-items/by-restaurant/{1,2,3}` | **200** sans aucun jeton | voir S-1 |

Fuite de données personnelles : sur les 53 routes exposées, `loyalty_phone`
n'apparaît que dans `OrderCreate` (entrée, le client donne son propre numéro) et
`OrderOutStaff` (sortie réservée au JWT). **L'invariant tient.**

### Ce qui n'a pas pu être vérifié en local — renvoyé à la Phase 20

- Le comportement derrière le **vrai proxy** de Railway/Render (le limiteur de
  débit en dépend entièrement — voir S-2).
- Le comportement en **HTTPS réel** sur un domaine (voir C-1).
- Le comportement sous **charge réelle** d'un service (une seule instance backend,
  gestionnaire WebSocket et limiteur en mémoire).

---

## 3. Les cinq audits

Gravité : 🔴 **bloquant avant mise en ligne** · 🟠 **à corriger avant le premier
pilote** · 🟡 **à corriger après** · ⚪ **observation**.

### 3.1 — Produit / PO

**P-1 🔴 La Phase 20 n'a pas commencé : 0 point sur 9.**
`ROADMAP.md:161-169` — hébergement, domaine, vraies clés, sauvegardes, restauration
d'une sauvegarde, monitoring, collecte d'erreurs, parcours de recette, déclaration
INPDP : les neuf cases sont vides. Deux d'entre elles ne sont pas des tâches
d'infrastructure mais des préalables : la **restauration d'une sauvegarde**
(« la seule qui prouve les autres », `ROADMAP.md:165`) et la **déclaration INPDP**
(`ROADMAP.md:169`), qui conditionne légalement la collecte des numéros de fidélité
déjà codée depuis la Phase 16.

*Ce qui casse* : il n'y a rien à mettre en ligne, et le premier client réel serait
servi hors cadre déclaratif.
*Correctif* : exécuter `terrain/MISE_EN_LIGNE.md` de bout en bout avant tout autre
travail de code.
*À noter* : la Phase 19 est close **à une case près**, `ROADMAP.md:133` — « vérifier
sur staging derrière le vrai proxy », marquée 🧑 et explicitement non constatable
ailleurs qu'en production. Elle ne bloque pas le code ; elle bloque avec la Phase 20,
et elle porte déjà la question CGNAT reprise en S-2.

**P-2 🔴 Le prix n'est toujours pas tranché.**
`frontend/lib/offer.ts:18` — `PRICE_MONTHLY_DT: number | null = null`. La page
publique affiche « tarif communiqué au premier rendez-vous ». La Phase 22
(`ROADMAP.md:207-224`) propose 120 DT ; personne ne l'a arrêté.
*Ce qui casse* : on peut faire visiter le produit, pas le vendre.
*Correctif* : trancher le prix (décision de Wassim, aucune donnée nouvelle requise).

**P-3 ⚪ Zéro entretien, zéro pilote — et c'est le vrai sujet.**
`terrain/ENTRETIENS.md:10-29` porte **20 lignes vides** ; `terrain/PILOTES.md`
ne contient qu'un modèle à copier, aucun établissement. Depuis l'audit du
2026-08-15, deux PR ont été fusionnées (#51, #52) : **les deux sont du code**.
*Ce qui casse* : c'est exactement la dérive que `ROADMAP.md:48` s'était engagé
à empêcher — « il ne manque pas de fonctionnalité, il manque un restaurateur ».
*Correctif* : aucun. C'est un constat, et il commande la grille du §4.

**P-4 ⚪ Le mot « Swagger » est affiché au restaurateur qui paie.**
`frontend/app/dashboard/page.tsx:547` — « Modifier un article, basculer une rupture
de stock, ou en ajouter un nouveau — **sans passer par Swagger**. »
*Ce qui casse* : un patron de restaurant ne sait pas ce qu'est Swagger ; la phrase
lui apprend surtout que l'écran a été écrit pour un développeur.
*Correctif* : réécrire la phrase du point de vue du patron, sans terme technique.

### 3.2 — Design

**D-1 🟠 L'écran serveur — celui qui est décrit comme *partagé* — est mis en page
comme un téléphone.**
Mesuré à 1280×800 : la colonne de contenu fait **448 px, soit 35 % de la largeur**,
et la page fait **816 px de haut pour une fenêtre de 800** — donc il faut déjà
faire défiler **avec une seule commande dans le système**. « Prêtes à servir »
commence à y=334, « Demandes de paiement en espèces » à y=488. À titre de
comparaison, l'écran cuisine occupe **96 %** de la largeur en deux colonnes de
604 px (`frontend/app/kitchen/page.tsx`, grille mesurée).
*Ce qui casse* : en service, un serveur qui a dix commandes en attente ne voit plus
« prêtes à servir » sans faire défiler — l'écran partagé posé au passe devient
inutilisable pour ce qu'il sert.
*Correctif* : donner à `/staff` la même mise en page multi-colonnes que
`/kitchen`, au-delà d'une largeur de tablette.

**D-2 ⚪ Deux systèmes de navigation empilés sur le tableau de bord.**
`frontend/app/dashboard/page.tsx` — une rangée de liens soulignés (« Suivi de
l'activité · Preuve du pilote · Rapport d'équipe · Se déconnecter ») surmonte une
barre d'onglets (« Menu · Tables & zones · Équipe · Réglages »). Deux grammaires
de navigation à 40 px l'une de l'autre.
*Correctif* : fusionner en une seule barre.

**D-3 ⚪ Vérifié et écarté** — la barre « Valider la commande » ne recouvre
**pas** le dernier plat de la carte. Mesuré au défilement maximal : dernier plat
jusqu'à y=668, barre à partir de y=771, soit 103 px de dégagement. L'apparence de
chevauchement venait d'une capture `fullPage`, pas du produit.

**D-4 ⚪ Vérifié et écarté** — le format de date américain observé sur le
sélecteur « Journée » vient de la locale du navigateur de test, pas du produit :
`app/layout.tsx:12` sert bien `<html lang="fr">`, confirmé sur le HTML rendu.

### 3.3 — Fonctionnel

**F-1 🔴 `scripts/seed_demo.py` produit une base sans les tables de commandes.**
`backend/scripts/seed_demo.py:74` appelle `Base.metadata.create_all(bind=engine)`,
mais ses imports (`:17-22`) ne chargent que `MenuItem`, `Staff`, `Table`,
`Restaurant` — **jamais `app.core.model_registry`**. SQLAlchemy ne crée donc que
ce qu'il connaît.
*Constaté* : après `python scripts/seed_demo.py` sur une base neuve, les 5 tables
créées sont `menu_items`, `menu_suggestions`, `restaurants`, `staff`, `tables`.
Manquent `orders`, `order_items`, `loyalty_members`, `waiter_calls`. La première
commande répond alors **HTTP 500** —
`sqlite3.OperationalError: no such table: orders`. Idem pour `/loyalty/lookup`.
*Ce qui casse* : `CLAUDE.md` documente cette commande comme le moyen de monter une
démo. Wassim la lance sur une base neuve devant un restaurateur, fait scanner le
QR, et l'application tombe en erreur au moment précis où le patron regarde. En
production le problème ne se pose pas — le `CMD` du `Dockerfile:15` lance
`alembic upgrade head` avant `uvicorn` — mais c'est justement pourquoi personne ne
l'a vu.
*Preuve que la convention est connue* : `scripts/purge_donnees_personnelles.py:26`
importe `model_registry` avec un commentaire qui explique exactement pourquoi.
*Correctif* : ajouter `from app.core import model_registry  # noqa: F401` aux
imports de `seed_demo.py`.

**F-2 🔴 Le tableau de bord se contredit sur le même écran.**
`backend/app/modules/stats/service.py:125-127` — `active_orders_count` compte
**toutes** les commandes actives du restaurant, sans borne : ni la journée de
service, ni même le paramètre `day` de la requête. Or
`backend/app/modules/orders/service.py:82` borne la liste des commandes actives à
`Order.created_at >= service_day_start()`. Les deux valeurs sont affichées **dans
la même carte** : le badge vient de `active_orders_count`
(`frontend/app/dashboard/stats/page.tsx:198`), la ventilation juste en dessous
vient de la liste bornée (`:137`).
*Constaté* : après injection d'une seule commande restée en attente il y a 3 jours,
l'écran affiche « Commandes en cours **5** » au-dessus d'une ventilation
3+0+0+0+1 = **4**. L'API confirme : `active_orders_count = 3` contre 2 commandes
renvoyées par `/orders/by-restaurant/1/active` au même instant.
*Ce qui casse* : le patron additionne la colonne, trouve une commande manquante,
et cesse de croire le seul écran que Tawla a à lui vendre. L'écart grandit à chaque
service.
*Déjà connu, et c'est ce qui compte ici* : `ROADMAP.md:147` écrit noir sur blanc,
à la clôture de la Phase 19.5, « Reste hors périmètre : `active_orders_count` du
tableau de bord manager n'est pas borné, il peut afficher un nombre que l'écran
serveur ne montre plus ». Le défaut n'est donc pas une découverte mais un report
assumé. Ce que ce report n'avait pas mesuré, c'est que les deux valeurs sont
affichées **dans la même carte, le total juste au-dessus de sa ventilation** : ce n'est pas un écart
entre deux écrans qu'un patron pourrait ne jamais rapprocher, c'est une
contradiction qu'il lit d'un seul coup d'œil. C'est ce qui le fait passer de
« hors périmètre » à bloquant.
*Correctif* : borner `active_orders_count` par `service_day_start()`, comme la
liste qu'il surmonte.

**F-3 🟠 Deux définitions de la journée cohabitent — et elles divergent pendant
Ramadan.**
Les écrans de service coupent à **5 h heure de Tunis**
(`backend/app/core/dates.py:16`, `service_day_start()`). Le tableau de bord et la
page de preuve coupent à **minuit UTC** (`backend/app/modules/stats/service.py:66`
et `:159-160`), un choix documenté comme « compromis assumé » en `:12-16`.
*Constaté*, sur la fenêtre commerciale visée : pour le jeûne du 19/02/2027,
l'iftar de 19 h 00 (Tunis) tombe dans la journée `2027-02-19` du tableau de bord,
le sohour de 2 h 30 dans la journée `2027-02-20`. Les écrans de service, eux,
rattachent les deux à la journée du `2027-02-19`.
*Ce qui casse* : pendant Ramadan — le seul moment où la démonstration se fait
toute seule (`ROADMAP.md:53`) — « Ventes du jour » coupe chaque soirée en deux
et ne correspond à aucune caisse.
*Correctif* : faire lire `service_day_start()` aux bornes de `stats/service.py`.

**F-4 🟠 Les demandes d'encaissement en espèces ne s'effacent jamais.**
`backend/app/modules/orders/service.py:97-107` — `list_pending_cash_payments`
filtre sur le restaurant, la méthode et le statut de paiement, **sans aucune borne
de date**, contrairement à `list_active_orders` juste au-dessus.
*Constaté* : une commande servie il y a 6 jours, restée en `CASH`/`PENDING`,
s'affiche toujours dans « Demandes de paiement en espèces » de l'écran serveur.
*Ce qui casse* : la liste que le serveur doit vider en fin de service se remplit
d'oubliés des semaines précédentes, et cesse d'être une liste de travail.
*Correctif* : même borne `service_day_start()` que les commandes actives.

**F-5 🟠 On peut payer une commande que personne n'a acceptée, puis se la faire
annuler — l'argent reste marqué « payé ».**
`backend/app/modules/orders/service.py:437-442` — `_get_payable_order` ne refuse
que les commandes `CANCELLED` ou déjà `PAID` : une commande en
`PENDING_CONFIRMATION` est payable. Et
`backend/app/modules/orders/service.py:309-325` autorise la transition vers
`CANCELLED` sans jamais regarder `payment_status`.
*Constaté* : commande #4 créée → `pay/card` avec 3 DT de pourboire → **200**,
`payment_status=paid` alors que `status=pending_confirmation` → le serveur annule
→ **200**, `status=cancelled` **et** `payment_status=paid`.
*Ce qui casse* : aujourd'hui le paiement est simulé, donc la conséquence se limite
à une ligne incohérente (`_paid_orders`, `stats/service.py:54-58`, l'exclut de la
recette — le patron ne voit rien). Le jour où Konnect est branché, c'est un
encaissement réel sans chemin de remboursement.
*Correctif* : refuser le paiement avant confirmation, et refuser l'annulation
d'une commande payée — ou exiger un geste de remboursement explicite.

**F-6 ⚪ Le suivi de commande vit en `sessionStorage`.**
`frontend/app/menu/[qrToken]/page.tsx:82` — les `public_token` des commandes
ouvertes sont écrits en `sessionStorage`, alors que la file hors ligne, elle, est
en `localStorage` (`:641`).
*Ce qui casse* : un client dont le navigateur ferme l'onglet — ce que fait iOS en
permanence sous pression mémoire — perd l'accès à son addition et au rappel
« vous avez des commandes non réglées ». Il reste rattrapable par le serveur en
espèces, pas par carte.
*Correctif* : passer ces références en `localStorage`, comme la file hors ligne.

### 3.4 — Sécurité

Le modèle décrit dans `CLAUDE.md` tient sous attaque réelle : énumération de
commandes fermée, isolation multi-tenant respectée sur les 12 routes testées,
rôles séparés, WebSockets refusés proprement (code 4401), aucune donnée
personnelle dans les réponses publiques. Les trois constats ci-dessous sont ce qui
reste.

**S-1 🟠 La carte de n'importe quel établissement se lit par identifiant
incrémental, sans aucun jeton.**
`backend/app/modules/menu/router.py:89-102` — `GET /menu-items/by-restaurant/{id}`
est publique et n'exige ni `qr_token` ni `public_token`. Idem pour
`GET /menu-items/by-restaurant/{id}/suggestions` (`:105-115`).
*Constaté* : `restaurant_id=1` → **200** avec la carte complète et les prix ;
`restaurant_id=2` et `3` → **200** avec `[]`. Un établissement qui a une carte se
distingue donc d'un identifiant libre.
*Ce qui casse* : c'est précisément l'énumération que la PR #44 (« Fermer
l'énumération des établissements par identifiant ») et la Phase 12.2 ont fermée
partout ailleurs — `GET /restaurants/{id}` répond bien **401** sans jeton, et la
route client passe par `/restaurants/by-token/{qr_token}`
(`backend/app/modules/tenants/router.py:26-37`). La liste des clients de Tawla,
avec leurs prix, reste lisible par la seule route qu'on a oubliée. C'est une
information commerciale, pas une donnée personnelle.
*Correctif* : servir la carte par `qr_token` comme le reste du parcours client.

**S-2 🟠 Le limiteur de débit repose sur une IP qu'une couche au-dessus a déjà
réécrite — et il bloque une table sur vingt au pire moment.**
Deux problèmes distincts dans `backend/app/core/rate_limit.py`.

*a) Le plafond.* `:13-14` — 20 requêtes par minute et par (IP, chemin).
**Constaté** : la 20ᵉ commande consécutive depuis une même IP reçoit **429**
(19 × 201, puis 11 × 429 sur 30 tentatives) ; et une commande passée **depuis une
autre table** sur la même IP reçoit **429** elle aussi. Or la Phase 23.1
(`ROADMAP.md:233`) impose de ne pas installer sans Wi-Fi utilisable à toutes les
tables : le déploiement nominal met donc **toute la salle derrière une seule IP
publique**. Vingt tables qui commandent dans la même minute — soit exactement
l'iftar — et la vingtième est refusée.
Aggravant : `RATE_LIMITED` **n'est traduit ni en français ni en arabe**
(`frontend/lib/errors.ts:6-33` et `:46-57`). Le client refusé lit le message
générique « Une erreur est survenue. **Réessayez dans un instant.** »
(`:40`) — un conseil qui prolonge le blocage.

*b) La source de l'IP.* `:37-43` lit `request.client.host` puis, si le pair est un
proxy déclaré, prend la **dernière** valeur de `X-Forwarded-For`. Mais uvicorn
enveloppe l'application dans son propre `ProxyHeadersMiddleware`, qui lit la
**même** variable d'environnement `FORWARDED_ALLOW_IPS`, et qui **réécrit
`scope["client"]`** à partir de la **première** valeur de l'en-tête
(`.venv/lib/python3.11/site-packages/uvicorn/middleware/proxy_headers.py:58`
et `:133`). Le raisonnement du fichier porte donc sur une valeur qu'une autre
couche a déjà choisie.
**Constaté**, avec `FORWARDED_ALLOW_IPS=*` — la valeur que
`backend/.env.example` recommande explicitement pour Railway/Render :
40 requêtes avec un `X-Forwarded-For` **différent** à chaque fois → **40 × 200,
aucun 429** ; 40 requêtes avec le **même** en-tête → 20 × 200 puis 20 × 429 ;
40 requêtes avec `X-Forwarded-For: "9.9.9.9, <IP variable>"` → **40 × 201**.
Autrement dit, dans la configuration recommandée, le limiteur ne vaut que la
garantie que le conteneur n'est **jamais** joignable autrement que par le proxy de
l'hébergeur, et que ce proxy ajoute bien l'IP qu'il a lui-même constatée.
*Pourquoi la suite de tests ne l'a pas vu* : `backend/tests/test_rate_limit.py:63`
(`test_en_tete_forwarded_ignore_quand_il_ne_vient_pas_du_proxy`) passe — et il a
raison de passer. Il exerce `client_ip()` via `TestClient(app)`
(`backend/tests/conftest.py:90`), qui appelle l'application ASGI **directement**.
`ProxyHeadersMiddleware` est ajouté par le **serveur** uvicorn, pas par
l'application : la couche qui réécrit l'IP en production n'existe tout simplement
pas sous test. La case cochée `ROADMAP.md:132` — « un en-tête envoyé par un client
non fiable est ignoré » — est donc vraie de l'application seule, et fausse du
processus réellement déployé.
*Cette garantie n'est pas vérifiable en local* : elle est renvoyée à la Phase 20
(elle y est déjà, `ROADMAP.md:133`), et elle doit y être **mesurée**, pas supposée.
*Correctif* : décider explicitement qui, d'uvicorn ou de l'application, détermine
l'IP cliente (une seule des deux), monter le plafond de `POST /orders` au-dessus
du nombre de couverts d'un service, et traduire `RATE_LIMITED`.

**S-3 ⚪ Le résidu assumé de `/loyalty/lookup` est plus large que ce qui est
écrit.**
`ROADMAP.md:111-114` note qu'avec le `qr_token` en main on peut « vérifier si un
numéro est connu de **ce** restaurant ». **Constaté** : la réponse **200** porte
aussi `order_count` et `is_birthday_today`
(`backend/app/modules/loyalty/schemas.py:38-39` et `:53-62`). Un numéro connu
renvoie donc « client d'ici, N commandes, et c'est son anniversaire aujourd'hui ».
Le `qr_token` est imprimé sur un chevalet posé sur la table : il n'est pas secret.
*Ce qui casse* : rien pour le restaurateur ; c'est un point de conformité 2004-63
à décrire exactement plutôt qu'à sous-estimer.
*Correctif* : ne rien changer au code, corriger la phrase du résidu — ou retirer
`order_count` de la vue publique.

**S-4 ⚪ Les canaux WebSocket `staff` et `kitchen` ne vérifient pas le rôle.**
`backend/app/modules/notifications/dependencies.py:31-54` —
`authenticate_staff_socket` contrôle le jeton, le compte actif et le restaurant,
jamais `staff.role`. Un compte cuisine peut donc écouter `/ws/staff/{id}` et
inversement, alors que les routes HTTP équivalentes séparent les rôles
(`require_role`, vérifié : **403**).
*Ce qui casse* : rien entre collègues d'un même établissement — les deux canaux
portent la même activité de service. À aligner par cohérence, pas par urgence.

**S-5 ⚪ `image_url` est stocké sans validation.**
`backend/app/modules/menu/schemas.py:80` accepte n'importe quelle chaîne.
**Constaté** : un manager peut y écrire `javascript:alert(...)` ou un
`data:image/svg+xml` contenant un `<script>` — les deux sont acceptés (**200**).
**Aucun script ne s'exécute** : vérifié dans le navigateur, l'`<img>`
(`frontend/app/menu/[qrToken]/page.tsx:1087`) ne rend rien et aucun dialogue ne se
déclenche. Le risque réel se limite à pointer les navigateurs des clients vers un
hôte tiers, et il est auto-infligé par établissement.
*À retenir pour la PR #53* : le jour où de vrais fichiers sont déposés, cette
absence de validation cesse d'être théorique.

**S-6 ⚪ Le dictionnaire du limiteur ne se vide jamais.**
`backend/app/core/rate_limit.py:16` — `_hits` est un `defaultdict` dont les clés
`(ip, chemin)` sont créées à chaque nouvelle IP et **jamais supprimées** ; seules
les entrées de la liste sont purgées (`:50-51`). Fuite lente sur une instance
longue durée. Sans conséquence à l'échelle visée (45 établissements), à connaître
avant d'y adosser quoi que ce soit.

### 3.5 — Client final

**C-1 🟠 Hors HTTPS, le panier ne se remplit pas — et rien ne le dit.**
`frontend/app/menu/[qrToken]/page.tsx:536` — `addToCart` appelle
`crypto.randomUUID()`. Cette fonction n'existe **que** dans un contexte sécurisé
(HTTPS, ou `localhost`).
**Constaté**, en isolant la cause (page servie depuis `localhost`, avec
`crypto.randomUUID` neutralisé) : le clic sur « + » lève
`crypto.randomUUID is not a function`, **le bouton « Valider la commande »
n'apparaît jamais**, et l'écran ne montre **aucune erreur**. Confirmé sur une
adresse IP en `http://` : `isSecureContext = false`,
`crypto.randomUUID = undefined`, `serviceWorker` indisponible.
*Ce qui casse* : sur le chemin documenté — Vercel + domaine, donc HTTPS
(`terrain/MISE_EN_LIGNE.md:138-146`) — le défaut **ne se déclenche pas**. Il se
déclenche partout ailleurs : démonstration sur une IP locale chez un prospect,
préproduction sans certificat, domaine `.tn` en attente de TLS. Le client tape
« + », rien ne se passe, et il n'y a rien dans les journaux. Le risque connu était
« les notifications push ne marchent pas hors HTTPS » ; la réalité est que
**la commande elle-même ne marche pas**.
*Correctif* : `crypto.randomUUID?.() ?? <repli>` — une ligne, et le contexte non
sécurisé ne coûte plus que les notifications.

**C-2 ⚪ Le parcours client est propre.** Rejoué de bout en bout sur un viewport
de téléphone : carte lisible et catégorisée dans l'ordre d'un repas, panier avec
note à la cuisine et plat « à partager », suivi en six étapes, prénom du serveur
affecté affiché, paiement carte et espèces, appel serveur avec accusé
(« ✓ Serveur prévenu, il arrive »), bascule arabe. **Zéro erreur JS** sur
l'ensemble des parcours.

**C-3 ⚪ Le hors-ligne est ce que le produit fait de mieux.** Réseau coupé
panier composé : « Votre commande est enregistrée sur votre téléphone et sera
envoyée automatiquement dès que la connexion revient ». Réseau rétabli : envoi
automatique, **une seule** commande, file locale vidée. C'est le critère de recette
n° 11 de `terrain/MISE_EN_LIGNE.md:211`, et il passe.

**C-4 ⚪ La carte n'a pas de photos sur `main`.** Aucune route d'upload n'existe
(53 routes exposées). Les photos arrivent avec la PR #53, non fusionnée. Le choix
de les stocker en base — assumé face aux systèmes de fichiers éphémères de
Railway/Render — **n'a donc pas été audité ici** : il n'existe pas dans le code
constaté. À réexaminer au moment de fusionner #53.

---

## 4. Grille de notation recalculée

Recalculée sur ce qui est **constaté** au 2026-08-18, jamais sur ce qui est
préparé, en cours de PR, ou prêt à être exécuté.

| Dimension | Poids | Précédente (2026-08-15) | **Constatée** | Mouvement et justification |
|---|---:|---:|---:|---|
| Accès au marché & vente | 20 % | 2,0 | **2,0** | `terrain/ENTRETIENS.md` : 20 lignes vides. `terrain/PILOTES.md` : aucun établissement. Phase 20 : 0/9. Zéro client. Rien n'a bougé — les deux PR fusionnées depuis sont du code. |
| Besoin marché prouvé | 20 % | 5,5 | **5,5** | Toujours aucun chiffre relevé nulle part. La PR #52 a amélioré l'**instrument** (recette limitée aux commandes réglées), pas la preuve. Tenu à 5,5 et non monté : F-2 montre que l'instrument se contredit encore à l'écran. |
| Viabilité économique | 20 % | 5,0 | **5,0** | `frontend/lib/offer.ts:18` : `PRICE_MONTHLY_DT = null`. Phase 22 intouchée. Aucun encaissement. |
| Prêt à vendre (installable, sûr) | 15 % | 7,5 | **7,0** | −0,5. Au crédit : la Phase 19 est close côté code et **vérifiée par l'attaque** (énumération, multi-tenant, WS, rôles : tout tient). Au débit : F-1 rend toute installation neuve hors Docker inutilisable, C-1 fait tomber le parcours client hors HTTPS sans message, F-2 fait mentir le tableau de bord, et la Phase 20 reste à 0/9. |
| Exécution technique | 15 % | 8,5 | **8,0** | −0,5. 299 tests verts, `tsc` propre, build propre, idempotence et hors-ligne prouvés en conditions réelles. Mais cinq défauts réels trouvés hors du filet de tests : `model_registry` oublié dans un script alors que la convention existe et qu'un autre script l'applique (`purge_donnees_personnelles.py:26`), une API à contexte sécurisé appelée sans garde, deux requêtes non bornées, deux définitions de la journée. |
| Différenciation sur une niche | 10 % | 6,5 | **6,5** | Aucun chiffre venu d'un pilote réel, aucun établissement citable. Inchangé par construction. |
| **Note pondérée** | **100 %** | **5,6** | **5,4** | |

Détail : (2,0×0,20) + (5,5×0,20) + (5,0×0,20) + (7,0×0,15) + (8,0×0,15) +
(6,5×0,10) = 0,40 + 1,10 + 1,00 + 1,05 + 1,20 + 0,65 = **5,40**.

La note baisse de 0,2 alors que deux PR ont été livrées. C'est cohérent avec ce
que `ROADMAP.md:48` avait posé : **le travail de code ne déplace plus la note**,
et un audit qui cherche vraiment finit par trouver de quoi la faire baisser. Les
deux lignes qui pèsent 40 % ne bougeront pas d'un dixième sans une porte de
restaurant franchie.

---

## 5. Ce que je refuse de faire maintenant

Chacun de ces manques est réel et reviendra. Aucun ne porte le nom d'un
restaurateur qui l'a demandé, donc aucun n'entre dans les recommandations — ils
vont en « Sous condition » (`ROADMAP.md:276-292`), avec leur déclencheur.

| Manque constaté | Pourquoi je ne le propose pas | Déclencheur |
|---|---|---|
| **Une addition unique pour plusieurs commandes d'une même table.** Vérifié : `payment_status` vit sur `Order` (`backend/app/modules/orders/models.py`), et la PR #52 a rendu les commandes ouvertes multiples — une table qui commande en deux fois produit donc deux additions à régler séparément. Le client final gère ça avec un rappel « commandes non réglées » (`page.tsx:686`), pas avec une addition. | C'est le premier chantier de la table « Sous condition », et son déclencheur est explicite. Le construire maintenant, c'est refaire exactement ce que la Phase 21.1 doit trancher. | Trois patrons sur vingt le mentionnent **spontanément** en Phase 21. |
| **Des tests frontend** (il n'y en a aucun sur 8 466 lignes). C-1 et D-1 auraient été attrapés par un test de rendu. | Le déclencheur écrit dit « un bug de panier constaté chez un pilote ». C-1 **est** un bug de panier — mais constaté par moi, pas chez un pilote. Je note la tension sans m'autoriser à trancher à la place de la roadmap. | Un bug de panier constaté chez un pilote, ou un second développeur sur `menu/[qrToken]/page.tsx`. |
| **Découper les deux fichiers de plus de 1 000 lignes** (`menu/[qrToken]/page.tsx` : 1 516 ; `dashboard/page.tsx` : 1 292). | Un refactor qui ne corrige aucun bug ne rapproche d'aucun client. | Même déclencheur que les tests frontend. |
| **L'intégration Konnect réelle.** F-5 (payer avant confirmation, annuler après paiement) ne coûte rien tant que le paiement est simulé. | Le cash domine le commerce tunisien ; personne n'a réclamé la carte. Mais F-5 doit être corrigé **avant** que Konnect soit branché, pas après. | Un pilote qui réclame le paiement par carte. |
| **Plusieurs instances backend.** Le gestionnaire WebSocket et le limiteur sont en mémoire (`notifications/manager.py:23`, `rate_limit.py:16`) ; S-6 en est un symptôme. | Contrainte assumée et documentée, sans conséquence à l'échelle de 45 établissements. | Une coupure constatée en pleine soirée, ou le 30ᵉ client. |
| **Un mode sombre côté client.** L'écran cuisine est déjà sombre, le parcours client est clair. | Aucun retour de terrain sur la lisibilité en terrasse le soir — et il n'y a pas de terrasse pour l'instant. | Un retour de pilote. |

---

## Annexe — ordre de traitement suggéré

1. **F-1** (une ligne d'import) — sans lui, aucune démonstration n'est fiable.
2. **F-2** (une borne de date) — sans lui, le tableau de bord ne se montre pas.
3. **C-1** (une ligne) — sans lui, toute démonstration hors HTTPS échoue en
   silence.
4. **Phase 20 entière**, `terrain/MISE_EN_LIGNE.md`, en terminant par la
   restauration de sauvegarde et le dépôt INPDP.
5. **S-2** à vérifier *sur l'hébergeur réel* une fois en ligne : le limiteur ne
   peut pas être validé ailleurs.
6. **P-2** (le prix) puis **Phase 21** — la seule chose qui déplace encore la note.

F-3, F-4, F-5, F-6, D-1, S-1 et P-4 sont réels mais peuvent attendre le premier
retour de terrain, qui dira lesquels comptent vraiment.
