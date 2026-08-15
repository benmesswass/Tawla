# Audit final — Tawla (15 août 2026)

Audit interne mené en position de fondateur qui doit décider quoi faire du
trimestre : code exécuté et non seulement lu, chaque fonctionnalité notée, le
modèle économique et le marché repris à zéro.

Périmètre : branche `main` au commit `2b4cb40`, après la Phase 18.

**Note pondérée : 5,6/10** — contre 6,5 affichés par `ROADMAP.md`. L'écart n'est
pas une divergence d'appréciation sur le code : c'est que deux lignes de la
grille de pilotage notent aujourd'hui **l'intention** au lieu de l'état.
Détail au § 5.

**Note d'artisanat technique : 8,5/10.** Le produit est meilleur que sa note
globale, et c'est exactement le diagnostic : 40 % du poids de la grille dépend
de choses qui n'ont pas encore été faites, et aucune ne se code.

---

## 1. Ce qui a été exécuté pour cet audit

Rien de ce qui suit ne repose sur une lecture seule.

| Vérification | Résultat |
|---|---|
| Suite backend (`pytest -q`) | **280 tests verts en 108 s** |
| Lint frontend (`next lint`) | vert, 1 avertissement (`<img>` sur la page menu) |
| Types frontend (`tsc --noEmit`) | vert |
| Build de production frontend | vert — 13 routes, 87 kB de JS partagé |
| CI GitHub sur `main` | verte au 15/08 06:56 |
| Tarifs concurrents rejoués sur source publique | inchangés : 19 / 29 / 39 / 49 DT/mois |
| Journal de terrain (`terrain/`) | **0 entretien, 0 pilote, 0 client** |

Volume : 4 221 lignes de backend, 5 149 lignes de tests backend, 7 861 lignes de
frontend, **0 ligne de test frontend**.

---

## 2. Audit technique

### 2.1 Ce qui est réellement bon

- **Le cœur métier est verrouillé au bon endroit.** `ALLOWED_TRANSITIONS`
  (`orders/service.py:43`) refuse explicitement tout le reste, `TERMINAL_STATUSES`
  en est dérivé pour qu'ils ne puissent pas diverger, et le prix est figé sur
  `OrderItem` au moment de la commande. C'est la partie du code où une erreur
  coûterait le plus, et c'est la mieux tenue.
- **L'isolation multi-tenant tient**, et elle est testée par attaque, pas par
  lecture. Discipline constante : `404` et jamais `403` quand la ressource
  appartient à un autre établissement, pour ne pas confirmer son existence.
- **`tests/test_migrations.py` est la meilleure décision d'ingénierie du dépôt.**
  La CI teste sur un schéma `create_all()`, la production tourne sur Alembic :
  c'était le seul écart qu'aucun test ne pouvait voir, et un champ ajouté sans
  migration passait tout puis cassait en plein service. Ce test le rend
  impossible.
- **Les commentaires expliquent des décisions, pas du code.** La raison d'un
  choix survit à celui qui l'a pris — c'est ce qui rend ce dépôt reprenable par
  quelqu'un d'autre, et c'est rare.
- **Les renoncements sont écrits** (`ROADMAP.md`, section « hors périmètre »).
  Un fondateur qui sait écrire ses « non » vaut mieux qu'un fondateur qui a tout
  coché.

### 2.2 Les défauts trouvés, par gravité

**T1 — `POST /loyalty/lookup` est le dernier trou de la surface publique.**
`loyalty/router.py:15` → `loyalty/service.py:29`

C'est la seule route publique qui accepte encore un `restaurant_id` numérique
et incrémental, et la seule qui **écrit** en base sans jeton. Deux conséquences,
toutes deux vérifiées en lisant le schéma de sortie :

- N'importe qui peut demander « le numéro +216XXXXXXXX est-il client de
  l'établissement 7, et combien de fois y est-il venu ? » et obtenir
  `order_count` et `reward_available`. Une requête suffit pour un numéro connu :
  le limiteur de débit ne protège que du balayage de masse, pas de la question
  ciblée.
