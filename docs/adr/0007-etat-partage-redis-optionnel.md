# État partagé entre instances : un magasin unique, Redis optionnel

Cinq choses vivaient dans des dicts de module : le registre de diffusion
WebSocket (`notifications/manager.py`), le panier de table
(`orders/table_cart.py`), le roster des convives (`tables/roster.py`), le mode
de répartition (`tables/split_mode.py`) et le limiteur de débit
(`core/rate_limit.py`). Chacun l'assumait explicitement, et chacun avait
raison : tant qu'un seul processus tourne, un dict est le bon choix.

C'est aussi ce qui rendait **une deuxième instance backend impossible** — une
commande passée sur l'instance A n'apparaissait jamais sur l'écran connecté à
l'instance B, et deux téléphones de la même table pouvaient tomber sur deux
paniers différents. La contrainte « une seule instance backend » était écrite
noir sur blanc dans `ROADMAP.md`. C'est elle que cette décision lève
(`ROADMAP_PRODUCTION.md` §P2.1 ; P2 est la condition d'existence de P3, la
capacité à 100 restaurants).

**Décision** : un magasin unique, `core/etat_partage.py::magasin`, avec deux
implémentations derrière le même contrat — `MagasinMemoire` (défaut) et
`MagasinRedis` (actif dès que `REDIS_URL` est renseignée). Les cinq usages
passent par lui ; aucun ne connaît Redis.

Trois propriétés portées par le contrat, parce que chacune protège un risque
métier réel :

- **écriture par champ** — deux téléphones qui ajoutent un plat au même
  instant écrivent deux clés différentes ; un blob JSON relu-réécrit en aurait
  perdu un ;
- **vider-et-lire atomique** — deux appareils qui valident au même instant ne
  peuvent pas transformer le même panier en deux commandes ;
- **ordre d'insertion** — le roster affiche les convives dans l'ordre où
  chacun a rejoint ; un dict Python le fait gratuitement, un hash Redis non,
  donc `MagasinRedis` range un rang devant chaque valeur.

**Redis optionnel, et non requis.** C'est le point qui a demandé un
arbitrage. Le mode mémoire reste le défaut et se comporte exactement comme
avant : aucune dépendance à installer, aucun service à payer, rien à lancer
pour `pytest -q`, et un pilote à un seul restaurant n'a aucune raison de payer
un Redis managé — `AUDIT_COUTS_PRODUCTION.md` ne le budgète d'ailleurs pas.
Rendre Redis obligatoire aurait ajouté un coût mensuel et un point de panne
supplémentaire à une installation qui n'en a pas besoin, pour une capacité dont
personne n'a encore la preuve qu'elle manque.

**Considered options.** *Postgres `LISTEN/NOTIFY` + tables SQL* : évite un
service de plus, mais demande une connexion bloquée en permanence par instance
pour l'écoute — exactement le défaut `idle in transaction` que P1.2 vient de
fermer — et ferait du panier de table une donnée persistée, ce que l'ADR 0005
a explicitement écarté. *Sessions collantes au répartiteur* : ne règle rien —
l'écran cuisine et le téléphone d'un client de la même table ne sont pas le
même client HTTP, et deux serveurs de la même salle non plus.

**Conséquences.** Un déploiement ne vide plus les paniers des clients attablés
quand Redis est branché (effet de bord gagné, pas visé). Redis devient un point
de panne quand il est activé : l'écoute de fond se rebranche seule après une
coupure, sans quoi une instance cesserait **silencieusement** de recevoir les
commandes des autres. Et les deux implémentations doivent rester
interchangeables : `tests/test_etat_partage.py` fait tourner les **mêmes
assertions** sur les deux, faute de quoi une suite qui tourne en mémoire ne
prouverait plus rien sur une production qui tourne sur Redis.
