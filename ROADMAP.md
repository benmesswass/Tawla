# Tawla — Roadmap

Fichier unique de pilotage du projet. Prendre la première tâche non cochée en
partant du haut, dans l'ordre des phases. Une tâche cochée `[x]` doit mentionner
la PR qui l'a livrée. Les tâches marquées 🧑 demandent une décision, un compte
réel ou une présence physique de Wassim — elles ne sont jamais faisables en
autonomie.

Refondue le **2026-08-18** après l'audit de pré-lancement
([`AUDIT_PRE_LANCEMENT.md`](./AUDIT_PRE_LANCEMENT.md), PR #54). Cette refonte
**fusionne** ce qui restait ouvert de la roadmap du 2026-08-15 avec ce que
l'audit a trouvé : les 44 tâches encore non cochées ont toutes été reprises ici,
aucune n'a été perdue, et les constats de l'audit sont devenus des tâches.
**Il n'existe toujours qu'une seule roadmap.**

Documents qui la fondent :

- [`AUDIT_PRE_LANCEMENT.md`](./AUDIT_PRE_LANCEMENT.md) — audit du 2026-08-18 :
  suites exécutées, parcours rejoués, attaques tentées avec leur code HTTP,
  vingt constats cités en `fichier:ligne`, grille recalculée à 5,4.
- [`AUDIT_FINAL.md`](./AUDIT_FINAL.md) — audit du 2026-08-15 : 42 fonctionnalités
  notées, trois défauts fermés depuis (Phase 19).
- [`REVUE_INVESTISSEURS.md`](./REVUE_INVESTISSEURS.md) — revue du 2026-08-13,
  grille de notation et plafond de revenus.
- [`PREMIERES_VENTES.md`](./PREMIERES_VENTES.md) — les dix recommandations pour
  décrocher les deux premiers clients payants.
- [`ROADMAP_ARCHIVE.md`](./ROADMAP_ARCHIVE.md) — phases 0 à 11. Lecture seule.

## Objectif

**Deux restaurants qui paient, avant Ramadan 2027.**

Ce n'est pas « passer de 5,4 à 8/10 au prochain jury ». La note suit, elle ne se
pilote pas : deux lignes valant 40 % de la grille ne bougeront qu'avec des
chiffres relevés dans un vrai établissement, et les deux audits successifs ont
montré qu'en visant la note directement on finit par se noter sur ses intentions.

L'objectif ci-dessus, lui, n'est pas interprétable : soit deux patrons ont viré
120 DT, soit non.

## La règle qui structure toute cette roadmap

**Une seule phase de code avant la mise en ligne, et plus rien ensuite avant le
premier pilote.**

Le produit ne manque pas de fonctionnalité — il manque un restaurateur. La
Phase 19 a fermé les trois défauts de l'audit du 15 août ; la **Phase 19bis**
ferme ce que l'audit du 18 août a trouvé en attaquant et en rejouant les
parcours ; la Phase 20 met en ligne ; et **tout ce qui suit passe par la porte
d'un restaurant**.

Toute tâche de code proposée après la Phase 20 doit d'abord répondre à :
« quel restaurateur l'a demandée, et lequel refuse de payer sans elle ? ».
Sans réponse nommée, elle va en § « Sous condition ».

**Une exception, et une seule** : un **défaut** constaté — le produit fait faux
— n'est pas une fonctionnalité et ne tombe pas sous cette règle. C'est ce qui
autorise la Phase 19bis. Un manque fonctionnel, lui, attend son restaurateur.
La distinction est tranchée dans `AUDIT_PRE_LANCEMENT.md` §5.

## Le calendrier, à rebours de Ramadan

Ramadan tombe en février-mars 2027. L'iftar est le service le plus tendu de
l'année, le mode ramadan et la pré-commande existent déjà, et c'est le seul
moment où la démonstration se fait toute seule. Rater cette fenêtre coûte un an.

| Quand | Phases | Ce qui doit être vrai à la fin |
|---|---|---|
| **18 – 19 août 2026** | 19bis | Les trois bloquants de l'audit sont fermés, avec les tests qui les prouvent |
| **19 – 25 août** | 20 | Le produit tourne en ligne, sauvegardé, sur un vrai domaine, déclaré à l'INPDP |
| **Fin août – septembre** | 21, 22 | 20 entretiens faits, prix tranché, roadmap coupée |
| **Octobre – novembre** | 23 | 3 pilotes installés, 4 semaines chacun, chiffres relevés |
| **Décembre – janvier 2027** | 24 | 2 pilotes passés au payant |
| **Février – mars 2027** | — | Ramadan : vendre avec des chiffres en main |

Une seule de ces lignes est du code. Le calendrier n'a plus de marge : c'est ce
qui justifie de refuser tout ajout fonctionnel.

## Où en est la note, et ce qui la déplace

Recalculée le 2026-08-18 sur l'état **constaté** par l'audit, jamais sur ce qui
est préparé ou en cours de PR.

| Dimension | Poids | 08-15 | **Constatée** | Cible | Ce qui la déplace | Phase |
|---|---:|---:|---:|---:|---|---|
| Accès au marché & vente | 20 % | 2,0 | **2,0** | 7,5 | 20 entretiens menés, 3 pilotes installés, 2 clients payants | 21, 23, 24 |
| Besoin marché prouvé | 20 % | 5,5 | **5,5** | 8,5 | Les trois métriques relevées **avant** et **après** chez un pilote réel | 23 |
| Viabilité économique | 20 % | 5,0 | **5,0** | 8,0 | Un prix tranché, puis réellement payé par deux établissements | 22, 24 |
| Prêt à vendre (installable, sûr) | 15 % | 7,5 | **7,0** | 9,0 | Les bloquants de 19bis fermés, la production en ligne avec sauvegardes restaurées | 19bis, 20 |
| Exécution technique | 15 % | 8,5 | **8,0** | 9,0 | Les défauts de 19bis corrigés **avec les tests qui les prouvent** | 19bis |
| Différenciation sur une niche | 10 % | 6,5 | **6,5** | 7,5 | Un chiffre venu d'un vrai pilote, cité avec le nom de l'établissement | 23 |
| **Note pondérée** | **100 %** | **5,6** | **5,4** | **8,2** | | |

Deux lignes ont baissé, alors que deux PR avaient été livrées entre les deux
audits : c'est exactement ce que la règle ci-dessus annonçait. Le travail de code
ne déplace plus la note vers le haut ; un audit qui cherche vraiment la fait
baisser. Recalculer cette colonne à la clôture de chaque phase.

---

## Phase 19bis — Fermer ce que l'audit de pré-lancement a trouvé

**Une journée. La dernière phase de code avant la porte d'un restaurant.**

Vingt constats, tous cités en `fichier:ligne` dans `AUDIT_PRE_LANCEMENT.md`.
Aucun n'est une fonctionnalité : ce sont des endroits où le produit fait faux.

Convention reconduite depuis la Phase 12.2 : **écrire d'abord le test qui
échoue**, puis le correctif. Un correctif sans test qui le prouve ne compte pas
comme livré. Deux exceptions explicites ci-dessous, marquées *(sans test)*, où
la vérification est manuelle par nature.

### 19bis.1 — Les trois bloquants

- [x] **F-1** — `from app.core import model_registry` ajouté à `scripts/seed_demo.py`, même correctif que `scripts/purge_donnees_personnelles.py:26` (PR #58)
- [x] **F-1 (test)** — process Python isolé qui exécute le script réel et passe une commande ; échoue sur l'ancien code (`no such table: orders`), passe avec le correctif (PR #58)
- [x] **F-2** — `active_orders_count` borné par `service_day_start()`, même borne que `list_active_orders` (PR #58)
- [x] **F-2 (test)** — une commande active datée d'avant le début de la journée de service ne compte plus (PR #58)
- [x] **C-1** — repli `crypto.randomUUID?.() ?? \`${Date.now()}-${Math.random().toString(36).slice(2)}\`` : cet identifiant n'a besoin que d'être unique par panier, pas cryptographique (PR #58)
- [x] **C-1 (vérification, sans test)** — `crypto.randomUUID` neutralisé sur une instance locale : l'ajout au panier fonctionne toujours, « Valider la commande » apparaît (PR #58)

### 19bis.2 — Les défauts à fermer avant le premier pilote

- [x] **F-3** — deux définitions de la journée cohabitaient : les écrans de service coupent à 5 h heure de Tunis (`app/core/dates.py:16`), le tableau de bord et la page de preuve coupaient à minuit UTC. `service_day_bounds()` ajoutée dans `dates.py`, utilisée aux deux endroits de `stats/service.py` (PR #61)
- [x] **F-4** — `list_pending_cash_payments` borné par `service_day_start()`, même borne que les commandes actives (PR #61)
- [x] **F-5** — paiement refusé avant confirmation (`ORDER_NOT_CONFIRMED`), annulation refusée après paiement (`CANNOT_CANCEL_PAID_ORDER`) (PR #61)
- [x] **S-1** — carte publique servie par `qr_token` (`/menu-items/by-token/{qr_token}`, même schéma que `restaurants`/`tables`) ; les routes `by-restaurant` réservées au staff de l'établissement (PR #61)
- [x] **S-2a** — collision confirmée en production (PR #57) : `ProxyHeadersMiddleware` d'uvicorn lit la même variable `FORWARDED_ALLOW_IPS` que notre `Settings` et réécrivait `request.client.host` avant `client_ip()`. Retirer la variable ne suffisait pas : le pair TCP brut est lui-même une IP interne à Render qui change à chaque requête (mesuré sur 24 requêtes réelles), et la première valeur de `X-Forwarded-For` est trivialement forgeable (testé). Correctif : `client_ip()` s'appuie uniquement sur `CF-Connecting-IP`, posé par Cloudflare et rejeté en 403 à son propre niveau s'il est forgé. `FORWARDED_ALLOW_IPS` retiré du code
- [x] **S-2b** — `POST /orders` a désormais son propre plafond (200/min par IP), distinct de celui de l'auth (toujours 20/min) — 20/min était partagé par toute la salle derrière le Wi-Fi du restaurant (PR #61)
- [x] **S-2c** — `RATE_LIMITED` traduit en français et en arabe, avec les deux nouveaux codes de F-5 (`ORDER_NOT_CONFIRMED` fr+ar, `CANNOT_CANCEL_PAID_ORDER` fr, staff-only) (PR #61)
- [x] **D-1** — écran serveur : les trois files (à confirmer / prêtes à servir / paiements en espèces) passent en colonnes au-delà de la largeur tablette, comme l'écran cuisine ; téléphone inchangé (PR #61)

### 19bis.3 — Ce qui attend le premier retour de terrain

Réel, cité, mais sans conséquence pour un patron cette semaine. À ne pas faire
maintenant, à ne pas oublier non plus.

- [ ] **F-6** — les `public_token` des commandes ouvertes vivent en `sessionStorage` (`frontend/app/menu/[qrToken]/page.tsx:82`) alors que la file hors ligne est en `localStorage` (`:641`) : un onglet fermé par iOS fait perdre l'addition. Passer en `localStorage`
- [ ] **P-4** — le mot « Swagger » est affiché au restaurateur qui paie (`frontend/app/dashboard/page.tsx:547`). Réécrire la phrase de son point de vue
- [ ] **S-3** — corriger la phrase du résidu de `/loyalty/lookup` : avec le `qr_token`, la réponse ne dit pas seulement qu'un numéro est connu, elle donne aussi `order_count` et `is_birthday_today` (`app/modules/loyalty/schemas.py:38-39`, `:53-62`). Corriger la description, ou retirer `order_count` de la vue publique
- [ ] **S-4** — `authenticate_staff_socket` (`app/modules/notifications/dependencies.py:31-54`) ne vérifie pas le rôle : un compte cuisine peut écouter `/ws/staff`. Sans risque entre collègues, à aligner par cohérence avec les routes HTTP
- [ ] **S-6** — `_hits` (`app/core/rate_limit.py:16`) crée une clé par IP et ne la supprime jamais. Fuite lente, sans conséquence à l'échelle de 45 établissements

### 19bis.4 — La PR #53, ouverte et non fusionnée 🧑

Photos de carte stockées en base, glisser-déposer, `UtcDatetime`, pourboire en
espèces, ardoise de table, `EnteteManager`. Elle n'était pas dans le périmètre
de l'audit et n'est comptée nulle part dans la grille.

- [ ] Décider 🧑 : fusionner avant la mise en ligne, ou la laisser en attente jusqu'après les pilotes. Une PR ouverte qui vieillit se fusionne de plus en plus mal
- [ ] Si elle est fusionnée : **valider `image_url` à la réception**. `S-5` a montré qu'un `javascript:` ou un SVG à script est accepté tel quel aujourd'hui (`app/modules/menu/schemas.py:80`) — non exploitable sans upload, mais la PR #53 apporte justement l'upload
- [ ] Si elle est fusionnée : réexaminer le stockage des photos **en base**, choix assumé face aux systèmes de fichiers éphémères de Railway/Render, à revoir à l'échelle d'une chaîne

---

## Phase 20 — Mettre en ligne, pour de vrai

**Mode d'emploi pas à pas : [`terrain/MISE_EN_LIGNE.md`](./terrain/MISE_EN_LIGNE.md)**
**Budget chiffré et sourcé : [`AUDIT_COUTS_PRODUCTION.md`](./AUDIT_COUTS_PRODUCTION.md)**

**Bloquant avant la première commande d'un vrai client.** Un pilote qui perd son
service du soir ne revient pas, et il le racontera aux autres patrons du
quartier — c'est le seul incident dont le coût dépasse celui du produit.

Tout ici demande un compte ou une carte bancaire de Wassim.

- [ ] Choisir et provisionner l'hébergement 🧑 — backend dockerisé sur Railway ou Render (WebSocket natif + Postgres managé), frontend sur Vercel. Contrainte à respecter : **une seule instance backend** (gestionnaire WebSocket et limiteur de débit en mémoire)
- [ ] Réserver le domaine 🧑 (`tawla.tn` en priorité, `.com` en secours)
- [ ] Générer les vraies clés en variables d'environnement 🧑 : `JWT_SECRET`, `FRONTEND_ORIGIN` sur l'origine exacte de prod, paire VAPID, `FORWARDED_ALLOW_IPS` (cf. 19bis.2 S-2a)
- [ ] Activer les sauvegardes automatiques du Postgres managé 🧑
- [ ] **Restaurer une sauvegarde une fois, sur une base jetable** 🧑 — une sauvegarde jamais restaurée n'est pas une sauvegarde. C'est la seule ligne de cette phase qu'on sera tenté de sauter, et la seule qui prouve les autres
- [ ] Brancher le monitoring externe sur `/health` 🧑 (UptimeRobot gratuit) — la sonde interroge déjà la base et renvoie 503 si elle est injoignable
- [ ] Collecte des erreurs 🧑 — log drain de l'hébergeur, ou Sentry si un DSN existe. Les logs sortent déjà en JSON sur stdout : ne rien coder avant d'avoir la destination
- [ ] Rejouer le parcours complet sur staging — client, serveur, cuisine, manager — puis bascule finale 🧑
- [ ] Déclaration du traitement des numéros de fidélité auprès de l'INPDP 🧑 (`inpdp.tn`) — avant le premier client réel, pas après. Le produit est conforme depuis la Phase 16 ; il manque le dépôt

**20.1 — Les trois vérifications que seule la production permet** (héritées de
la Phase 19.3 et de l'audit — aucune n'est constatable en local, et aucune ne
doit être cochée sur une supposition)

- [x] **Mesurer** le limiteur derrière le vrai proxy — fait le 2026-08-18 sur `tawla-backend.onrender.com` (24 requêtes réelles, log temporaire du pair TCP / `X-Forwarded-For` / `CF-Connecting-IP`). Confirmé qu'aucun `429` n'apparaissait avant correctif, et qu'il apparaît à la 21ᵉ requête après (PR #57)
- [x] Vérifier que le conteneur n'est **joignable que** par le proxy de l'hébergeur — reformulé par le correctif : ce n'est plus le proxy Render qui compte (son IP interne tourne, sans valeur), mais Cloudflare, qui fronte Render même sur `onrender.com` brut et rejette en 403 toute tentative de forger `CF-Connecting-IP` (testé). À réaffirmer si le DNS du domaine final passe un jour hors du proxy Cloudflare ("grey-cloud")
- [ ] Confirmer sur le domaine réel que `isSecureContext` est vrai 🧑 — notifications push, service worker et `crypto.randomUUID` en dépendent (cf. C-1)

**Critère de sortie de phase** : une commande passée depuis un téléphone sur le
domaine réel, vue sur l'écran cuisine, avec une sauvegarde restaurée la veille.

---

## Phase 21 — Vingt entretiens de restaurateurs 🧑

**Mode d'emploi : [`terrain/GUIDE_ENTRETIEN.md`](./terrain/GUIDE_ENTRETIEN.md) — comment obtenir les rendez-vous, puis comment mener la conversation.**

**La ligne la plus lourde de la grille (20 %), notée 2,0, et la seule qui
conditionne toutes les suivantes.** Elle n'attend rien : elle peut démarrer le
jour où la Phase 19bis est en revue, sans attendre la mise en ligne.

Le matériel existe depuis la Phase 13 et n'a jamais servi : au 2026-08-18,
`terrain/ENTRETIENS.md` porte toujours **vingt lignes vides**.

- [ ] Mener les 20 entretiens 🧑 — restaurants et brasseries de **6 tables et plus** (Tunis, La Marsa, Sousse, Hammamet), pas les petits cafés. Ne jamais montrer l'application avant la fin
- [ ] Remplir `terrain/ENTRETIENS.md` sur place ou juste après 🧑 — une ligne par établissement, et les verbatims mot pour mot, surtout les refus
- [ ] Poser la question de prix franchement, après avoir décrit le bénéfice et jamais la fonctionnalité 🧑
- [ ] Repérer les trois profils de pilote au passage 🧑 : café de quartier, restaurant de centre-ville, zone touristique. Chercher celui dont les autres patrons parlent, pas le plus accueillant
- [ ] Écrire la synthèse 🧑 : les trois douleurs les plus citées, le prix médian accepté, l'écart entre le prix spontané et la réaction à 120 DT

**21.1 — La coupe** (ce qui rend cette phase utile au produit, et pas seulement
au commercial)

La synthèse doit produire un **retrait**, pas un ajout. Une fonctionnalité
qu'aucun des vingt n'a mentionnée spontanément est candidate à la suppression —
pas au maintien « au cas où ».

- [ ] Trancher le sort des trois candidats déjà identifiés par `AUDIT_FINAL.md` 🧑 : partage d'addition (noté 6,0), mode café (6,5), célébration et carte à partager (4,0). Les retirer coûte moins cher que les maintenir dans chaque écran, chaque traduction et chaque test
- [ ] Écrire la coupe dans cette roadmap avec la raison, même si la décision est « on garde »
- [ ] Si l'addition par table remonte spontanément chez plusieurs patrons, c'est la **seule** fonctionnalité qui remonte en Phase 23 ; sinon elle reste en § « Sous condition »

---

## Phase 22 — Un seul prix 🧑

Décision qui n'attend aucune donnée nouvelle : elle est écrite dans deux
documents et attendue par une constante `null` dans le code
(`frontend/lib/offer.ts:18`, toujours `PRICE_MONTHLY_DT = null` au 2026-08-18).

- [ ] Fixer le prix unique 🧑 — proposition tenue depuis la revue : **120 DT/mois, service d'installation inclus**, cible 45 établissements. 45 × 120 DT ≈ 65 k DT/an tenable seul, contre 290 clients à 35 DT pour un revenu comparable et une charge de support intenable
- [ ] Renseigner `PRICE_MONTHLY_DT` dans `frontend/lib/offer.ts` — la page publique affiche alors le montant sans autre changement de code
- [ ] `Restaurant.pilot_ends_on` + bandeau « pilote gratuit jusqu'au JJ/MM » sur le dashboard + migration. Rend l'échéance explicite au lieu d'une conversation gênante à avoir. **Ne pas coder avant que le prix soit tranché** : un bandeau qui n'annonce aucune suite ne sert à rien
- [ ] Facturation : facture mensuelle **manuelle** pour les dix premiers clients (un virement ou un chèque). N'automatiser qu'au-delà — YAGNI strict
- [ ] Ne pas activer la facturation avant la fin de la phase pilote gratuite

**Le prix ne bouge jamais. Le périmètre, oui.** La première remise tue le
positionnement définitivement, et elle se saura — dans un milieu où tout le
monde se parle. Face à une négociation : donner du temps (quatre semaines
gratuites), jamais des dinars.

---

## Phase 23 — Les trois pilotes

**Modes d'emploi : [`terrain/RELEVE_AVANT.md`](./terrain/RELEVE_AVANT.md) (la semaine de référence), [`terrain/FORMATION_10MIN.md`](./terrain/FORMATION_10MIN.md) et [`terrain/PRISE_EN_MAIN.md`](./terrain/PRISE_EN_MAIN.md) (installation et équipe).**

C'est ici que la note « besoin marché prouvé » se gagne, et nulle part ailleurs.
Au 2026-08-18, `terrain/PILOTES.md` ne contient qu'un modèle à copier.

**23.1 — Avant d'installer quoi que ce soit** 🧑

- [ ] Disqualifier à la porte 🧑 : pas de Wi-Fi utilisable ou de réseau à toutes les tables → ne pas installer, même s'il insiste. Moins de six tables → la douleur est trop faible pour 120 DT. Une terrasse est le signal positif le plus fort
- [ ] Accord écrit d'une page par pilote 🧑 : quatre semaines d'usage **effectif en service**, droit de citer le nom, droit de publier les chiffres mesurés, et en échange installation, formation, chevalets et support pendant le service. Un pilote qui refuse le droit de citation est un client gratuit, pas un pilote
- [ ] **Relever la semaine de référence à la main, avant activation** 🧑 : commandes perdues par service et panier moyen, comptés sur place pendant quatre soirs. Sans cet « avant », la preuve d'après ne vaut rien — et c'est le seul travail de cette roadmap qui devient impossible à rattraper une fois l'outil installé
- [ ] Arriver avec **sa** carte déjà chargée 🧑 (`setup_restaurant.py` + import CSV) et lui faire scanner son propre QR. « Voilà votre carte, elle tourne » ne se rattrape par aucun argument

**23.2 — L'audit d'avant devient un écran** (à coder **quand le premier relevé
existe**, pas avant : un écran qui n'a rien à afficher n'est pas une
préparation)

- [ ] `Restaurant.baseline_lost_orders_per_day`, `baseline_avg_basket`, `baseline_measured_on` + migration + `model_registry.py`
- [ ] Saisie depuis le dashboard manager, avec la date du relevé — rien d'affiché tant que ce n'est pas saisi
- [ ] `/dashboard/preuve` affiche « avant Tawla » en face de « mesuré » quand le relevé existe. C'est **la** capture d'écran qui vend le passage au payant
- [ ] Ne jamais inventer ni pré-remplir ces valeurs : un chiffre « avant » inventé rend toute la démonstration mensongère, et la mesure est la seule chose que Tawla a à vendre

**23.3 — Les quatre semaines** 🧑

- [ ] Former l'équipe sur place, dix minutes pendant un service creux (`terrain/FORMATION_10MIN.md`) 🧑
- [ ] **Convaincre les serveurs avant le patron** 🧑 — « tu ne prends plus les commandes, tu les confirmes ». Traiter de front le sujet du téléphone personnel (batterie, forfait), et proposer au patron de fournir un téléphone de salle. Le personnel de salle est le premier saboteur possible de cet outil
- [ ] Répéter le repli papier **avant** d'en avoir besoin, pas le soir où le réseau tombe 🧑
- [ ] Tenir `terrain/PILOTES.md` le soir même de chaque service observé 🧑 : incidents, verbatims, ce qui a été contourné ou jamais utilisé
- [ ] Relever les trois métriques chaque semaine sur `/dashboard/preuve` 🧑
- [ ] Confronter les seuils codés au réel 🧑 : `ABANDONED_PENDING_AFTER` (10 min) et le seuil de fin de service de 5 h (`app/core/dates.py:16`) sont des propositions, pas des vérités
- [ ] Confronter le plan de salle aux entretiens 🧑 : les zones suffisaient-elles, ou le plan dessiné change-t-il vraiment la conversation ?
- [ ] Vérifier en service réel que le plafond du limiteur tient 🧑 — c'est le premier endroit où vingt tables commandent vraiment dans la même minute (cf. 19bis.2 S-2b)

**23.4 — Ce qui sort des pilotes**

- [ ] Remplir `PILOT_RESULTS` dans `frontend/lib/offer.ts` avec des chiffres réellement relevés chez un établissement qui a donné son accord écrit pour être cité
- [ ] Écrire la réponse à « pourquoi toi et pas Digital Menu à 39 DT » **dans les mots d'un patron pilote**, pas dans les nôtres

---

## Phase 24 — Les deux clients payants

Le passage de « produit » à « entreprise ». C'est la seule phase dont la
réussite ne dépend d'aucune ligne de code.

- [ ] Deux des trois pilotes passent à l'abonnement payant 🧑
- [ ] Première facture émise et encaissée 🧑
- [ ] Mesurer les deux chiffres qui décident de la suite 🧑 : durée réelle d'une installation, et minutes de support par client et par semaine. Le modèle à 45 clients suppose une heure et quelques minutes ; si l'installation prend une demi-journée, la cible est 20 clients, pas 45 — et il vaut mieux l'apprendre au deuxième client qu'au vingtième
- [ ] Instrumenter la rétention : compter les ouvertures du tableau de bord par établissement et par semaine. Le produit sait dire ce qu'un restaurant encaisse, pas si son patron l'a regardé — or c'est ce signal qui précède une résiliation de deux mois. Une colonne suffit, à ne coder qu'ici : avant deux clients payants, il n'y a rien à retenir

---

## Sous condition — ne pas ouvrir sans le déclencheur nommé

Chaque ligne est une chose qu'il serait tentant de construire. Le déclencheur
est la condition **exacte** qui la ferait entrer dans la roadmap.

| Chantier | Déclencheur |
|---|---|
| **Addition au niveau de la table** — vérifié le 2026-08-18 : `payment_status` vit sur `Order`, et les commandes ouvertes multiples (PR #52) font qu'une table qui commande en deux temps produit deux additions séparées | Trois patrons sur vingt le mentionnent **spontanément** en Phase 21 |
| **Formules / menus du jour** | Idem — trois mentions spontanées |
| **Tests frontend** (aucun aujourd'hui, sur 8 466 lignes) — C-1 et D-1 auraient été attrapés par un test de rendu, mais aucun pilote ne les a constatés | Un bug de panier constaté **chez un pilote**, ou un deuxième développeur qui touche `menu/[qrToken]/page.tsx` |
| **Découper les deux fichiers de plus de 1 000 lignes** (`menu/[qrToken]/page.tsx` : 1 516 ; `dashboard/page.tsx` : 1 292) | Le même déclencheur que ci-dessus. Un refactor qui ne corrige aucun bug ne rapproche d'aucun client |
| **Intégration Konnect réelle** (le paiement carte reste simulé) | Un pilote qui le réclame. **F-5 doit être fermé avant**, pas après |
| **Intégration caisse / stock** | Dix prospects qui la citent comme motif de refus. C'est un autre produit, et la vraie douleur du patron |
| **Plusieurs instances backend** (WebSocket et limiteur en mémoire ; S-6 en est un symptôme) | Une coupure de service constatée en pleine soirée, ou le 30ᵉ client |
| **Multi-établissements sous un même compte** | Un client qui possède deux établissements et le demande |
| **Mode sombre côté client** | Un retour de pilote sur la lisibilité en terrasse le soir |

## Hors périmètre, définitivement

- **Expansion régionale** (Algérie, Maroc, Libye) — seul chemin compatible avec une levée, donc hors sujet depuis le cadrage « entreprise rentable et non diluée ». Trois conquêtes commerciales distinctes pour un fondateur seul
- **Trois paliers d'abonnement** — remplacés par un prix unique. `Restaurant.subscription_tier` reste en base sans coût, et **aucun gating n'est codé** : bloquer une fonctionnalité déjà utilisée par un pilote casserait son service sans aucun bénéfice
- **Grands groupes, événements, réservations de salle** — Wassim a choisi de ne pas cadrer ; ne pas relancer
- **SMS au client, imprimante cuisine matérielle, montée de version Next.js** — arbitrages déjà tranchés (cf. archive)

---

## Ce qui est déjà livré (phases 12 à 19, closes)

Résumé destiné à ce fichier ; le détail par tâche vit dans l'historique git et
dans les PR citées.

| Phase | Ce qu'elle a livré | PR |
|---|---|---|
| **12.1** | Comptes serveur et cuisine créés par le manager, `Staff.is_active` vérifié à chaque requête, onglet Équipe | #36 |
| **12.2** | Surface publique fermée : `Order.public_token`, `qr_token` exigé à la création, `loyalty_phone` sorti de la vue client, WebSockets authentifiés, `POST /restaurants` supprimé | #36, #44 |
| **12.3** | Alembic seule voie du schéma, test de conformité modèles/migrations, sonde `/health` qui interroge la base | #36, #41, #43 |
| **13.2** | Kit d'installation : `setup_restaurant.py`, import CSV, chevalets QR, fiches de prise en main et de formation | #37 |
| **13.3** | Les trois métriques de preuve, `/dashboard/preuve`, export CSV, définition codée de « commande perdue » | #37 |
| **14.1** | Vente incitative « avec ce plat » et son effet **mesuré** (`OrderItem.from_suggestion`) | #38 |
| **14.2** | Page publique « service inclus », rapport hebdomadaire par serveur, jamais de statistiques nominatives en salle | #39 |
| **15** | Tenue en service réel : écran cuisine à 360 px, repli papier, session expirée gérée, test de charge | #39, #45 |
| **16** | Conformité 2004-63 : consentement au-dessus du champ, politique fr/ar, rétention et purge réelle | #40 |
| **17** | Recette du jour et commandes perdues en tête du dashboard, encart « ma soirée » sur l'écran serveur | #46 |
| **18** | Plan de salle : édition par glisser-déposer, vue serveur en direct, action depuis la table, couverts dessinés | #47, #48, #49, #50 |
| **19** | `/loyalty/lookup` fermée, création de commande idempotente (`client_order_id`), limiteur sur l'IP réelle, échappement de `table_label`, `<html lang>`, journée de service bornée à 5 h | #51 |
| **19 (suite)** | Recette limitée aux commandes réglées, résolution d'appel serveur poussée au client, commandes ouvertes multiples, durées par étape, cuisine en deux colonnes, note partageable, plats partagés par convive, rupture barrée | #52 |
| **Audit** | Audit de pré-lancement : 299 tests, parcours rejoués, attaques mesurées, 20 constats, grille recalculée | #54 |

Ce qui restait ouvert de ces phases a été repris ci-dessus, sans perte : la
vérification du limiteur derrière le vrai proxy (→ 20.1), la mise en ligne
(→ 20), les entretiens et les pilotes (→ 21, 23), le prix (→ 22), l'écran de
relevé « avant » (→ 23.2), le bandeau de fin de pilote (→ 22), et
`active_orders_count` non borné, jusqu'ici « hors périmètre » (→ 19bis.1 F-2).

---

## Comment travailler cette roadmap (pour Claude Code)

1. **Une tâche = une branche = une PR.** Jamais de push direct sur `main`. CI verte avant merge.
2. **Ordre strict**, sauf la Phase 21 (les entretiens) qui tourne en parallèle et n'attend aucun code.
3. **Phase 19bis : écrire le test qui échoue d'abord**, puis le correctif. Un correctif de sécurité ou d'intégrité sans test qui le prouve ne compte pas comme livré — sauf les deux lignes marquées *(sans test)*, où la vérification est manuelle par nature.
4. **Cocher `[x]` avec le numéro de PR**, et si le scope a été réduit, écrire pourquoi sur la ligne.
5. **À la clôture d'une phase, recalculer la grille** — sur ce qui est constaté, jamais sur ce qui est préparé. Si une phase n'a déplacé aucune note, le dire dans la PR : c'est le signal que la tâche n'aurait pas dû être faite.
6. **Après la Phase 20, toute proposition de code doit nommer le restaurateur qui l'a demandée.** Sans nom, elle va en § « Sous condition ». Un **défaut constaté** échappe à cette règle — un manque fonctionnel, jamais.
7. **Ne jamais cocher une case sur une supposition.** Les trois lignes de 20.1 sont là parce qu'un test vert en local a déjà laissé passer un contournement réel du limiteur : `TestClient` n'exécute pas la couche qui, en production, réécrit l'IP.
8. **Ne jamais remplir `terrain/*` depuis une session.** Ces fichiers se tiennent à la main, sur place. Un chiffre de terrain inventé détruit la seule chose que Tawla a à vendre.
9. **Conventions inchangées** : voir `CLAUDE.md` (multi-tenant partout, transitions d'état contrôlées, prix figé sur `OrderItem`, tout nouveau modèle dans `model_registry.py`, toute migration dans la même PR, logs via `log_event`).
10. **Face à une ambiguïté produit** : livrer le scope le plus étroit qui règle le problème réel, et signaler l'ambiguïté dans la PR — plutôt que d'inventer une réponse.
