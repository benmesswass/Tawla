# Tawla — Roadmap Production

Née le **2026-09-10** de l'audit technique de mise en production : suite de tests
exécutée, PostgreSQL 16 réel, uvicorn lancé comme en production, charge tirée
jusqu'à la rupture, courses de concurrence reproduites.

**Ce fichier ne remplace pas [`ROADMAP.md`](./ROADMAP.md)** — mais il est le
seul des documents parallèles qui **le réordonne**, sur un point précis : la
**Phase 20 (« Mettre en ligne, pour de vrai ») ne doit pas être entamée avant
que le palier P1 ci-dessous soit clos**. Mettre Tawla en ligne aujourd'hui,
c'est mettre en ligne un backend que 40 commandes simultanées tuent
définitivement. La Phase 20 n'est pas annulée : elle est absorbée par P1
(correspondance en annexe C).

Pour le reste, la règle habituelle tient : une session qui cherche la prochaine
tâche de **code produit** va dans `ROADMAP.md`, une session qui travaille le
**visuel du parcours client** va dans `ROADMAP_DESIGN.md`, une session qui
travaille **la tenue en production et la montée en charge** vient ici.

## Le constat qui fonde cette roadmap

Le code métier de Tawla est bon. L'audit n'a trouvé **aucune fuite entre
restaurants** (21 sondes IDOR sur 21 bloquées), aucun double débit, aucune
requête qui dégénère (8 à 24 ms sur deux semaines de données réelles), et 789
tests verts.

Le problème est ailleurs, et il est unique : **le modèle d'exécution**. Trois
choix isolément défendables se combinent en interblocage.

```
A) endpoint def (threadpool)       -> 40/40 OK en 0.6s   | serveur sain
B) endpoint async def (POST /orders) ->  1/40 OK en 70.8s | serveur MORT
   +45s : health=INJOIGNABLE, 15 connexions "idle in transaction", 0 client
```

Même serveur, même base, même rafale de 40. Seule différence : `def` contre
`async def`. Le cas B ne récupère jamais — seul un redémarrage le sauve.

Deux plafonds mesurés en découlent :

- **14 WebSockets simultanées**, tous restaurants confondus (chaque canal
  authentifié immobilise une connexion base à vie) ;
- **≈ 100 requêtes/seconde**, et ce plafond **ne bouge pas** quand on triple le
  pool — il est dans le processus Python, pas dans la base.

La cible est de 100 restaurants × 50 clients. L'écart est d'environ **350×**.

## Objectif

**Tenir un service du vendredi soir sur 100 restaurants sans qu'un seul
restaurateur s'en aperçoive.**

Trois paliers, dans l'ordre. Chacun se termine par une **mesure**, jamais par
une impression.

| Palier | Ce qu'il rend possible | Effort estimé |
| --- | --- | --- |
| **P1 — Pilote sûr** | Un restaurant réel, jusqu'à ~50 clients. Débloque la Phase 20 de `ROADMAP.md`. | ≈ 5–7 j |
| **P2 — Multi-restaurants** | ~20 restaurants, plusieurs instances backend. | ≈ 8–12 j |
| **P3 — Tenir 5 000** | 100 restaurants × 50 clients, capacité **démontrée**. | ≈ 6–10 j |

Rapport complet de l'audit :
<https://claude.ai/code/artifact/2b06f62d-2cd6-4982-aec4-7e4cdc75dd96>

## §0 — Règles de session

1. **Prendre la première tâche non cochée en partant du haut**, dans l'ordre des
   paliers. Ne jamais piocher une tâche de P3 parce qu'elle paraît plus
   intéressante : P2 sans P1 ne sert à rien, P3 sans P2 est invérifiable.
2. **Une tâche cochée `[x]` mentionne la PR qui l'a livrée.** Si le périmètre a
   été réduit, écrire pourquoi sur la ligne.
3. **Chaque tâche porte son critère de validation.** Une correction de
   concurrence qui n'est pas prouvée par une mesure reproductible n'est pas
   livrée — c'est précisément parce que les tests existants ne testaient
   aucune concurrence que F1, F2 et F3 sont passés inaperçus si longtemps.
4. **Ne jamais casser ce qui est sain.** L'annexe B liste ce que l'audit a
   trouvé solide. Toute PR de ce chantier doit laisser ces propriétés vraies —
   en particulier l'isolation multi-tenant et l'intégrité du paiement.
5. Les tâches 🧑 demandent un compte, une carte bancaire ou une décision de
   Wassim. Elles ne sont jamais faisables en autonomie : les signaler et passer
   à la suivante, sans jamais rester bloqué.
6. **Les mesures de référence sont en annexe A.** Toute tâche qui prétend
   améliorer la tenue en charge se compare à ces chiffres, pas à une intuition.

---

## Palier P1 — Pilote sûr

**Bloquant avant la Phase 20 de `ROADMAP.md`.** Objectif : qu'un restaurant réel
puisse ouvrir son service sans qu'une rafale de commandes tue le backend, et
qu'une panne soit vue et récupérable.

### P1.1 — Supprimer l'interblocage (F1)