- `lookup_or_create` **crée** la fiche si elle n'existe pas. Un anonyme peut donc
  écrire des numéros de téléphone de tiers dans la base fidélité de n'importe
  quel établissement, sans limite autre que 20 par minute.

La Phase 12.2 a retiré `birth_date` et posé un limiteur — le test dédié
(`test_public_loyalty_lookup_never_exposes_the_birth_date`) ne vérifie que la
date de naissance. Le constat 4 de la revue est donc **partiellement** fermé,
alors que la roadmap le compte comme clos. C'est aussi le seul point où le code
contredit `frontend/lib/i18n/privacy.ts`, qui promet que le numéro n'est jamais
partagé.

*Correction : exiger le `qr_token` de la table (le client l'a déjà dans son
URL) au lieu du `restaurant_id`, et ne jamais créer la fiche depuis cette route
— `create_order` la crée déjà au bon moment.*

**T2 — La file d'attente hors ligne peut dupliquer une commande.**
`frontend/app/menu/[qrToken]/page.tsx:512` + `backend/app/modules/orders/router.py:17`

Quand `fetch` échoue avec une `TypeError`, la commande est mise de côté sur le
téléphone et rejouée au retour du réseau. Mais `fetch` échoue aussi avec une
`TypeError` quand la requête **est arrivée au serveur** et que c'est la réponse
qui s'est perdue. Il n'y a aucune clé d'idempotence sur `POST /orders` : la
commande part alors deux fois, la cuisine prépare deux fois, et le client paie
une addition qu'il conteste.

C'est le défaut le plus coûteux du lot, parce qu'il frappe précisément le
scénario que le produit met en avant en rendez-vous — « et si votre wifi
tombe ? ». Le repli papier a été pensé pour ce cas, la file hors ligne pas
jusqu'au bout.

*Correction : un `client_order_id` (UUID) généré par le navigateur, unique en
base, renvoyant la commande existante au lieu d'en créer une seconde.*

**T3 — Le limiteur de débit s'effondre derrière un proxy d'hébergeur.**
`core/rate_limit.py:18`

La clé est `request.client.host`. Uvicorn ne fait confiance aux en-têtes
`X-Forwarded-For` que depuis `127.0.0.1` par défaut (`FORWARDED_ALLOW_IPS` non
renseigné dans `.env.example`, aucun réglage dans le `Dockerfile`). Sur Railway
ou Render, le conteneur reçoit les connexions du proxy de la plateforme : **tous
les clients du parc partagent alors la même clé**.

Effet le jour de la mise en ligne : 20 connexions par minute pour tous les
restaurants réunis sur `/auth/login`, 20 appels serveur par minute pour toutes
les tables de tous les établissements, 20 recherches fidélité. Le 21ᵉ serveur
qui se connecte à 20 h prend un `429`. Invisible en test, certain en production
— et c'est la Phase 12.3 qui arrive.

*Correction : lire `X-Forwarded-For` explicitement, ou fixer
`FORWARDED_ALLOW_IPS` à l'IP du proxy au déploiement. À traiter dans la même
passe que les sauvegardes.*

**T4 — `POST /orders` n'est pas limité en débit, `POST /waiter-calls` l'est.**

Les deux routes ont exactement le même niveau d'accès (le `qr_token` d'une
table) et la même nuisance possible. Le raisonnement écrit sur l'appel serveur
(« le QR est physiquement sur la table, donc un client attablé peut insister »)
s'applique mot pour mot à la création de commande — sauf que là, la nuisance
mobilise la cuisine. Une photo du QR d'une terrasse, prise depuis le trottoir,
suffit.

**T5 — Échappement incohérent dans les deux fenêtres d'impression.**
`app/staff/page.tsx:429` et `app/kitchen/page.tsx:215`

Dans la même fonction, `notes` (saisie par le client) et `taken_by_staff_name`
sont échappés, `table_label` ne l'est pas. La donnée est sous contrôle du
manager, donc la gravité est faible — mais c'est le genre d'incohérence qui
devient une faille le jour où quelqu'un déplace ce code.

**T6 — Zéro test frontend, et deux fichiers de plus de 1 000 lignes.**