- [x] Sortir le travail base de la boucle d'événements. Approche retenue par
      Wassim : une fonction de service devient **synchrone** et se contente de
      décrire ce qu'il faudra diffuser (`Diffusion`) ; le routeur exécute ce
      travail bloquant dans un thread (`run_in_threadpool`) puis envoie les
      messages. La règle est vérifiable d'un grep — **aucune couche métier
      n'appelle `manager.broadcast`**. Point d'entrée unique :
      `manager.executer_puis_diffuser()`.
      **Mesuré, harnais et pool identiques à ceux de l'audit
      (5+10, timeout 30 s) : `0/40, serveur mort` → `40/40 en 0,7 s`,
      `/health` à 10 ms. Avec les défauts actuels : `200/200 en 3,8 s`.**
      (PR #201)
      *Reste, assumé et sans risque de concurrence : les trois routes de dépôt
      de photo (`tenants` ×2, `menu` ×1) gardent leur travail base sur la
      boucle. Ce sont des gestes de manager, isolés, jamais en rafale — les
      convertir imposait de réordonner leurs contrôles 403/415/413, du risque
      pour aucun gain mesurable. À faire avec §P2.2, qui les réécrit de toute
      façon en sortant les photos de la base.*

L'alternative — passer à `AsyncSession` + asyncpg — est écartée pour ce palier :
elle touche tous les modules, exige de réécrire chaque requête, et le gain sur
un produit dont les requêtes durent 8 à 24 ms est théorique. À rouvrir seulement
si P3 montre que le threadpool est le facteur limitant.

### P1.2 — Rendre la session base à la fin de l'authentification WebSocket (F2)

- [x] Les quatre canaux authentifiés déclarent `db: Session = Depends(get_db)`
      et gardent la connexion ouverte pour toute la durée de vie de la socket —
      des heures. Trois d'entre eux ne s'en resservent jamais. Authentifier,
      extraire ce qui est nécessaire, **fermer la session**, puis entrer dans la
      boucle de pompage. Rouvrir une session courte à la demande pour les
      mutations du panier de table (`/ws/table`), seul canal qui écrit ensuite.
      **Mesuré après correction : 500/500 WebSockets simultanées en 2,1 s,
      `/health` à 4 ms, et 2 connexions Postgres au total (zéro
      `idle in transaction`)** — contre 14 sockets et une API injoignable
      avant. `Depends(get_db)` conservé à dessein : c'est le point d'injection
      que `conftest.py` surcharge (PR #200)
      *Fichier : `app/modules/notifications/router.py`*

Le canal `/ws/menu` est déjà correct (aucune session déclarée) : c'est le
modèle à suivre.

### P1.3 — Dimensionner le pool explicitement (F3)

- [x] `create_engine()` n'a ni `pool_size`, ni `max_overflow`, ni `pool_timeout`,
      ni `pool_recycle` : les défauts SQLAlchemy (5 + 10, 30 s) sont devenus le
      plafond de capacité du produit entier. Poser des valeurs explicites, avec
      un **`pool_timeout` court** (5 s plutôt que 30) : mieux vaut un 503 franc
      qu'une requête qui pend une demi-minute. Valeurs **configurables par
      environnement** (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`,
      `DB_POOL_RECYCLE`) plutôt qu'en dur : le bon dimensionnement dépend du
      plan Postgres et du nombre d'instances, qui changeront en §P3.1 (PR #200)
      *Fichier : `app/core/database.py`*

⚠️ **Ne corrige rien seul.** Mesuré : porter le pool de 15 à 50 ne change pas le
débit (105,7 → 105,7 req/s à concurrence 10). C'est le troisième pied du
trépied, pas un raccourci — sans P1.1 et P1.2, cette tâche n'achète qu'un
meilleur mode de panne.

### P1.4 — Fermer la course de règlement de paiement (F6)

- [x] La mise à jour dite « idempotente » filtre sur `id` et `payment_ref`, deux
      valeurs qui ne changent pas au règlement, mais **pas sur le statut**. Deux
      appelants concurrents (webhook + retour navigateur) obtiennent chacun
      `rowcount = 1` et rejouent tous deux `_after_share_paid`. Ajouter
      `OrderPayment.status == OrderPaymentStatus.PENDING` au filtre du
      `.update()` — c'est alors PostgreSQL qui arbitre, le perdant voit
      `rowcount = 0` et n'entre pas dans `_after_share_paid`.
      **Vérifié dans les deux sens** : le test de course échoue sur le code
      d'avant (`compteur de fidélité à 2`), passe après — `order_count = 1`,
      facture `F2026-00001`, compteur à 1, une seule part PAID. Témoin
      séquentiel (webhook puis page de retour une seconde plus tard) conservé :
      un rejeu légitime doit continuer de ne rien casser (PR #202)
      *Fichiers : `app/modules/orders/service.py`,
      `tests/test_reglement_concurrent.py`*

Reproduit en conditions réelles : compteur de fidélité à 2 au lieu de 1, e-mail
et PDF envoyés deux fois, et facture `F2026-00002` — **le numéro `F2026-00001`
consommé et rattaché à aucune facture**. C'est un trou dans la séquence
continue, précisément l'invariant que `core/invoice_number.py` existe pour
garantir. Ce n'est **pas** un double débit : le prestataire n'a encaissé qu'une
fois.

### P1.5 — Sortir les appels réseau de la boucle d'événements (F7)

- [x] `pywebpush` est appelé **à chaque création de commande**, une fois par
      membre du staff abonné, sans timeout : le défaut de la librairie vaut
      `10000`, interprété par `requests` comme **10 000 secondes**. Deux bornes
      posées : `DELAI_PUSH_SECONDES = 5` par envoi, et
      `BUDGET_PUSH_EQUIPE_SECONDES = 15` pour toute l'équipe — sans ce second
      plafond, le premier se multiplie par la taille de la brigade. Vérifié
      dans les deux sens : le test échoue sans le `timeout=` (`[None] == [5]`),
      passe avec (PR #206)
      *Fichiers : `app/core/push.py`, `app/modules/staff/service.py`*
- [x] Appels `httpx` vers le prestataire de paiement et Resend : ils portaient
      **déjà** un `timeout=15` explicite, et **§P1.1 les avait déjà sortis de
      la boucle d'événements** en faisant tourner les fonctions de service dans
      un thread. Rien à corriger donc — mais le critère de validation, lui,
      n'avait jamais été vérifié : il l'est désormais par un test (un envoi qui
      traîne pendant qu'une requête ordinaire passe en < 2 s), plus un
      garde-fou de lecture qui échoue si un appel `httpx` repart un jour sans
      `timeout` (PR #206)
      *Fichier : `tests/test_appels_reseau_lents.py`*

`run_in_threadpool` suffit à ce palier. Une vraie file d'attente est en P3.

### P1.6 — Rejeu concurrent et refus WebSocket (F11, F12)

- [x] Le contrôle de rejeu d'une commande est un `SELECT` suivi d'un `INSERT`
      sans verrou : deux rejeux simultanés du même `client_order_id` passent
      tous deux le `SELECT`, et le second heurte la contrainte d'unicité —
      `IntegrityError` non rattrapée, **500** au lieu de la réponse idempotente.
      Rattrapé sur les deux chemins de création (commande directe et panier de
      table), même motif que `core/invoice_number.py`. Vérifié dans les deux
      sens : le test échoue avant (`UniqueViolation` remontée au client), passe
      après — une seule commande en base, un seul `public_token` rendu aux deux
      appelants (PR #207)
      *Piège rencontré : l'identifiant de table doit être lu AVANT le `try`.
      Une session dont le flush a échoué refuse tout accès ORM, et `table.id`
      dans le `except` levait un `PendingRollbackError` qui masquait
      l'`IntegrityError` qu'on voulait traiter.*
      *Fichier : `app/modules/orders/service.py`*
- [x] ⚠️ **La prémisse de cette tâche était fausse, mesuré le 2026-09-10.**
      L'audit supposait que « pool saturé = authentification en échec = 4401 ».
      Vérifié sur un vrai `uvicorn`, base réellement arrêtée : une base
      injoignable fait échouer la **poignée de main au niveau HTTP** (le
      navigateur rapporte 1006, que le hook réessaie déjà avec backoff), et
      n'émet **jamais** 4401. Ce dernier ne sort que de `_reject`, appelé
      uniquement sur un vrai défaut d'autorisation. Rien à corriger, donc — et
      surtout pas un second code de fermeture que rien ne pourrait émettre.
      La bonne propriété tient toutefois par construction (l'erreur base
      survient avant le `accept()`) et non par intention : quatre tests la
      verrouillent désormais, pour qu'un remaniement de l'authentification ne
      la renverse pas silencieusement (PR #207)
      *Fichier : `tests/test_refus_websocket.py`*

### P1.7 — Voir les pannes (F5) — absorbe `ROADMAP.md` Phase 20

- [ ] Activer les sauvegardes automatiques du Postgres managé 🧑
- [ ] **Restaurer une sauvegarde une fois, sur une base jetable** 🧑 — reprise
      telle quelle de `ROADMAP.md:202`, qui l'appelle déjà « la seule ligne de
      cette phase qu'on sera tenté de sauter, et la seule qui prouve les
      autres ». Elle reste vraie, et elle reste non faite.
- [ ] Brancher un moniteur externe sur `/health` 🧑 — la sonde est écrite,
      correcte (elle interroge réellement la base et renvoie 503), et
      **personne ne l'interroge**.
- [ ] Collecte des erreurs 🧑 — log drain de l'hébergeur ou Sentry. Les logs
      sortent déjà en JSON structuré avec le contexte métier : il manque
      uniquement une destination.
- [x] **Exposer les connexions du pool en métrique** — `engine.pool.checkedout()`
      et le nombre de connexions `idle in transaction`, avec une alerte au-delà
      de 70 %. C'est le signal avancé unique de F1, F2 et F3 : les cinq
      effondrements provoqués pendant l'audit auraient tous été annoncés par
      cette seule courbe, plusieurs secondes avant la panne (PR #209)
      *Fichiers : `app/core/pool_metrics.py` (mesure + seuil + journalisation),
      `app/main.py` (greffe sur `/health`),
      `app/modules/platform_admin/router.py` (`GET /api/v1/platform-admin/pool`),
      `tests/test_metrique_pool.py`*

  **Trois décisions**, pour que la suite ne les redécouvre pas :

  1. **Greffée sur `/health`, sans ordonnanceur.** C'est la seule route que
     quelque chose appelle à intervalle régulier — donc la seule qui donne une
     **courbe** plutôt qu'un instantané, et une saturation de pool ne se voit
     que sur une courbe. La réponse de `/health` ne bouge pas d'un caractère
     (`{"status": "ok"}`) : un moniteur externe déclenche dessus.
  2. **L'alerte est un log WARNING `pool.sature`, pas un appel réseau.** La
     destination, c'est le log drain de la ligne « Collecte des erreurs »
     ci-dessus. Appeler soi-même un service d'alerte, ce serait un service
     payant de plus **et** une dépendance réseau dans le chemin de `/health` —
     les deux sont exclus. `log_event()` accepte désormais un `level`
     (INFO par défaut) : sans lui, une alerte est noyée dans le flux normal.
  3. **Les chiffres se lisent sous le JWT admin plateforme**, jamais en public :
     capacité et connexions ouvertes disent à un attaquant combien de requêtes
     concurrentes suffisent à saturer le service.

  **Deux défauts trouvés par leurs propres tests, et corrigés :**

  - `/health` répondait **500** quand la mesure levait — c'est-à-dire une
    fausse alerte de panne provoquée par l'outil censé les prévenir. La mesure
    est désormais enveloppée : commodité d'un côté, contrat de l'autre.
  - PostgreSQL met `pg_stat_activity` **en cache pour toute la durée de la
    transaction** : deux lectures successives dans la même transaction rendent
    le même chiffre, même si dix connexions se sont bloquées entre les deux.
    En production la session de `/health` est neuve à chaque requête, donc le
    piège reste invisible — mais il rendait aveugle tout appelant qui mesure en
    boucle, exactement l'usage que cette métrique appelle.
    `SELECT pg_stat_clear_snapshot()` avant chaque comptage.

### P1.8 — Dépendances (F10)

- [x] Monter PyJWT (7 avis — c'est la bibliothèque qui valide toute
      l'authentification du personnel), Starlette + FastAPI, python-multipart,
      python-dotenv, et Next.js (avis **RCE critique** sur l'API d'optimisation
      d'images). Mesuré avant/après : `pip-audit` passe de **42 avis sur 4
      paquets à 0**, `npm audit` de **1 critique + 1 haut à 0** (PR #208)
      *Versions : `fastapi` 0.115.0 → 0.141.1 (qui tire `starlette` 0.38.6 →
      1.6.0), `pyjwt` 2.9.0 → 2.13.0, `python-multipart` 0.0.12 → 0.0.32,
      `python-dotenv` 1.0.1 → 1.2.3, `next` 14.2.35 → 15.5.25.*
- [x] **Ajouter `pip-audit` et `npm audit` à la CI** — c'est le correctif
      durable. Les 42 avis étaient invisibles pour l'équipe faute de scan.
      Bloquants tous les deux (PR #208)
      *Fichiers : `backend/requirements.txt`, `backend/requirements-dev.txt`,
      `frontend/package.json`, `.github/workflows/ci.yml`*
      *Validation : 813 tests toujours verts, les deux scans propres.*

**Trois décisions prises pendant la montée, à ne pas redécouvrir plus tard :**

1. **Next 15.5.25 et non Next 16.** Les deux avis critiques (exécution de code
   à distance sur l'API d'optimisation d'images, et sur un hôte Windows) sont
   corrigés en **15.5.24** : `npm audit fix --force` proposait 16.3.4 parce que
   c'est la dernière version, pas parce qu'il la faut. Une seule version
   majeure franchie au lieu de deux, sur un frontend sans test de bout en bout.
2. **`overrides: { postcss }`** dans `frontend/package.json` : Next 15 embarque
   `postcss` 8.4.31, visé par quatre avis. Ils sont tous **au moment du build**
   (lecture d'un `.map` désigné par un commentaire CSS) et Tawla ne compile que
   son propre CSS — l'exposition réelle est nulle. L'`override` les ferme quand
   même, parce que le critère de sortie est « scan propre » : une porte avec une
   exception permanente n'est plus une porte. À retirer le jour où on passe à
   Next 16, qui embarque un `postcss` corrigé.
3. **Portée des deux scans.** `pip-audit -r requirements.txt` (et non
   l'environnement installé) et `npm audit --omit=dev --audit-level=high` : on
   bloque sur ce qui **part en production**. Un avis sur eslint ou vitest
   n'atteint aucun client, et un avis modéré sur une dépendance de build ne doit
   pas empêcher un correctif urgent — une porte qu'on apprend à contourner ne
   protège plus rien.

⚠️ **Piège rencontré, et le seul vrai changement de code de cette tâche.**
Starlette 1.x réécrit son `TestClient` : hors `with`, chaque
`websocket_connect` ouvre **son propre portail**, donc sa propre boucle
d'événements dans son propre thread, et les files de la session — autrefois des
`queue.Queue` thread-safe — sont désormais des flux anyio liés à cette boucle.
Un `broadcast` déclenché par le socket B ne réveille alors jamais le socket A
s'il attend déjà : `test_table_cart.py` se figeait **pour toujours** sur
`ws_a.receive_json()` (diagnostiqué à la pile, `py-spy dump`, la suite étant
muette). La correction tient en une ligne de `tests/conftest.py` — la fixture
`client` entre enfin dans le contexte du `TestClient`, ce qui donne un portail
unique à toutes les sessions, comme un processus uvicorn réel n'a qu'une
boucle. Le commentaire qui refusait ce `with` invoquait le `create_all()` du
lifespan : celui-ci a disparu à la Phase 12.2, le commentaire était périmé.

Côté produit, une seule adaptation : `params` est une `Promise` depuis Next 15,
y compris dans un composant client. `app/menu/[qrToken]/page.tsx` lit désormais
le segment avec `useParams()` — la valeur directement, sans `use()` à dérouler.
À noter, `npx tsc --noEmit` **ne voit pas** cette erreur (elle vient des types
générés par Next) : c'est `npm run build` qui l'attrape, d'où son intérêt en CI.

### P1.9 — Le test qui empêche la rechute

- [x] Test de charge de non-régression en CI (niveau **N0**) : 40 requêtes
      simultanées sur `POST /orders` contre un vrai `uvicorn` et un vrai
      PostgreSQL, plus un témoin sur un endpoint `def` — si le témoin se met à
      échouer, c'est qu'on a cassé le monde qui marchait.
      **Deux faux négatifs rencontrés en l'écrivant, tous deux documentés dans
      la docstring du test** : `TestClient` sérialise les requêtes derrière son
      portail, et 40 threads clients sont étalés par le GIL — les deux
      donnaient un test vert des DEUX côtés de la correction, donc sans
      valeur. Il faut `asyncio.gather` sur un client async.
      Vérifié dans les deux sens : échoue sur le code d'avant (`0/40`,
      `ReadTimeout`), passe après (PR #201)
      *Fichier : `tests/test_concurrence_commandes.py`*

⚠️ `backend/tests/test_service_load.py` porte le nom de test de charge mais joue
200 commandes **séquentielles** sur SQLite en mémoire, dans un seul thread : il
vérifie qu'une requête ne dégénère pas avec le volume — utile, à garder — mais
il ne teste ni concurrence, ni WebSockets, ni Postgres, ni le pool.

**Critère de sortie de P1** : la rafale de 40 commandes simultanées passe
40/40, le serveur est sain juste après, 500 WebSockets tiennent sans connexion
`idle in transaction`, une sauvegarde a été restaurée pour de vrai, et une
alerte est arrivée lors d'un arrêt volontaire.

---

## Palier P2 — Multi-restaurants

Objectif : plusieurs instances backend possibles, et le produit qui tient une
vingtaine de restaurants. **P2 est la condition d'existence de P3** : sans
plusieurs instances, aucun réglage ne fait passer 100 restaurants.

### P2.1 — Sortir l'état partagé de la mémoire du processus (F4, F17)

- [x] Aujourd'hui, le registre WebSocket, le panier de table, le roster des
      convives, le mode de partage et le limiteur de débit vivent dans des
      dicts de module. Deux instances ne se voient pas : une commande passée
      sur l'instance A n'apparaît jamais sur l'écran cuisine connecté à
      l'instance B. La contrainte « une seule instance backend » est explicite
      dans `ROADMAP.md:191` — c'est elle qui tombe ici (PR #210)
      **Mesuré, deux vrais `uvicorn` derrière le même Postgres et le même
      Redis** : la commande passée sur A arrive sur l'écran connecté à B, le
      panier de table est le même des deux côtés, et le limiteur de débit
      refuse bien au 21ᵉ appel réparti moitié-moitié sur les deux.
      *Fichiers : `app/core/etat_partage.py` (neuf),
      `app/modules/notifications/manager.py`, `app/modules/orders/table_cart.py`,
      `app/modules/tables/roster.py`, `app/modules/tables/split_mode.py`,
      `app/core/rate_limit.py`, `app/main.py` (écoute de fond),
      `docs/adr/0007-etat-partage-redis-optionnel.md`*
      *Tests : `tests/test_etat_partage.py` (contrat, joué à l'identique sur
      les DEUX implémentations), `tests/test_deux_instances.py` (validation
      bout en bout + son témoin).*

**Trois décisions, pour que la suite ne les rejoue pas :**

1. **Un magasin unique** (`core/etat_partage.py::magasin`) plutôt que cinq
   portages séparés. Les cinq usages ont besoin des mêmes trois primitives ;
   les écrire cinq fois, c'est cinq occasions de diverger.
2. **Redis optionnel, mémoire par défaut.** Sans `REDIS_URL`, rien ne change :
   aucune dépendance, aucun service à payer, rien à lancer pour `pytest -q`.
   C'est ce qui permet à un pilote à un restaurant de ne pas payer un Redis
   managé — que `AUDIT_COUTS_PRODUCTION.md` ne budgète d'ailleurs pas, 🧑 à
   trancher avant P2.5.
3. **Champs nommés, pas un blob JSON par table.** Deux téléphones qui ajoutent
   un plat au même instant écrivent deux clés différentes ; avec un blob, le
   second `lire → modifier → écrire` écrase le premier et **un plat disparaît
   de la commande**. `HSET` conserve l'atomicité par ligne que le dict Python
   donnait gratuitement.

⚠️ **Deux propriétés qu'un hash Redis ne donne pas et qu'il a fallu
reconstruire** — les deux étaient gratuites avec un dict Python, donc invisibles
jusqu'à ce qu'un test les réclame : **l'ordre d'insertion** (le roster affiche
les convives dans l'ordre où chacun a rejoint) et **le vider-et-lire atomique**
(sans lui, deux appareils qui valident au même instant facturent la table deux
fois). `MagasinRedis` range un rang devant chaque valeur pour la première, et
passe par `MULTI/EXEC` pour la seconde.

**Le témoin compte autant que les trois tests de validation**
(`test_temoin_sans_magasin_partage_la_commande_reste_sur_son_instance`) : les
deux mêmes instances démarrées **sans `REDIS_URL`** ne doivent PAS se voir. Sans
lui, rien ne prouverait que les trois autres mesurent quoi que ce soit — c'est
le faux négatif qui a coûté deux réécritures à `test_concurrence_commandes.py`.

Effet de bord obtenu, comme prévu : avec Redis branché, **un déploiement ne
vide plus les paniers des clients attablés**.

### P2.2 — Photos hors de la base (F8)

- [ ] Les photos de plats sont des `LargeBinary` **dans Postgres** (3 Mo max
      chacune), servies par le processus applicatif : jusqu'à 120 Mo par
      restaurant dans un plan *Basic-256mb*, répliqués dans chaque sauvegarde,
      et chaque premier chargement client traverse le backend et son pool.
      Migrer vers un stockage objet + CDN. Le choix d'origine était assumé face
      aux disques éphémères de Render/Railway ; il ne tient plus à 100
      restaurants, et `ROADMAP.md:176` le prévoyait déjà.
      *Fichiers : `app/modules/menu/models.py:86`, `app/modules/menu/router.py:305,347`*

L'atténuation actuelle est bonne et à conserver : l'URL porte l'empreinte du
contenu, donc `Cache-Control: immutable` est sûr et Cloudflare absorbe les vues
répétées.

⛔ **Bloqué sur toi — deux documents de ce dépôt se contredisent, et je ne
tranche pas seul** (relevé le 2026-09-11, en abordant la tâche).

`AUDIT_COUTS_PRODUCTION.md` §4.4 a **déjà** instruit ce point, chiffres à
l'appui, et conclu l'inverse : à 45 établissements comme à 450, les photos en
`LargeBinary` coûtent **quelques dinars par mois** et ne forcent aucune mise à
niveau de palier Postgres. Il met R2 en regard « **sans recommandation de
migrer maintenant** — YAGNI, comme déjà tranché ».

Les deux documents ne répondent pas à la même question, et c'est ce qui les
rend tous les deux défendables :

- l'audit des coûts mesure **l'argent** : verdict, ça ne coûte rien ;
- P2.2 mesure **la ressource rare** que P1 vient de protéger : chaque
  chargement d'image qui atteint l'origine occupe un thread et une connexion
  du pool pendant le transfert de 150-300 Ko.

**Mais l'atténuation en place affaiblit fortement le second argument** :
l'URL portant l'empreinte du contenu, Cloudflare ne redemande l'image à
l'origine qu'au défaut de cache, pas une fois par client. Le débit réel qui
atteint l'origine pendant un service n'est **pas mesuré** — et c'est
exactement ce que la campagne de charge P3.5 révélera.

**Ma recommandation** : laisser P2.2 ouverte et **conditionnée à cette
mesure**, plutôt que de migrer maintenant. Migrer ajoute un service payant,
une clé d'API et un point de défaillance pour un problème dont on n'a, à ce
jour, la preuve ni qu'il coûte de l'argent, ni qu'il consomme le pool.
Déclencheur proposé : *si la campagne P3.5 montre que les requêtes d'image
atteignant l'origine dépassent quelques pour cent du trafic backend, migrer
vers R2*. Sinon, ne rien faire.

### P2.3 — Index du chemin le plus chaud (F13)

- [x] `orders` n'a qu'un index sur `restaurant_id`, alors que l'écran serveur et
      l'écran cuisine filtrent sur `(restaurant_id, status, created_at)` à
      chaque montage et à chaque reconnexion. Invisible aujourd'hui ; à ~73 000
      commandes par an et par restaurant, chaque montage d'écran devient un
      balayage complet de l'historique. Index composite
      `(restaurant_id, created_at)` — une migration (PR #211)
      **Mesuré sur 73 000 commandes/an/restaurant, trois restaurants en base :**

      | | avant | après |
      | --- | --- | --- |
      | plan | Index Scan (`restaurant_id`) **+ Sort** | Index Scan (`restaurant_id, created_at`) |
      | `Rows Removed by Filter` | **72 929** | **28** |
      | buffers | 813 | 5 |
      | temps | **8,611 ms** | **0,092 ms** |

      *Fichiers : `app/modules/orders/models.py`,
      `alembic/versions/d64562dcc42c_*.py`, `tests/test_plan_ecran_service.py`*

**Trois points qui valaient d'être écrits :**

1. **L'ordre des colonnes n'est pas indifférent** — égalité (`restaurant_id`)
   d'abord, plage (`created_at`) ensuite. Il fait aussi **disparaître le nœud
   `Sort`** : l'index rend déjà les lignes triées par `created_at`, ce que
   demande précisément le `ORDER BY`.
2. **`status` n'est volontairement pas dans l'index.** Une fois la plage de
   dates appliquée, il ne reste qu'une journée de service à filtrer (28 lignes
   écartées). Une troisième colonne alourdirait chaque écriture pour ne rien
   gagner à la lecture.
3. **`CREATE INDEX` simple, pas `CONCURRENTLY`** — une migration ne s'applique
   qu'une fois, maintenant, sur une table de quelques milliers de lignes ; les
   73 000 lignes/an sont l'état futur, celui où l'index existera déjà.
   `CONCURRENTLY` protégerait d'un scénario impossible ici, au prix d'une
   branche par dialecte (la suite rejoue les migrations sur SQLite) et d'un
   risque d'index INVALID. **Indexer une table déjà volumineuse en production,
   elle, exigera `CONCURRENTLY`** : la règle est écrite dans la migration.

⚠️ **Le test de plan est le garde-fou, et il fallait qu'il le soit vraiment.**
Un index peut être « utilisé » tout en laissant Postgres relire l'année
entière — c'est exactement ce que faisait l'index sur `restaurant_id` seul.
Le test vérifie donc que `created_at` est dans l'**`Index Cond`** et non dans
le `Filter`. Vérifié dans les deux sens, au volume du test (6 000 lignes) :
sans l'index composite, `Rows Removed by Filter` vaut **6 000** et un nœud
`Sort` réapparaît — les deux assertions tombent.

### P2.4 — Jeton WebSocket de courte durée (F9)

- [x] Le JWT du personnel n'a pas de claim `exp` (choix produit assumé du
      2026-09-09 : ne pas éjecter un serveur en plein service) et transite en
      **query string** dans l'URL WebSocket — contrainte navigateur réelle, mais
      les URLs sont journalisées par Cloudflare et l'hébergeur. Un jeton
      éternel retrouvé dans un log d'accès reste valide indéfiniment.
      Conserver l'intention produit sans le risque : un jeton WebSocket court et
      à usage unique, échangé via une route authentifiée, pour que le JWT long
      ne quitte jamais l'en-tête `Authorization` (PR #212)
      *Fichiers : `app/modules/staff/ws_tickets.py` (neuf),
      `app/modules/staff/router.py` (`POST /api/v1/auth/ws-ticket`),
      `app/modules/notifications/dependencies.py`, `notifications/router.py`,
      `frontend/lib/api.ts`, `frontend/lib/useReconnectingSocket.ts`,
      `frontend/app/{staff,kitchen}/page.tsx`*
      *Tests : `tests/test_billet_websocket.py` (9), plus tous les tests de
      canal existants passés au billet.*

**L'intention produit est intacte** : ce n'est **pas** la session du serveur en
salle qui devient courte — elle ne change pas d'un iota, le bouton « Se
déconnecter » reste la seule déconnexion. C'est le **jeton de transport** qui
devient jetable. Billet opaque, **30 secondes**, **une seule connexion**.

**Deux gardes, parce qu'elles couvrent deux fuites différentes :** l'usage
unique contre le billet lu dans un log *avant* sa péremption ; la durée courte
contre le billet demandé puis jamais utilisé, qui resterait sinon éternel — on
aurait remplacé un jeton immortel par un autre.

Le billet dit **qui**, jamais **à quoi on a droit** : le socket relit ensuite le
rôle et le restaurant en base, exactement comme avant. Un billet de cuisine
n'ouvre pas plus l'écran serveur que le JWT ne le permettait (S-4 inchangé).

Stocké dans `core/etat_partage.py::magasin` — et c'est P2.1 qui rend la chose
possible : le billet est délivré par l'instance qui sert la requête HTTP et
consommé par celle qui reçoit la WebSocket, sans garantie que ce soit la même.
`test_deux_instances.py` en fait la preuve gratuitement : il demande le billet
à A et le présente à B.

⚠️ **Le vrai risque n'était pas la sécurité, c'était la reconnexion.** Un billet
à usage unique la rend fragile par construction : une URL calculée une fois ne
sert qu'une fois, et l'écran ne reviendrait **jamais** après une coupure — panne
d'autant plus vicieuse qu'elle ne se déclencherait qu'au pire moment.
`useReconnectingSocket` prend donc désormais une **fabrique d'URL** appelée
avant chaque tentative, et non une URL figée ; `cle` (l'identifiant du canal)
est seule en dépendance de l'effet, sinon la socket se rebrancherait à chaque
rendu.

**Vérifié pour de vrai, navigateur réel, en coupant le backend :** écran passé
à « Déconnecté », puis « Connecté » au redémarrage, avec la trace
`WS fermée → POST ws-ticket ×4 → WS ouverte` — un billet neuf à chaque
tentative. *Une première version de ce test ne prouvait rien (la coupure
simulée ne fermait pas la socket, `0 nouvel échange`) : il a fallu arrêter le
processus backend.*

**Rupture de contrat assumée, sans transition** : l'ancien `?token=<JWT>` n'est
plus accepté du tout — un test le verrouille. Accepter les deux le temps d'une
version aurait laissé la faille ouverte et la suppression se serait oubliée. Le
coût est un déploiement coordonné backend+frontend, et il est nul aujourd'hui :
la Phase 20 n'a pas commencé, il n'y a aucun utilisateur en ligne.

### P2.5 — Staging et retour arrière (F19)

- [ ] Un environnement de staging avec une copie de la base 🧑 — il n'y en a pas
      aujourd'hui, et `ROADMAP.md` prévoit un rejeu complet du parcours dessus.
- [x] Tester `downgrade` en CI. Le constat de l'audit était en fait à moitié
      faux, et la moitié fausse cachait le défaut : les `downgrade` **étaient**
      exercés (`test_every_migration_can_be_rolled_back`, PR #43), mais sur
      SQLite. Or sur Postgres, `DROP TABLE` ne supprime pas le type enum nommé
      créé pour la colonne — SQLite, lui, rend un VARCHAR + CHECK et n'a donc
      rien à laisser derrière. **Vérifié sur un vrai Postgres : `downgrade base`
      laissait six types (`staffrole`, `orderstatus`, `paymentmethod`,
      `paymentstatus`, `modificationrequeststatus`, `modificationlinestatus`) et
      la remontée mourait aussitôt sur « type staffrole already exists ».** Le
      retour arrière était donc à sens unique depuis la migration initiale,
      c'est-à-dire qu'il n'existait pas. Le piège avait déjà été rencontré deux
      fois et corrigé migration par migration (`c2e7b41f8a90`, `55a307a3bc86`)
      sans jamais être gardé. Les deux migrations fautives suppriment désormais
      leurs types, et le round-trip tourne sur le moteur de la production
      (`TEST_DATABASE_URL`, service Postgres déjà en CI) avec une assertion qui
      nomme les types survivants plutôt que de laisser un « already exists »
      surgir des dizaines de révisions plus loin. (PR #216)

### P2.6 — Démo hors du chemin de requête (F14)

- [ ] Chaque clic sur « Voir la démo » crée un restaurant complet avec deux
      semaines d'historique — **218 commandes et 604 lignes mesurées, en 1,4 s**
      sur 4 vCPU (donc bien plus sur 0,5 CPU), en tenant une connexion du pool.
      C'est la seule route publique qui écrit en base. Les garde-fous existants
      sont bons (3/min/IP, plafond dur `PLAFOND_DEMOS`, purge à chaque
      création) mais aucun ne borne la **concurrence**. Pré-générer un vivier
      d'établissements de démonstration, ou créer la démo hors requête.

**Critère de sortie de P2** : deux instances servent le même restaurant sans
que personne ne s'en aperçoive, un déploiement ne perd plus un seul panier, et
le niveau N1 (10 restaurants / 500 clients) passe 30 minutes sans dégradation.

---

## Palier P3 — Tenir 5 000

C'est le palier que l'audit **n'a pas pu chiffrer** et qui reste à démontrer.
Tout ce qui suit repose sur des estimations explicitement marquées comme telles.

### P3.1 — Dimensionner la flotte 🧑

- [ ] **Compter les WebSockets, pas les clients.** Chaque client ouvre **2 à 3
      sockets** (`/ws/menu`, `/ws/table`, puis `/ws/order` après commande) —
      vérifié dans `frontend/app/menu/[qrToken]/page.tsx:879,943,979`. La cible
      n'est donc pas 5 000 connexions mais **≈ 13 000**, plus ~300 écrans staff.
- [ ] **Dimensionner à partir de la mesure** : 37,5 Ko par WebSocket, linéaire
      et vérifié jusqu'à 3 000 connexions sur un processus (`/health` toujours
      à 7 ms). 13 000 × 37,5 Ko + 158 Mo de base ≈ **634 Mo pour un seul
      processus** — au-dessus des 512 Mo du plan Render Starter visé par
      `AUDIT_COUTS_PRODUCTION.md`.
      Estimation de départ, **à confirmer par P3.5** : **4 à 6 instances**.
- [ ] Choisir le plan d'hébergement en conséquence 🧑. `AUDIT_COUTS_PRODUCTION.md`
      chiffre Render Starter (0,5 CPU / 512 Mo) et Postgres *Basic-256mb* : ni
      l'un ni l'autre n'est un plan pour 5 000 clients. Ce chantier a un coût
      d'infrastructure à réévaluer, et c'est une décision de Wassim.

### P3.2 — PgBouncer 🧑

- [ ] Avec N instances, `N × pool_size` doit rester sous le plafond de
      connexions du plan Postgres — de l'ordre d'une centaine sur
      *Basic-256mb*. Cinq instances à pool 20 y sont déjà. Un pooling
      transactionnel (PgBouncer, ou l'équivalent managé) devient nécessaire, et
      il impose ses propres contraintes : pas de `SET` de session, attention
      aux transactions longues.
      *À vérifier au passage : `with_for_update()` de `core/invoice_number.py`
      reste correct en mode transaction — il l'est, la transaction est courte,
      mais c'est à confirmer plutôt qu'à supposer.*

### P3.3 — Le débit, qui ne vient pas du pool

- [ ] **Mesuré : porter le pool de 15 à 50 ne change pas le débit** (105,7 →
      105,7 req/s à concurrence 10 ; ~95 req/s à concurrence 50). Le plafond de
      ~100 req/s est celui d'**un processus Python** sur 4 vCPU — GIL et
      threadpool de 40 — pas celui de la base. Il ne se lève qu'en ajoutant des
      processus, donc par P2.1.
- [ ] Charge de fond à réduire avant d'ajouter des instances (F18) : l'écran
      serveur interroge le plan de salle toutes les 20 s
      (`frontend/app/staff/page.tsx:410`). À 100 restaurants × ~3 écrans, c'est
      **15 req/s en permanence**, avant le premier client — environ 15 % du
      débit d'une instance. Diffuser les changements de plan sur le canal
      `staff` déjà ouvert plutôt que d'interroger.

### P3.4 — Une vraie file d'attente

- [ ] P1.5 sort les envois du chemin de requête vers un threadpool : c'est un
      dépannage correct pour un pilote. À 100 restaurants, le fan-out push par
      commande (une notification par membre du staff abonné, à chaque commande)
      devient un volume réel, avec des échecs à réessayer et des abonnements
      expirés à purger. Le projet n'a **aucune** file aujourd'hui — ni Celery,
      ni RQ, ni même `BackgroundTasks`.
      *À instruire avec la philosophie du projet : mesurer d'abord. Si les
      chiffres de P3.5 montrent que le threadpool tient, ne rien ajouter.*

### P3.5 — La campagne de charge qui clôt le chantier

Aucune de ces tâches n'est un test unitaire : elles se tirent sur
**l'hébergement réel**, pas sur un poste de développement.

- [ ] **N1 — 10 restaurants / 500 clients** : 500 WebSockets tenues 30 minutes,
      commandes, transitions, paiements. Connexions du pool stables et non
      croissantes.
- [ ] **N2 — 50 restaurants / 2 500 clients** : idem, plus un pic de service —
      30 % des commandes concentrées sur 10 minutes.
- [ ] **N3 — 100 restaurants / 5 000 clients** : la cible.
- [ ] **Test de rupture** : au-delà de la cible, jusqu'à l'échec. Le but n'est
      pas le chiffre mais le **comportement** : vérifier que la défaillance
      dégrade (429/503 puis récupération) au lieu de se verrouiller.

Chaque niveau couvre le parcours entier : connexion staff, scan QR, carte,
panier partagé multi-appareils, commande, prise en charge serveur, envoi
cuisine, transitions, paiement par personne, webhook, facture.

Trois métriques à instrumenter pendant les tirs — sans elles, un test de charge
dit seulement « ça a cassé », jamais pourquoi : **connexions du pool en cours**,
**connexions `idle in transaction`**, et **retard de la boucle d'événements**.

**Critère de sortie de P3** : N3 passe sur l'infrastructure de production, avec
les trois métriques ci-dessus stables pendant toute la durée du tir. Tant que ce
tir n'a pas eu lieu, la formulation honnête reste : *architecture probablement
capable, capacité non démontrée*.

---

## Annexe A — Mesures de référence (2026-09-10)

Toutes obtenues sur le code du dépôt **non modifié**, contre PostgreSQL 16 réel
et uvicorn lancé comme en production.

⚠️ **Matériel : 4 vCPU / 16 Go.** La cible documentée est Render Starter,
**0,5 CPU / 512 Mo**. Tous ces plafonds sont des **bornes hautes optimistes** :
la production fera moins, pas plus. Les rejouer sur l'infra réelle fait partie
de P3.5.

| Mesure | Valeur | Contexte |
| --- | --- | --- |
| Rafale 40 sur endpoint `async def` | **1/40 OK, serveur mort** | `POST /orders`, aucune récupération |
| Rafale 40 sur endpoint `def` | 40/40 OK en 0,6 s | `GET /menu-items/by-table`, serveur sain |
| Plafond WebSocket (code actuel) | **14** | tous restaurants confondus |
| Pool de connexions | 5 + 10 = 15 | défaut SQLAlchemy jamais surchargé |
| Débit lecture carte, pool 15 | ~100 req/s | plateau de concurrence 10 à 50 |
| Débit lecture carte, pool 50 | **~100 req/s** | inchangé — le pool n'est pas le plafond |
| Effondrement lecture carte | concurrence ≥ 100 | 520 × `QueuePool limit` dans les logs |
| Mémoire par WebSocket | **37,5 Ko** | linéaire, vérifié jusqu'à 3 000 |
| 3 000 WS sur un processus | RSS 267,9 Mo, `/health` 7 ms | canal sans session DB |
| Extrapolation 13 000 WS | ≈ 634 Mo (un processus) | > 512 Mo du plan visé |
| Sockets par client | **2 à 3** | `menu` + `table` + `order` |
| Charge de fond staff | 15 req/s | 100 restos × 3 écrans, polling 20 s |
| Latence écran serveur | 8 ms | sur 653 commandes, 1 812 lignes |
| Latence cuisine terminées | 24 ms | idem |
| Latence dashboard manager | 15 ms | idem |
| Génération PDF facture | 2,1 ms / 1,9 Ko | **non problématique** |
| Création session démo | 1,4 s | 218 commandes + 604 lignes écrites |
| Suite de tests | 789 verts, 5 min 09 s | — |
| Sondes IDOR cross-tenant | **21/21 bloquées** | — |
| Avis de sécurité connus | 41 (Python) + 2 (npm) | 4 paquets, dont PyJWT et Next.js |

## Annexe B — Ce que l'audit a trouvé sain (à ne pas casser)

Ces propriétés sont vérifiées aujourd'hui. Toute PR de ce chantier doit les
laisser vraies — et le dire dans sa description.

- **Isolation multi-tenant étanche.** 21 sondes IDOR, 0 accès réussi. Le client
  n'envoie jamais de `restaurant_id` (déduit du `qr_token`), chaque route staff
  revérifie `staff.restaurant_id` en base, et les canaux WebSocket appliquent la
  même règle plus un contrôle de rôle.
- **Intégrité du paiement.** Signatures vérifiées (HMAC Konnect, natif Stripe
  sur le corps brut), montant **toujours** relu chez le prestataire et jamais
  cru depuis le webhook, montants de parts recalculés côté serveur.
- **Prix figés** sur `OrderItem` (nom, prix, catégorie TVA, options) — une
  modification de carte ne réécrit jamais une commande passée.
- **Transitions d'état contrôlées.** `ALLOWED_TRANSITIONS` refuse tout ce qui
  n'est pas listé ; `TERMINAL_STATUSES` en est dérivé et ne peut pas diverger.
- **Double validation impossible.** `pop_all()` lit et vide le panier partagé en
  une seule opération synchrone, sans `await` intercalé.
- **Numérotation de facture par émetteur**, verrou `FOR UPDATE`, repli sur
  `IntegrityError`, jamais dérivée de `Order.id`.
- **Couche marché France** : EUR/2 décimales/virgule, `zoneinfo` conscient de
  l'heure d'été, TVA figée à la commande, deux tests de CI qui échouent si une
  devise ou un fuseau réapparaît en dur.
- **Aucun N+1** sur les chemins chauds, `selectinload` correctement posé.
- **Aucun secret commité**, `.gitignore` complet.

## Annexe C — Correspondance avec `ROADMAP.md` Phase 20

La Phase 20 (« Mettre en ligne, pour de vrai ») n'est pas annulée : ses lignes
sont reprises ici, et elle reste le point d'entrée pour tout ce qui n'est pas
technique (domaine, variables d'environnement, déclaration INPDP).

| `ROADMAP.md` Phase 20 | Devient |
| --- | --- |
| Choisir et provisionner l'hébergement 🧑 | **P3.1** — mais la contrainte « une seule instance » qu'elle pose tombe en **P2.1** |
| Activer les sauvegardes automatiques 🧑 | **P1.7** |
| Restaurer une sauvegarde une fois 🧑 | **P1.7** |
| Brancher le monitoring sur `/health` 🧑 | **P1.7** |
| Collecte des erreurs 🧑 | **P1.7** |
| Réserver le domaine, générer les vraies clés, INPDP 🧑 | **reste en Phase 20** — hors périmètre technique |
| Rejouer le parcours complet sur staging 🧑 | **P2.5** (le staging n'existe pas encore) |

**Ordre à respecter** : P1 clos → Phase 20 exécutable → P2 → P3.