`menu/[qrToken]/page.tsx` fait 1 199 lignes, `dashboard/page.tsx` en fait 1 292.
Ce sont les deux seuls endroits du dépôt qui échappent à la discipline du reste,
et ce sont **les deux écrans que le prospect regarde**. Le panier, le total
affiché, la file hors ligne, le passage en RTL et le parcours de paiement n'ont
aucun test automatisé, alors que le backend en a 5 149 lignes.

La convention du projet dit « tester les risques métier réels, pas la couverture
pour la couverture ». Le panier client est un risque métier réel.

**T7 — Le mono-instance est un plafond, pas seulement une contrainte.**

Gestionnaire WebSocket et limiteur de débit en mémoire : pas de montée en
charge horizontale, et surtout **pas de redéploiement sans coupure**. Publier un
correctif à 20 h 30 fait tomber tous les écrans de salle en même temps (le hook
reconnecte, mais l'état se recharge). À 45 clients c'est tenable ; il faut le
savoir avant de promettre « joignable pendant le service », pas après.

### 2.3 Note technique par sous-dimension

| Sous-dimension | Note |
|---|---:|
| Architecture et lisibilité | 9,5 |
| Cœur métier (états, prix, isolation) | 9,5 |
| Tests backend | 9,0 |
| Migrations et évolution du schéma | 9,5 |
| Sécurité de la surface publique | 7,0 |
| Robustesse en conditions réelles (réseau, proxy) | 6,0 |
| Tests frontend | 0,0 |
| Prêt pour l'exploitation (déploiement, sauvegardes, supervision) | 4,0 |
| **Artisanat technique** | **8,5** |

---

## 3. Notation fonctionnalité par fonctionnalité

Barème : la note dit **l'état de livraison _et_ la valeur commerciale prouvée**.
Une fonctionnalité parfaitement écrite dont aucun restaurateur n'a jamais eu
besoin ne peut pas dépasser 5.

### Parcours client

| # | Fonctionnalité | Note | Ce qui fixe la note |
|---|---|---:|---|
| 1 | Scan QR → carte (catégories, piment, allergènes, halal) | 8,5 | Ordre logique d'un repas, rupture de stock qui disparaît en direct. Aucun test automatisé |
| 2 | Panier, notes, plat partagé | 8,0 | Le bon périmètre. Le total est recalculé côté serveur : rien à falsifier depuis le téléphone |
| 3 | Vente incitative « avec ce plat » | **9,0** | La seule fonctionnalité qui produit un chiffre défendable en rendez-vous, et son effet est **mesuré** (`from_suggestion`). La meilleure du produit au sens commercial |
| 4 | Suivi temps réel de la commande | 8,5 | Canal lié au `public_token`, reconnexion avec repli, prénom du serveur annoncé au client |
| 5 | Notification push « c'est prêt » | 7,0 | Dégradation propre sans clés VAPID, abonnement purgé en statut terminal. Jamais éprouvée sur iOS |
| 6 | File d'attente hors ligne | **5,0** | Bonne intention, exécution incomplète : rejeu sans idempotence → commande dupliquée (T2). Sur la promesse « et si le wifi tombe », c'est la pièce qui doit être irréprochable |
| 7 | Paiement carte simulé + pourboire | 4,0 | Honnête (mode simulé assumé) mais sans valeur en rendez-vous, et le cash domine le marché. Ne jamais en faire un argument |
| 8 | Paiement espèces (demande + encaissement) | 8,0 | C'est le vrai flux tunisien, correctement adressé au serveur qui tient la table |
| 9 | Partage d'addition | 6,0 | Soigné, mais aucun restaurateur n'a jamais dit en avoir besoin. Premier candidat à la coupe après les entretiens |
| 10 | Appel serveur depuis la table | 8,0 | Utile, limité en débit, et l'identifiant devinable a été corrigé (PR #45) |
| 11 | Fidélité par numéro de téléphone | **5,5** | Fonctionne, mais porte le seul trou de sécurité restant (T1) et la seule donnée personnelle du produit. Le plus mauvais rapport valeur/risque du dépôt |
| 12 | Mode ramadan + pré-commande iftar | 7,5 | Vrai différenciateur saisonnier, aucun concurrent local ne l'a. Plafonné : jamais joué pendant un vrai Ramadan |
| 13 | Mode café | 6,5 | Simplification d'écran peu coûteuse, cohérente avec la cible |
| 14 | Bilingue fr/ar avec RTL | 8,0 | `dir` géré page par page, dictionnaires complets. `<html lang="fr">` jamais mis à jour : défaut d'accessibilité |
| 15 | Consentement + politique de confidentialité fr/ar | 8,5 | Affiché **au-dessus** du champ, pas derrière un lien. Rare et bien fait. Moins un point : le texte ne décrit pas T1 |
| 16 | Célébration, anecdotes culturelles, carte à partager | 4,0 | Soin réel, valeur commerciale nulle. À garder (c'est écrit), à ne jamais démontrer en rendez-vous |

### Écran serveur

| # | Fonctionnalité | Note | Ce qui fixe la note |
|---|---|---:|---|
| 17 | Pool partagé + prise en charge nominative | **9,0** | Le vrai parti pris d'organisation de salle, et la base des primes. Le meilleur argument produit face à un patron |
| 18 | Plan de salle + action depuis la table | 8,5 | Le meilleur écran de démonstration du produit. Retenue : les commandes actives ne sont pas bornées dans le temps, des tables restent rouges le lendemain (tâche ouverte, Phase 18) |
| 19 | Encart « ma soirée » | 8,0 | Bonne réponse au risque n°1 (le serveur sabote l'outil). L'API n'envoie aucun nom d'autrui : rien ne peut fuiter dans une évolution future |
| 20 | Repli papier (impression) | 7,0 | Présent des deux côtés et documenté dans `terrain/`. Moins un point pour l'échappement incohérent (T5) |
| 21 | Fidélité en salle (consultation, récompense) | 7,0 | Correctement sous JWT, et le contrôle humain borne l'abus |

### Écran cuisine

| # | Fonctionnalité | Note | Ce qui fixe la note |
|---|---|---:|---|
| 22 | Écran cuisine temps réel (+ son, vérifié à 360 px) | 8,5 | Rien n'y entre sans validation du serveur. La vérification à 360 px lève la réserve de la revue |
| 23 | Compteur de commandes du jour | 7,0 | Peu coûteux, immédiatement lisible |

### Tableau de bord manager

| # | Fonctionnalité | Note | Ce qui fixe la note |
|---|---|---:|---|
| 24 | Recette du jour + commandes perdues, en tête | **9,0** | La fonctionnalité de rétention. Définitions partagées avec la page de preuve (`_lost_orders`, `_billable_orders`) : les deux écrans ne peuvent pas se contredire |
| 25 | Statistiques détaillées (temps par étape, top plats, heures) | 7,5 | Complet et honnête. Aucun patron ne l'ouvrira tous les soirs, et c'est normal |
| 26 | Page de preuve + export CSV | 8,5 | L'écran qui vend le passage au payant. Il lui manque le relevé « avant Tawla » (17.2 non faite) : la comparaison n'est encore que semaine contre semaine |
| 27 | Rapport hebdomadaire par serveur | 8,0 | L'angle que les trois concurrents ne mettent pas en avant. Jamais affiché en salle, à raison |
| 28 | Carte + import CSV + rupture en un clic | 8,5 | L'import tolérant aux erreurs est ce qui évite le premier abandon d'un patron |
| 29 | Tables, zones, éditeur de plan (enregistrement automatique) | 8,5 | Suppression du bouton « Enregistrer » : bonne décision, un bouton n'offrait que l'occasion de perdre son travail |
| 30 | Gestion de l'équipe | 8,5 | Dernier manager actif protégé, mot de passe régénéré et montré une seule fois |
| 31 | Inscription self-service | 7,0 | Pas de vérification d'e-mail — assumé, et suffisant pour un produit vendu en main propre |

### Plateforme

| # | Fonctionnalité | Note | Ce qui fixe la note |
|---|---|---:|---|
| 32 | Authentification JWT + rôles + compte désactivé | 8,5 | L'état actif est revérifié à **chaque** requête, pas seulement au login |
| 33 | Isolation multi-tenant | **9,0** | Testée par attaque. `404` plutôt que `403` partout, sans exception |
| 34 | Temps réel WebSocket + reconnexion | 8,0 | Solide, mais mono-instance : c'est le plafond d'architecture (T7) |
| 35 | Migrations Alembic + test de conformité modèles/migrations | **9,5** | La meilleure décision d'ingénierie du dépôt |
| 36 | Kit d'installation (script, CSV, chevalets QR, fiche) | **9,0** | C'est concrètement ce qui justifie 120 DT face à un concurrent à 39 DT |
| 37 | Conformité 2004-63 (consentement, rétention, purge) | 7,5 | Purge réelle, lancée à la main, `--appliquer` explicite. Moins des points pour T1 et la déclaration INPDP non déposée |
| 38 | Observabilité (`/health` réel, logs JSON) | 7,0 | Le code est prêt et honnête ; rien n'est branché faute de production |
| 39 | Sécurité de la surface publique | 7,0 | Sept constats sur huit fermés **et** testés nommément. Le huitième (T1) est resté ouvert et compté comme clos |
| 40 | Facturation | — | Inexistante. C'est le bon choix pour dix clients : une facture manuelle suffit |
| 41 | Intégration caisse | — | Hors périmètre assumé — et c'est la première objection que le patron posera |
| 42 | Tests frontend | **0,0** | Aucun. Le parcours qui encaisse l'argent n'a aucun filet automatisé |

**Moyenne des fonctionnalités livrées : 7,6/10.** Ce chiffre est plus flatteur
que la note globale, et l'écart dit tout : ce projet n'a pas un problème de
produit.

---

## 4. Design

### Ce qui est réussi

- **Une identité qui tient sans folklore.** Palette semoule / harissa / menthe /
  laiton, Lalezar en titrage, Hanken Grotesk en texte, logo et icônes dessinés
  pour le projet. C'est tunisien sans être une carte postale — le piège habituel
  est évité.
- **Le plan de salle est du vrai design d'outil de service**, pas une
  illustration. Contraste inversé (sol sombre, plateaux clairs) pour qu'une
  table qui attend soit la seule chose colorée d'un écran regardé dans une salle
  peu éclairée. L'anneau autour d'une table est un **compte à rebours calé sur
  le seuil de perte** — le même seuil dont la page de preuve tire l'argent
  perdu. Une seule table respire, la plus urgente : trois en feraient un sapin.
  Chaque règle a une raison écrite.
- **`prefers-reduced-motion` respecté partout**, y compris sur les animations
  festives du parcours client. Rare à ce stade d'un projet.
- **La hiérarchie du tableau de bord est la bonne** : la recette d'abord, en
  gros, puis les commandes perdues à côté avec leur définition en clair. C'est
  ce que le patron vient chercher, et il découvre le reste en passant.

### Ce qui ne va pas

- **Le système de composants est contourné là où il compte le plus.**
  `Button`, `Card`, `Badge`, `EmptyState` existent et servent sur les écrans
  serveur, cuisine et statistiques. Les deux plus grosses surfaces — la page
  client (137 `className` en dur) et le tableau de bord manager (131) — ne les
  utilisent quasiment pas. Ce sont **exactement les deux écrans qu'un prospect
  regarde**, et ce sont les deux qui dériveront en premier.
- **`<html lang="fr">` reste figé** alors que le parcours client bascule en
  arabe. Le `dir` est bien géré page par page, mais un lecteur d'écran prononce
  l'arabe avec les règles du français. Correction : une ligne.
- **Pas de mode sombre côté client.** L'écran cuisine l'a parce qu'il était
  pensé pour une cuisine ; un téléphone tenu en terrasse le soir, non.
- **Aucun contrôle de contraste formel.** Les valeurs choisies paraissent
  saines, mais « paraissent » n'est pas une vérification — et une carte
  illisible en terrasse à midi est un motif d'abandon silencieux.
- L'avertissement `<img>` sur la page menu est le seul reproche de l'outillage :
  les photos de plats ne sont pas optimisées, sur la page la plus chargée et la
  plus souvent ouverte en 3G.

**Note design : 8,0/10.** Le plan de salle vaut 9 ; la dette de cohérence sur
les deux écrans principaux coûte le reste.

---

## 5. Modèle économique

### L'arithmétique tient, et elle se vérifie devant le client

- 120 DT/mois ≈ **4 DT par jour**.
- Panier moyen supposé 25 DT → **une commande perdue par semaine paie
  l'abonnement**, une par jour le paie six fois.

Ce calcul est solide parce qu'il ne demande pas d'être cru : le produit
**mesure** les commandes perdues, et les affiche avec leur définition. On promet
un chiffre, puis on le montre sur le même écran. C'est le meilleur actif
commercial du projet — davantage que n'importe quelle fonctionnalité.

Le 25 DT reste une hypothèse. Le citer comme un fait devant un patron est la
seule façon de perdre l'avantage que donne la mesure.

### Le choix de prix est le bon, pour la bonne raison

| Stratégie | Prix | Clients | Revenu/an | Charge réelle |
|---|---:|---:|---:|---|
| Volume, aligné concurrence | 35 DT | 290 | ≈ 122 k DT | Intenable seul |
| **Valeur, service inclus** | **120 DT** | **45** | **≈ 65 k DT** | Tenable seul |
| Valeur, à deux | 120 DT | 90 | ≈ 130 k DT | Même revenu que la ligne 1, trois fois moins de clients |

Un fondateur seul ne gagne pas une guerre de volume : chaque client ajouté coûte
du déplacement, de la formation, du support un vendredi soir. Ce qui justifie
120 DT face à 39 DT n'est pas une fonctionnalité de plus — c'est ce qu'un
éditeur en libre-service ne fera jamais : **venir**. Et cette promesse est
**déjà outillée** (`setup_restaurant.py`, import CSV tolérant, chevalets
imprimables, fiche de remise) : c'est la seule partie de l'argumentaire qui
existe en code.

### Les trois faiblesses du modèle

1. **Le prix n'est toujours pas tranché.** `PRICE_MONTHLY_DT` est `null`, et la
   page publique affiche « tarif communiqué au premier rendez-vous ». C'est le
   bon choix par défaut, mais c'est devenu un report : la page attend une
   décision qui n'a besoin d'aucune donnée nouvelle pour être prise. Le prix
   proposé (120 DT) est déjà écrit dans deux documents.
2. **Le service inclus est le produit, et il n'a pas de plafond mesuré.**
   45 clients à 120 DT suppose que l'installation prend une heure et le support
   quelques minutes par semaine. Aucun de ces deux chiffres n'a été observé une
   seule fois. Si l'installation prend une demi-journée, le modèle ne tient plus
   à 45 clients — il tient à 20.
3. **Rien ne mesure la rétention.** Le produit sait dire ce qu'un restaurant
   encaisse ; il ne sait pas dire si son patron a ouvert le tableau de bord
   cette semaine. C'est pourtant le signal qui précède une résiliation de deux
   mois. Un compteur d'ouvertures du tableau de bord par établissement coûterait
   une colonne.

### Pourquoi la note de la grille descend à 5,6

`ROADMAP.md` affiche 6,5. Recalculé ligne à ligne sur l'**état constaté** :

| Dimension | Poids | Roadmap | Cet audit | Pourquoi l'écart |
|---|---:|---:|---:|---|
| Accès au marché & vente | 20 % | 2,0 | 2,0 | Inchangé : 0 entretien, 0 pilote |
| Prêt à vendre | 15 % | 8,5 | 7,5 | T1 reste ouvert, T3 casse le jour de la mise en ligne, et rien n'est déployé |
| Besoin marché prouvé | 20 % | 7,0 | 5,5 | La roadmap écrit elle-même que cette note « ne bougera qu'avec des chiffres relevés chez un vrai restaurant ». Il n'y en a aucun |
| Viabilité économique | 20 % | 7,0 | 5,0 | Zéro client payant, prix non tranché. On note un plan |
| Différenciation | 10 % | 6,5 | 6,5 | Inchangé : la vente incitative et le plan de salle sont réels |
| Exécution technique | 15 % | 9,0 | 8,5 | Trois défauts réels et zéro test frontend |
| **Total** | | **6,5** | **5,6** | |

**Le constat le plus important de cet audit n'est pas T1 ni T2 : c'est que
l'instrument de pilotage s'est mis à noter l'intention.** Deux lignes valant
40 % du poids ont été montées alors que les faits qu'elles mesurent — des
chiffres relevés en établissement, un prix réellement payé — n'existent
toujours pas. Un tableau qui se félicite du travail préparatoire cesse de
signaler ce qui manque, et c'est exactement le rôle qu'on lui a donné.

**Note modèle économique : 6,0/10.** Le raisonnement est juste, l'outillage
existe, rien n'est encore confronté à un client.

---

## 6. Étude de marché

### Le marché adressable

| Étape | Valeur | Hypothèse |
|---|---:|---|
| Cafés en Tunisie | ≈ 40 000 | Estimation de presse 2025, non officielle |
| Filtre d'adressabilité | × 6 % | Wi-Fi utilisable, clientèle smartphone, volume, grandes villes |
| Établissements adressables | ≈ 2 400 | Le vrai marché, pas le TAM de présentation |
| Objectif retenu | **45** | ≈ 1,9 % des établissements adressables |

À 45 clients, l'objectif représente moins de 2 % du marché adressable. C'est ce
qui rend le plan crédible : il n'exige pas de gagner un marché, seulement d'en
convaincre quarante-cinq patrons — un par semaine pendant un an.

### La concurrence, revérifiée aujourd'hui

Tarifs de Digital Menu inchangés depuis la revue du 13 août : **19 DT** (light),
**29 DT** (serveur), **39 DT** (commande à table), **49 DT** (premium), avec
écran cuisine, zones, fidélité et statistiques du personnel. Scanny ajoute une
caisse connectée, Menu-QR occupe l'entrée de gamme.

Trois lectures de ce fait, dans l'ordre d'importance :

1. **C'est une bonne nouvelle.** Trois acteurs qui vendent cette catégorie
   prouvent que le marché tunisien paie pour ça. Il n'y a plus d'idée à
   évangéliser — le travail le plus coûteux et le plus incertain qui existe.
2. **Le logiciel n'est pas défendable.** Tawla n'a aucune fonctionnalité que ces
   trois-là ne pourraient pas répliquer en quelques semaines, et l'inverse est
   vrai aussi (les postes de production de Digital Menu n'existent pas ici). En
   2026, cette couche logicielle n'est pas un actif : **la distribution l'est.**
3. **Le prix ne se compare que si le produit vendu est le même.** À 120 DT face
   à 39 DT, un patron qui compare deux lignes de tarif dira non, et il aura
   raison. Tout le travail du rendez-vous consiste à rendre la comparaison
   impossible : eux vendent un lien vers un menu, Tawla vend quelqu'un qui vient
   installer, forme l'équipe et reste joignable pendant le service.

### Les vrais différenciateurs, classés

| Différenciateur | Défendable ? | Valeur |
|---|---|---|
| **Le service sur place** | Oui — structurel, un éditeur en libre-service ne peut pas le faire sans changer de modèle | La plus haute |
| **La mesure avant/après** | Oui tant que personne d'autre ne l'outille — c'est un argument qui se prouve | Haute |
| **Le rapport par serveur comme base de prime** | Partiellement — l'angle est neuf, la fonctionnalité non | Moyenne |
| **Mode ramadan et pré-commande iftar** | Non durablement — mais personne ne l'a construit, et la fenêtre revient chaque année | Saisonnière, forte |
| **Plan de salle** | Non — copiable | Démonstration, pas défense |

### La fenêtre de tir, et ce qu'elle impose

**Ramadan, février-mars 2027.** L'iftar est le service le plus tendu de l'année :
toutes les tables commandent à la même minute, et c'est là que les commandes se
perdent. Le mode ramadan et la pré-commande existent déjà.

À rebours depuis cette date :

| Quand | Quoi | Marge restante |
|---|---|---|
| **Août – septembre 2026** | Mise en ligne + 20 entretiens | **6 semaines** |
| Octobre – novembre 2026 | Trois pilotes, quatre semaines chacun | aucune |
| Décembre – janvier 2027 | Deux passages au payant | aucune |
| Février – mars 2027 | Ramadan : la démonstration se fait seule | — |

Nous sommes le 15 août. **Le calendrier n'a plus de marge**, et le seul poste
qui en consomme aujourd'hui est le développement de fonctionnalités.

**Note étude de marché : 7,5/10.** L'analyse est juste, sourcée, et sa
conclusion la plus dure (« le code n'est pas un actif ») est assumée. Elle
perd des points sur un seul point : elle repose entièrement sur des sources
publiques, aucune sur un restaurateur.

---

## 7. Verdict et ce qu'il faut faire

### Le diagnostic en une phrase

**Tawla est un très bon produit qui n'a rencontré personne.** L'écart entre
8,5 en artisanat technique et 2,0 en accès au marché n'est pas un déséquilibre à
corriger progressivement : c'est le seul sujet qui reste, et il ne se code pas.

### Les cinq choses à faire, dans cet ordre

1. **Fermer T1, T2 et T3 — une journée, pas plus.** Ce sont les trois seuls
   défauts qui coûteraient un client. T3 casse le jour même de la mise en ligne,
   T2 le jour où un wifi tombe, T1 le jour où quelqu'un regarde. Rien d'autre
   dans le code n'a besoin d'être touché.
2. **Mettre en ligne, avec les sauvegardes.** Un pilote qui perd son service du
   soir ne revient pas, et il le racontera aux autres patrons du quartier.
3. **Faire les vingt entretiens.** C'est 20 % de la grille noté 2,0, et la seule
   ligne qui conditionne toutes les suivantes. La synthèse doit produire une
   **coupe** dans la roadmap — les candidats sont déjà identifiés : partage
   d'addition, mode café, carte à partager.
4. **Trancher le prix.** 120 DT est écrit dans deux documents et attendu par une
   constante `null` dans le code. Cette décision n'a besoin d'aucune donnée
   nouvelle.
5. **Ne plus écrire une ligne de fonctionnalité avant le premier pilote.** Y
   compris le relevé « avant Tawla » (17.2) : sans établissement, il n'a rien à
   afficher.

### Ce qu'il faut arrêter de faire

Depuis la Phase 12, chaque phase livrée a été techniquement irréprochable et
n'a déplacé aucune des deux lignes qui portent 40 % de la note. Le plan de salle
est le meilleur écran du produit et n'a rapproché d'aucun client — sa propre
tâche de clôture le dit : « confronter le plan aux entretiens de 13.1 ».

Écrire du code est devenu la façon confortable de ne pas franchir la porte d'un
restaurant. La roadmap le dit déjà, en toutes lettres, depuis trois phases :
**« écrire du code supplémentaire maintenant ferait baisser la note ».** Trois
phases ont été livrées depuis.

---

## Sources

- Concurrence, revérifiée le 15/08/2026 :
  [Digital Menu — tarifs](https://digitalmenu.tn/prix-tarif-menu-digital-qr-code),
  [Digital Menu — fonctionnalités](https://digitalmenu.tn/fonctionnalites/menu-digital-qr-code),
  [Menu-QR](https://www.menu-qr.tn/), [Menu QR Code](https://menuqrcode.tn/)
- Marché, paiements, financement et loi 2004-63 : voir les sources de
  [`REVUE_INVESTISSEURS.md`](./REVUE_INVESTISSEURS.md), inchangées
- Documents internes : [`ROADMAP.md`](./ROADMAP.md),
  [`REVUE_INVESTISSEURS.md`](./REVUE_INVESTISSEURS.md),
  [`PREMIERES_VENTES.md`](./PREMIERES_VENTES.md), `terrain/`
