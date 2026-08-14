# Tawla — Roadmap

Fichier unique de pilotage du projet. Prendre la première tâche non cochée en
partant du haut, dans l'ordre des phases. Une tâche cochée `[x]` doit mentionner
la PR qui l'a livrée. Les tâches marquées 🧑 demandent une décision, un compte
réel ou une présence physique de Wassim — elles ne sont jamais faisables en
autonomie.

Historique des phases 0 à 11 : [`ROADMAP_ARCHIVE.md`](./ROADMAP_ARCHIVE.md).
Revue d'investissement qui fonde cette roadmap :
[`REVUE_INVESTISSEURS.md`](./REVUE_INVESTISSEURS.md).
Audit fonctionnel et business orienté vente, et les dix recommandations pour
les premiers clients : [`PREMIERES_VENTES.md`](./PREMIERES_VENTES.md).

## Objectif

**Passer de 5,3/10 à 8/10 au prochain jury d'investisseurs.**

L'objectif produit n'a pas changé (un service fluide en salle, une visibilité
complète pour le manager). Ce qui change, c'est la nature du travail : les
phases 0 à 11 ont construit un produit sans jamais le confronter à un
restaurant. Les phases 12 à 16 fabriquent la preuve qui manque, et ferment les
deux trous qui rendent aujourd'hui le produit invendable.

**Décision de cadrage (Wassim, 2026-08-13) : Tawla est une entreprise rentable
et non diluée, pas un dossier de levée de fonds.** Toute la roadmap en découle —
notamment le prix (moins de clients mieux payés, cf. Phase 14.3) et le refus de
l'expansion régionale (cf. § hors périmètre).

## La grille du jury, et ce qui déplace chaque note

C'est l'instrument de pilotage de cette roadmap : chaque phase existe pour
déplacer une ligne de ce tableau. Recalculer la colonne « actuelle » à la
clôture de chaque phase.

| Dimension | Poids | Actuelle | Cible | Ce qui la déplace | Phase |
|---|---:|---:|---:|---|---|
| Accès au marché & vente | 20 % | 2,0 | 7,5 | 20 entretiens, 3 pilotes actifs, 2 clients payants — le plan de salle est l'écran qui fait comprendre Tawla en deux secondes | 13, 18 |
| Prêt à vendre (installable, sûr) | 15 % | 8,5 | 9,0 | ~~Comptes staff~~, ~~surface publique fermée~~, ~~kit d'installation~~, ~~conformité 2004-63~~, reste le déploiement avec sauvegardes | 12, 13.2, 16 |
| Besoin marché prouvé | 20 % | 7,0 | 8,5 | Les 3 métriques mesurées avant/après chez un pilote | 13.3 |
| Viabilité économique | 20 % | 7,0 | 8,0 | Un prix réellement payé par deux établissements, et un outil qu'on rouvre tous les soirs | 14.3, 17 |
| Différenciation sur une niche | 10 % | 6,5 | 7,5 | ~~Vente incitative~~, ~~positionnement service~~, ~~angle primes~~ — reste un chiffre venu d'un vrai pilote | 14 |
| Exécution technique | 15 % | 9,0 | 9,0 | ~~Tests de sécurité dédiés~~, ~~tenue en service réel~~ (atteint) | 12.2, 15 |
| **Note pondérée** | **100 %** | **6,5** | **8,2** | | |

Mise à jour du 2026-08-13 (clôture de 12.1 et 12.2) : « prêt à vendre » passe de
2,5 à 7,0 — le produit est désormais installable par un restaurateur et sa
surface publique est fermée, vérifié par 36 tests dédiés et un parcours complet
rejoué en navigateur. Il reste le déploiement réel et les sauvegardes, qui
demandent des comptes de Wassim. « Exécution technique » passe à 9,0 : les
correctifs de sécurité sont couverts par des tests nommés d'après chaque
constat, pas seulement corrigés.

Mise à jour du 2026-08-13 (13.2 et 13.3) : « prêt à vendre » passe à 8,0 —
installer un pilote est passé d'une dizaine d'appels Swagger enchaînés à la main
sur place à une seule commande, chevalets imprimables et fiche de remise
compris. Il reste le déploiement réel.

Mise à jour du 2026-08-13 (14.1) : « différenciation » passe de 4,0 à 5,5 — la
vente incitative existe et son effet est **mesuré** (panier moyen avec et sans
suggestion acceptée, sur la même période et le même établissement). C'est le
seul chiffre du produit qui se cite en rendez-vous. La note n'atteint pas la
cible parce qu'il manque encore le positionnement « service inclus » (14.2) et
un chiffre issu d'un vrai restaurant, pas d'un jeu de données de test.

Mise à jour du 2026-08-13 (16) : « prêt à vendre » passe à 8,5 — un produit qui
collecte des numéros de téléphone sans dire à quoi ils servent ni les supprimer
jamais n'est pas vendable à un restaurateur qui, lui, sera le responsable du
traitement. La finalité est maintenant écrite au-dessus du champ, la politique
de confidentialité existe en français et en arabe, et la purge est un script
réel — vérifié en le lançant, pas seulement en le lisant. Il reste la
déclaration INPDP (🧑) et le déploiement, qui demandent Wassim.

**Correction du total pondéré** : le tableau affichait 6,6 alors que ses propres
lignes donnaient 6,4. Recalculé ici (6,5 avec la nouvelle note de « prêt à
vendre »). Le total n'était pas faux dans les conclusions qu'il servait, mais un
instrument de pilotage qui ne s'additionne pas ne pilote rien.

**Ces sous-phases n'ont déplacé aucune autre note, et c'est normal** :
elles construisent l'instrument de mesure et l'outil d'installation, pas la
preuve elle-même. « Besoin marché prouvé » ne bougera qu'avec des chiffres
relevés chez un vrai restaurant, et « accès au marché » qu'avec des entretiens
menés. Ces deux lignes portent 40 % du poids cumulé et **aucune ligne de code ne
peut plus les faire monter** — tout ce qui reste à faire pour atteindre 8/10
passe par la porte d'un restaurant.

## Où en est la roadmap, et ce qui reste

**Toutes les tâches réalisables sans sortir de la machine sont faites** (phases
12.1, 12.2, 12.3-code, 13.2, 13.3, 14.1, 14.2, 15, 16, 17.1, 17.3). Ce qui reste
tient en trois blocs, dans cet ordre — et aucun ne se code (17.2 attend le
relevé d'un vrai établissement, 17.4 le prix tranché) :

1. **Mettre en ligne** (12.3) — hébergement, domaine, clés, **sauvegardes**,
   moniteur branché sur `/health`. Les sauvegardes sont bloquantes avant la
   première commande réelle : un pilote qui perd son service du soir ne
   revient pas.
2. **Aller voir des restaurateurs** (13.1) — 20 entretiens. C'est la ligne qui
   pèse le plus lourd (20 % de la grille, notée 2,0) et la seule qui
   conditionne les suivantes : la synthèse doit provoquer une **coupe** dans
   cette roadmap, pas un ajout.
3. **Trois pilotes, puis deux clients payants** (13.4, 14.3) — avec la semaine
   de mesure **avant** activation, sinon la preuve ne vaut rien. Fixer le prix
   au passage, et déposer la déclaration INPDP avant le premier client réel.

Le produit est prêt pour ces trois blocs : installable en une commande, sûr,
conforme, avec l'instrument de mesure déjà en place. **Écrire du code
supplémentaire maintenant ferait baisser la note**, en repoussant la seule
chose qui manque.

---

## Phase 12 — Rendre le produit vendable (bloquant absolu)

Rien de cette phase n'est optionnel et rien après elle n'a de sens avant. Deux
constats de la revue en sont l'origine : le produit n'est aujourd'hui pas
installable par un client, et sa surface publique laisse lire les commandes de
n'importe quel restaurant.

**12.1 — Comptes serveur et cuisine** (sans ça, il n'y a littéralement rien à
vendre : un manager onboardé en self-service ne peut donner accès ni au pool
serveur ni à l'écran cuisine)

- [x] `Staff.is_active` (booléen, défaut `True`) + migration Alembic + vérification dans `staff/dependencies.py::get_current_staff` — un compte désactivé doit être refusé même avec un JWT déjà émis et encore valide (PR #36)
- [x] `POST /api/v1/staff` (manager uniquement, `staff/router.py`) — crée un compte serveur ou cuisine. `restaurant_id` **toujours** pris sur le JWT du manager, jamais accepté depuis le payload (cf. la faille d'isolation déjà corrigée sur `assign-staff`) (PR #36)
- [x] `GET /api/v1/staff/by-restaurant/{restaurant_id}` (manager) — liste de l'équipe avec rôle et état (PR #36)
- [x] `PATCH /api/v1/staff/{staff_id}` (manager) — renommer, changer de rôle, activer/désactiver. Refuser la désactivation du dernier manager actif du restaurant (PR #36)
- [x] `POST /api/v1/staff/{staff_id}/reset-password` (manager) — régénère un mot de passe et le renvoie **une seule fois** dans la réponse ; le manager le transmet de la main à la main (aucun service d'e-mail dans le projet, cohérent avec l'existant) (PR #36)
- [x] Onglet « Équipe » dans le dashboard manager (`frontend/app/dashboard/page.tsx`, même pattern que l'onglet « Tables & zones ») : liste, création, édition, désactivation, réinitialisation de mot de passe (PR #36)
- [x] Tests (`backend/tests/test_staff_management.py`) : un manager ne crée que dans son restaurant ; un serveur ou un compte cuisine ne peut pas créer de compte (403) ; un compte désactivé ne peut plus se connecter **ni utiliser son JWT existant** ; le dernier manager actif n'est pas désactivable — 16 tests (PR #36)

**12.2 — Fermer la surface publique du parcours client** (les sept constats de
la revue ; le parcours client reste sans compte, mais chaque appel doit être
lié à la table qui a scanné ou à la commande créée)

- [x] `Order.public_token` — `secrets.token_urlsafe(32)` comme `Table.qr_token`, généré à la création, renvoyé **une seule fois** dans la réponse de `POST /orders`, jamais dans une autre réponse. Migration Alembic + `model_registry.py` (PR #36)
- [x] Exiger ce token (en-tête `X-Order-Token`) sur `GET /orders/{id}`, `pay/card`, `pay/cash` et `push-subscription` — répondre `404 ORDER_NOT_FOUND` sans lui, jamais `403` (ne pas confirmer l'existence de la commande) (PR #36)
- [x] `OrderCreate` prend le `qr_token` de la table au lieu de `table_id` brut (`restaurant_id` en est déduit) — le frontend l'a déjà dans son URL. C'est ce qui empêche d'injecter une commande dans un service en cours sans avoir scanné (PR #36)
- [x] Retirer `loyalty_phone` de `OrderOut`. Les écrans staff qui en ont besoin (demande de paiement cash, badge fidélité) passent par un schéma séparé `OrderOutStaff`, servi uniquement aux routes authentifiées (PR #36)
- [x] JWT obligatoire sur `/ws/staff/{restaurant_id}` et `/ws/kitchen/{restaurant_id}` — token en paramètre de requête, compte actif et `restaurant_id` du token vérifiés. **Écart assumé par rapport au plan** : le refus accepte la poignée de main puis ferme aussitôt en 4401, au lieu de fermer avant `accept()`. Un rejet avant `accept()` arrive au navigateur en code 1006, indistinguable d'une coupure réseau — le hook de reconnexion martelait alors sans fin un canal interdit. La socket n'est jamais enregistrée dans le `ConnectionManager` et aucun message n'est émis, donc l'accès reste nul ; le frontend, lui, peut désormais renvoyer vers `/login` (PR #36)
- [x] `/ws/order/{restaurant_id}/{order_id}` — exiger le `public_token` en paramètre, même règle (PR #36)
- [x] `POST /loyalty/lookup` — appliquer `rate_limit` et retirer `birth_date` de la réponse publique (le bandeau anniversaire est calculé côté serveur, le client n'a pas besoin de la date). Empêche de tester si un numéro est client d'un établissement (PR #36)
- [x] Supprimer `POST /api/v1/restaurants` (`tenants/router.py`) — inutile depuis `/auth/register`, et ouvert. Remplacer son usage dans les ~9 fichiers de tests par un helper `create_restaurant()` de `conftest.py` qui écrit directement en base (PR #36)
- [x] `backend/tests/test_public_surface.py` — **un test par constat de la revue**, nommé d'après lui : lecture anonyme d'une commande, énumération par ID séquentiel, paiement carte anonyme, création de commande sans `qr_token`, énumération fidélité, WebSocket staff sans token, création de restaurant anonyme. Chaque test doit échouer sur le code d'avant la phase et passer après — 20 tests (PR #36)
- [x] Vérifier qu'aucun `restaurant_id`/`table_id`/`order_id` ne sert plus de secret nulle part (audit rapide des routers, à noter dans la description de PR) (PR #36)
- [x] Reprise de l'audit, une route avait survécu (PR #44) : `GET /restaurants/{id}` était publique et incrémentale — parcourir 1, 2, 3… donnait la liste des établissements clients de Tawla avec leur formule d'abonnement. Remplacée côté client par `GET /restaurants/by-token/{qr_token}`, qui ne sert que le nom et les réglages de service ; la fiche complète passe sous JWT et refuse un autre établissement

**12.3 — Mise en production réelle** (reprise des tâches non faites de
l'ancienne Phase 10, désormais débloquées par le choix d'hébergeur)

- [x] Basculer sur Alembic : retirer `create_all()` de `backend/app/main.py`, la migration initiale et celles des phases 12.1/12.2 devenant la seule voie (PR #36)
- [x] Garantir que les migrations décrivent vraiment les modèles (PR #43) — c'était le seul écart que la CI ne pouvait pas voir : elle teste sur un schéma `create_all()`, la production tourne sur Alembic. Un champ ajouté sans migration passait tous les tests et cassait en plein service
- [ ] Choisir et provisionner l'hébergement 🧑 — backend dockerisé sur Railway ou Render (WebSocket natif + Postgres managé), frontend sur Vercel. Contrainte à respecter : **une seule instance backend** (gestionnaire WebSocket et limiteur de débit en mémoire, cf. `notifications/manager.py`)
- [ ] Réserver le domaine 🧑 (`tawla.tn` en priorité, `.com` en secours)
- [ ] Générer les vraies clés en variables d'environnement 🧑 : `JWT_SECRET`, `FRONTEND_ORIGIN` sur l'origine exacte de prod, paire VAPID
- [ ] Activer les sauvegardes automatiques du Postgres managé 🧑 — **bloquant avant la première commande réelle**
- [x] Rendre `/health` digne d'un monitoring : la sonde interroge la base et renvoie 503 si elle est injoignable (PR #41). Avant, elle renvoyait « ok » sans rien vérifier — un moniteur branché dessus aurait certifié que tout allait bien pendant qu'aucune commande ne passait
- [ ] Brancher le monitoring externe sur `/health` 🧑 (UptimeRobot gratuit) — le code est prêt, il manque le compte et l'URL de prod
- [ ] Collecte des erreurs 🧑 — Sentry (offre gratuite) ou log drain de l'hébergeur. Rien à coder d'ici là : les logs backend sortent déjà en JSON sur stdout (`app/core/logging.py`), qu'un log drain ramasse tel quel. Ne pas ajouter le SDK Sentry avant d'avoir un DSN : une dépendance inutilisable en production n'est pas une préparation
- [ ] Rejouer le parcours complet (client / serveur / cuisine / manager) sur staging avant la bascule, puis bascule finale 🧑

---

## Phase 13 — Fabriquer la preuve terrain

La dimension la plus lourde du jury (20 %) est notée 2/10 pour une seule
raison : aucun restaurateur n'a été rencontré. C'est la seule phase que le code
ne peut pas résoudre — mais le code peut la rendre facile à exécuter, et c'est
l'objet de 13.2 et 13.3. **Les entretiens (13.1) peuvent démarrer en parallèle
de la Phase 12, ils n'attendent rien.**

**13.1 — Vingt entretiens de restaurateurs** (avant de montrer l'application)

- [x] Rédiger le guide d'entretien (`terrain/GUIDE_ENTRETIEN.md`) : ouvrir sur « qu'est-ce qui te fait perdre de l'argent chaque semaine ? », ne jamais montrer l'app avant la fin, une question de prix posée franchement (« combien tu paierais par mois pour ça ? » après avoir décrit le bénéfice, jamais la fonctionnalité) (PR #37)
- [x] Tableau de dépouillement (`terrain/ENTRETIENS.md`) : une ligne par établissement — type, nombre de tables, douleur citée en premier, outil déjà utilisé, prix accepté, objection principale, verbatim marquant (PR #37)
- [ ] Mener les 20 entretiens 🧑 — cible : restaurants et brasseries de 6 tables et plus (Tunis, La Marsa, Sousse, Hammamet), pas les petits cafés
- [ ] Synthèse : les trois douleurs les plus citées, le prix médian accepté, et ce qui dans la roadmap devient inutile au vu des réponses (attendre une coupe, pas un ajout)

**13.2 — Kit d'installation d'un pilote** (ce que Claude Code peut préparer pour
que Wassim installe un restaurant en une heure)

- [x] Script d'installation guidée (`backend/scripts/setup_restaurant.py`) : crée le restaurant, le manager, l'équipe, les tables avec leurs zones, importe une carte depuis un CSV, et génère tous les QR en une passe — l'alternative actuelle est une dizaine d'appels Swagger (PR #37)
- [x] Import de carte en CSV depuis le dashboard manager (nom, description, catégorie, prix, piment, allergènes) — saisir 30 plats à la main est le premier abandon probable d'un patron (PR #37)
- [x] Fiche de prise en main, une page, fr + ar (`terrain/PRISE_EN_MAIN.md`) : ce que fait le serveur, ce que fait la cuisine, quoi faire si le Wi-Fi tombe (PR #37)
- [x] Script de formation du personnel en 10 minutes (`terrain/FORMATION_10MIN.md`) — déroulé exact, à jouer pendant un vrai service (PR #37)
- [x] Vérifier le rendu des QR sur support imprimé réel (`generate_table_qr.py` existe ; valider taille, contraste et lisibilité à 30 cm sur un chevalet de table) (PR #37)

**13.3 — Instrumenter les trois métriques qui valent de l'argent**

Rien d'autre. Ni tableau de bord supplémentaire, ni graphique de plus : ces
trois chiffres, mesurables avec les horodatages déjà présents sur `Order`.

- [x] Définir « commande perdue » dans le code : commande annulée + commande restée en `pending_confirmation` au-delà d'un seuil (proposer 10 min, à confirmer avec un pilote) — constante nommée et documentée dans `orders/service.py` (PR #37)
- [x] `GET /api/v1/stats/preuve/{restaurant_id}` (manager) — pour une plage de dates : commandes perdues, délai moyen commande → arrivée en cuisine, panier moyen, nombre de commandes. Réutiliser `stats/service.py` (PR #37)
- [x] Page `/dashboard/preuve` : les trois chiffres, semaine courante contre semaine précédente, avec l'écart en pourcentage. C'est la page que Wassim montre au patron à la fin du pilote — et au jury (PR #37)
- [x] Export CSV de cette page (même mécanique client que `/dashboard/stats`) (PR #37)
- [ ] Mesurer une semaine de référence **avant** d'activer la commande QR chez chaque pilote (saisie manuelle par le patron : commandes perdues et panier moyen) — sinon il n'y a pas d'« avant » et la preuve ne vaut rien 🧑
- [x] `terrain/PILOTES.md` — un bloc par établissement : date d'installation, contact, matériel utilisé, métriques hebdomadaires, verbatims, incidents (PR #37)

**13.4 — Les pilotes eux-mêmes** 🧑

- [ ] Trois établissements pilotes gratuits, trois profils différents (café de quartier, restaurant de centre-ville, établissement de zone touristique), avec un accord écrit : quatre semaines d'usage effectif en service, et le droit de citer leur nom
- [ ] Quatre semaines d'usage réel, incidents consignés dans `terrain/PILOTES.md`
- [ ] Deux des trois passent à un abonnement payant — c'est le passage de « produit » à « entreprise », et la ligne qui débloque la note de viabilité économique

---

## Phase 14 — Différenciation et prix

Trois concurrents tunisiens vendent déjà cette catégorie (Digital Menu à
19–49 DT/mois avec commande à table, écran cuisine, zones, fidélité ; Scanny
avec caisse connectée ; Menu-QR en entrée de gamme). Leur existence prouve que
le marché paie — mais elle interdit de vendre la même chose au même prix.

**14.1 — Vente incitative** (la seule fonctionnalité manquante qui produit un
chiffre défendable en rendez-vous : « +X % de panier moyen »)

- [x] Table de liaison `menu_suggestions` (`menu_item_id`, `suggested_item_id`, `restaurant_id`) + migration + `model_registry.py` — pas un champ texte libre, pour que la suggestion reste un vrai article commandable en un geste (PR #38)
- [x] Gestion des suggestions dans le dashboard manager : sur la ligne d'un plat, choisir jusqu'à 3 articles associés (PR #38)
- [x] Côté client : à l'ajout au panier, proposer les articles associés (« avec ce plat »), ajout en un tap, jamais bloquant, traduit fr/ar (PR #38)
- [x] Mesurer l'effet : compter les articles ajoutés depuis une suggestion (`OrderItem.from_suggestion`) et exposer sur `/dashboard/preuve` le panier moyen avec et sans suggestion acceptée (PR #38)
- [ ] Formules / menus du jour — **seulement si les entretiens de 13.1 les font remonter.** Ne pas construire avant

**14.2 — Positionnement « service inclus »** (ce qu'un éditeur en libre-service
à 19 DT ne fera jamais)

- [x] Page publique d'accueil — bénéfice, service inclus, contact. **Deux blocs volontairement vides** : les résultats de pilotes (`lib/offer.ts::PILOT_RESULTS`) ne s'affichent que remplis avec des chiffres réellement relevés chez un établissement qui a donné son accord pour être cité, et le prix (`PRICE_MONTHLY_DT`) reste `null` tant que 14.3 n'est pas tranchée — la page affiche alors « tarif communiqué au premier rendez-vous » plutôt qu'un montant que personne n'a arrêté (PR #39)
- [x] Rapport hebdomadaire par serveur, exportable — le manager s'en sert pour ses primes de rendement. C'est l'angle que les trois concurrents ne mettent pas en avant, et il est déjà à 80 % dans `stats/service.py` (PR #39)
- [x] Ne **pas** afficher les statistiques nominatives sur les écrans partagés de salle : le rapport est un document de direction, pas un classement public. Vérifier `staff/page.tsx` et `kitchen/page.tsx` sur ce point (PR #39)

**14.4 — Rétention** (issu de l'audit fonctionnel du 2026-08-14, cf.
[`PREMIERES_VENTES.md`](./PREMIERES_VENTES.md))

- [ ] Afficher le **chiffre encaissé du jour** en tête du tableau de bord manager. La donnée existe déjà (`orders_count` × `avg_basket_amount`), elle n'est jamais montrée comme un total. C'est le seul chiffre qu'un restaurateur cherche chaque soir : sans lui le tableau de bord est une curiosité, avec lui c'est une habitude quotidienne — et une habitude quotidienne est ce qui empêche une résiliation au troisième mois. À faire **avant** le premier pilote
- [ ] Addition au niveau de la **table** et non de la commande — une table qui commande en deux temps (boissons puis plats) produit aujourd'hui deux additions et deux cartes sur l'écran serveur. **Ne pas construire avant les entretiens de 13.1** : s'ils ne le font pas remonter spontanément, le construire serait deviner

**14.3 — Un seul prix** (remplace la décision « trois paliers » de l'ancienne
Phase 11, prise avant tout contact client)

- [ ] Fixer le prix unique 🧑 — proposition de la revue : **120 DT/mois, service d'installation inclus**, cible 45 établissements. Arithmétique : 45 × 120 DT ≈ 65 k DT/an tenable seul, contre 290 clients à 35 DT pour un revenu comparable et une charge de support intenable
- [x] Page tarifs publique : un prix, ce qui est inclus, pas de grille à trois colonnes (PR #39) — **scope réduit et assumé** : ce sont les sections « Un seul prix » et « Tout est inclus » de la page d'accueil, pas une page séparée. Une page tarifs dédiée qui n'affiche aucun tarif n'aurait servi à rien. Le montant apparaît dès que `PRICE_MONTHLY_DT` est renseigné, sans autre changement de code
- [x] Garder `Restaurant.subscription_tier` en base (déjà là, sans coût) mais **ne pas coder de gating** : bloquer une fonctionnalité déjà utilisée par un pilote casserait son service sans aucun bénéfice — vérifié, le champ n'est lu nulle part ailleurs que pour afficher un badge sur `/dashboard`. Ligne à laisser cochée : elle décrit une chose à **ne pas** faire
- [ ] Facturation : facture mensuelle manuelle pour les 10 premiers clients (un virement ou un chèque, pas d'outil). N'automatiser qu'au-delà — YAGNI strict
- [ ] Ne pas activer la facturation avant la fin de la phase pilote gratuite

---

## Phase 15 — Tenir un vrai service

Un incident en pleine soirée fait résilier, quelle que soit la qualité du reste.
Deux réserves viennent du choix « le restaurant utilise son matériel existant ».

- [x] Écran cuisine vérifié à 360 px — il a été dessiné pour un grand écran (mode sombre, cartes larges, badge « il y a X min ») ; s'il tourne sur un téléphone posé sur une étagère, le vérifier en vrai avant de le promettre (PR #39)
- [x] Repli papier assumé : bouton d'impression de la commande depuis l'écran serveur et l'écran cuisine, et procédure écrite dans `terrain/PRISE_EN_MAIN.md` (« si l'app tombe, on fait quoi ») (PR #39)
- [x] Comportement en cas de JWT expiré ou de compte désactivé en pleine session : redirection propre vers `/login` avec un message clair, jamais un écran blanc ou une boucle de reconnexion silencieuse (PR #39)
- [x] Test de charge minimal : un restaurant, 20 tables, 200 commandes sur un service simulé — vérifier qu'aucune diffusion WebSocket n'est perdue et que `/dashboard` reste utilisable (PR #39)
- [x] Sujet social du téléphone personnel du serveur (batterie, forfait data, appareil personnel utilisé pour travailler, couplé à des statistiques nominatives) — préparer la réponse à donner au patron avant l'installation, la consigner dans `terrain/FORMATION_10MIN.md`. Le personnel de salle est le premier saboteur potentiel de cet outil (PR #39)
- [x] Deux défauts trouvés en rejouant un service, corrigés (PR #45) : l'appel serveur acceptait des identifiants devinables — deux boucles suffisaient à faire sonner tous les écrans de tous les établissements, sans entrer nulle part ; et les écrans serveur/cuisine affichaient `Table {table_id}`, l'identifiant en base et non le nom de la table. Le client lisait « Terrasse 2 », le serveur « Table 1 », et le plat partait au mauvais endroit

---

## Phase 16 — Conformité données personnelles

Le produit collecte des numéros de téléphone (fidélité). C'est une donnée
personnelle au sens de la loi organique tunisienne 2004-63, dont l'article 7
impose une déclaration préalable auprès de l'INPDP.

- [ ] Déclaration du traitement auprès de l'INPDP 🧑 (formulaires sur `inpdp.tn`) — avant le premier client réel, pas après
- [x] Politique de confidentialité, page publique + lien depuis l'écran de saisie du numéro, fr et ar (PR #40) — `/confidentialite`, dans la langue déjà choisie sur le menu ; le texte ne décrit que ce que le code fait, et rien d'autre
- [x] Consentement explicite à la saisie du téléphone : dire à quoi il sert (fidélité de cet établissement uniquement) et qu'il n'est jamais partagé (PR #40) — affiché **au-dessus** du champ, pas derrière un lien que personne n'ouvre
- [x] Rétention : purger `Order.push_subscription` une fois la commande servie, et les `LoyaltyMember` inactifs au-delà de 24 mois (tâche de nettoyage à lancer à la main au départ, pas d'ordonnanceur) (PR #40) — l'abonnement push est effacé sur tout statut terminal (servi *et* annulé) ; `scripts/purge_donnees_personnelles.py` simule par défaut et n'efface qu'avec `--appliquer`

---

## Phase 17 — Faire adopter l'outil

Issue de l'audit du 2026-08-14 ([`PREMIERES_VENTES.md`](./PREMIERES_VENTES.md)).
Les phases 12 à 16 ont rendu Tawla **vendable**. Celle-ci le rend **utilisé** —
ce n'est pas la même chose : un outil installé qu'on n'ouvre pas est un
abonnement qu'on résilie au troisième mois.

Le principe de cette phase : **chaque argument de vente doit exister comme un
écran**, pas comme une phrase. Un argument qu'on ne peut pas montrer est un
argument qu'on devra répéter à chaque rendez-vous, puis défendre à chaque
échéance de facture.

### Traduction des dix recommandations en code

Le tableau dit, pour chaque recommandation commerciale, ce que le code doit
faire — ou pourquoi il n'a rien à faire. **Une recommandation sans solution
technique n'est pas un manque : c'est un acte de vente, et le noter évite de
construire une fonctionnalité pour se donner l'impression d'avancer.**

| # | Recommandation | Solution technique |
|---|---|---|
| 1 | Vendre la commande perdue | **17.1** — commandes perdues du jour en tête du tableau de bord, à côté du chiffre encaissé |
| 2 | Choisir le pilote pour son poids social | *Aucune. Acte de vente pur.* Ne rien construire |
| 3 | Arriver avec sa carte chargée | *Déjà livré* — `setup_restaurant.py` + import CSV tolérant (PR #37) |
| 4 | Vendre un audit gratuit de quatre soirs | **17.2** — saisie du relevé « avant Tawla » et affichage en face des chiffres mesurés |
| 5 | Convaincre le serveur avant le patron | **17.3** — encart « ma soirée » sur l'écran serveur : ses propres chiffres, sur son écran, jamais un classement public |
| 6 | Le prix ne bouge jamais | **17.4** — date de fin de pilote affichée au manager (différé : demande le prix tranché, 14.3 🧑) |
| 7 | Remonter le calendrier depuis Ramadan | *Déjà livré* — mode ramadan, heure d'iftar, pré-commande (phases 0-11) |
| 8 | Disqualifier durement à la porte | *Aucune.* Le réseau du restaurant ne se corrige pas en code, il se refuse en rendez-vous |
| 9 | Accord écrit par pilote | *Aucune.* Document papier, hors du dépôt |
| 10 | Montrer son chiffre du jour | **17.1** — c'est la même tâche que la 1 |

**17.1 — Le premier écran répond à la première question** (le patron doit
apprendre ses commandes perdues *en passant*, pendant qu'il regarde sa recette)

Les définitions de « commande perdue » et de « recette » sont extraites dans
`stats/service.py::_lost_orders` et `::_billable_orders`, partagées par le
tableau de bord et la page de preuve. Les deux écrans montrent le même jour au
même homme : s'ils divergeaient d'une seule commande, il cesserait de croire
les deux — et c'est sur ce chiffre que repose l'argument de vente.

- [x] `GET /api/v1/stats/dashboard/{restaurant_id}` renvoie `revenue_today` et `lost_orders_today` (PR #46) — la donnée existe déjà (`_period_proof`), elle n'est simplement jamais servie comme un total du jour
- [x] Les deux chiffres en tête de `/dashboard`, avant tout le reste, en gros (PR #46). La recette d'abord : c'est elle qu'il vient chercher tous les soirs, et c'est cette habitude qui empêche la résiliation
- [x] Les commandes perdues juste à côté, avec leur définition en clair (PR #46) (annulées + jamais prises en charge après 10 min) — un chiffre dont on ne comprend pas la définition ne convainc personne

**17.2 — L'audit avant installation devient un écran** (sans relevé « avant »,
la preuve d'après ne vaut rien, et un tableur ne se montre pas en rendez-vous)

- [ ] `Restaurant.baseline_*` : commandes perdues par jour et panier moyen relevés **à la main avant** l'installation, saisis par le manager (ou par Wassim à l'installation), + migration
- [ ] Saisie depuis le dashboard, avec la date du relevé — et rien d'affiché tant que ce n'est pas saisi
- [ ] La page de preuve affiche « avant Tawla » en face de « mesuré » quand le relevé existe. C'est **la** capture d'écran qui vend le passage au payant
- [ ] Ne jamais inventer ni pré-remplir ces valeurs : un chiffre « avant » inventé rend toute la démonstration mensongère

**17.3 — Le serveur y trouve son compte** (premier risque de churn : l'équipe
contourne l'outil, et le patron résilie sans jamais dire pourquoi)

- [x] `GET /api/v1/stats/ma-soiree` — les chiffres du **staff connecté** (PR #46) pour aujourd'hui : commandes prises, montant encaissé, délai moyen de prise en charge
- [x] Encart en tête de l'écran serveur. Ses chiffres à lui, sur son écran à lui (PR #46) — rafraîchi à la **prise en charge**, pas à l'envoi en cuisine : c'est là que son compteur bouge
- [x] **Jamais de comparaison avec les collègues, jamais de classement** (PR #46) — l'API elle-même n'envoie aucun nom d'autrui, donc rien ne peut fuiter dans une évolution future de cet écran. Le rapport d'équipe reste un document de direction (14.2) ; le jour où un serveur se découvre classé publiquement, l'équipe est perdue

**17.4 — Fin de pilote visible** 🧑 (différé : demande le prix tranché en 14.3)

- [ ] `Restaurant.pilot_ends_on` + bandeau « pilote gratuit jusqu'au JJ/MM » sur le dashboard. Rend l'échéance explicite au lieu d'une conversation gênante à avoir

---

## Phase 18 — Le plan de salle

Idée de Wassim (2026-08-14). J'avais proposé une grille de tuiles par zone,
moins chère ; il a tranché pour le vrai plan, et il a eu raison sur un point
que j'avais sous-estimé : un restaurateur reconnaît **sa** salle en deux
secondes, et « accès au marché » est la note la plus faible de la grille.

Ce que le plan règle, au-delà de la démonstration : **une liste grandit
indéfiniment, un plan a exactement le nombre de tables de la salle.** L'écran
serveur accumulait les commandes abandonnées sans borne de date ; sur un plan,
une table est occupée ou ne l'est pas.

- [x] `Table.pos_x`, `pos_y` (en **pourcentage**, jamais en pixels) et `shape`, + migration (PR #48) — le même plan se lit sur un téléphone de 360 px et sur l'écran du bureau
- [x] `PUT /api/v1/tables/plan/{restaurant_id}` — tout le plan en une écriture, vérifié entièrement avant d'écrire quoi que ce soit : une table étrangère glissée en fin de liste ne doit pas laisser la salle à moitié enregistrée (PR #48)
- [x] `GET /api/v1/tables/plan/{restaurant_id}` — ouvert à toute l'équipe, **sans les `qr_token`** : ils n'ont rien à faire sur un écran de service (PR #48)
- [x] Éditeur manager : glisser-déposer, trois formes, réserve des tables non posées. Dessiner la salle reste un acte de gestion — un serveur ne peut pas la réorganiser en plein service (PR #48)
- [x] Vue serveur en direct, alimentée par les **mêmes listes** que celles affichées dessous : deux sources finiraient par se contredire, et un plan qui ment est pire qu'aucun plan (PR #48)
- [x] L'anneau autour d'une table est un **compte à rebours avant perte** : il se referme exactement à `ABANDONED_PENDING_AFTER`, le seuil dont la page de preuve tire l'argent perdu (PR #48)
- [x] Pas de clignotement — ignoré au bout de dix minutes ou insupportable. Seule la table la plus urgente respire, et rien ne bouge sous `prefers-reduced-motion` (PR #48)
- [ ] **Borner les commandes actives dans le temps** — le plan a rendu le défaut visible : deux tables restaient rouges avec « +1 h » pour des commandes abandonnées la veille. Arbitrage produit à trancher avec Wassim (masquer au-delà de N heures ? un bouton « classer sans suite » pour le serveur ?)
- [ ] Confronter le plan aux entretiens de 13.1 : les zones suffisaient-elles, ou le plan dessiné change-t-il vraiment la conversation ?

---

## Hors périmètre, délibérément

Chaque ligne ici est une chose qu'il serait tentant de construire et qui ne
déplacerait aucune note du jury. Ne pas les rouvrir sans une demande explicite
de Wassim.

- **Expansion régionale** (Algérie, Maroc, Libye) — seul chemin compatible avec une levée de fonds, donc hors sujet depuis la décision de cadrage. Trois conquêtes commerciales distinctes pour un fondateur seul
- **Intégration Konnect réelle** — le paiement carte reste un confort client en mode simulé. Le paiement à la livraison représente encore ~68 % des commandes e-commerce tunisiennes : brancher un vrai flux carte avant d'avoir des clients qui le réclament est un chantier sans retour. À rouvrir si, et seulement si, un pilote le demande
- **Intégration caisse / gestion de stock** — c'est la vraie douleur du patron et le chemin d'un revenu par client bien supérieur, mais c'est un produit différent. À reconsidérer seulement après 20 clients payants
- **Multi-établissements sous un même compte** — attendre un client qui possède deux établissements et le demande
- **SMS au client, imprimante cuisine matérielle, montée de version Next.js** — arbitrages déjà tranchés, inchangés (cf. archive)
- **Trois paliers d'abonnement** — remplacés par un prix unique (14.3)
- **Grands groupes / événements (mariages, réservations de salle)** — Wassim a choisi de ne pas cadrer ; ne pas relancer

---

## Comment travailler cette roadmap (pour Claude Code)

1. **Une tâche = une branche = une PR.** Jamais de push direct sur `main`. CI verte avant merge.
2. **Ordre strict**, sauf 13.1 (les entretiens) qui tourne en parallèle et n'attend aucun code.
3. **Pour toute tâche de la Phase 12.2 : écrire le test qui échoue d'abord**, puis le correctif. Un correctif de sécurité sans test qui le prouve ne compte pas comme livré.
4. **Cocher `[x]` avec le numéro de PR**, et si le scope a été réduit, écrire pourquoi sur la ligne — c'est la convention qui a rendu l'archive utile.
5. **À la clôture d'une phase, recalculer le tableau de la grille du jury** en haut de ce fichier. Si une phase n'a déplacé aucune note, le dire dans la PR : c'est le signal que la tâche n'aurait pas dû être faite.
6. **Conventions inchangées** : voir `CLAUDE.md` (multi-tenant partout, transitions d'état contrôlées, prix figé sur `OrderItem`, tout nouveau modèle dans `model_registry.py`, logs via `log_event`).
7. **Face à une ambiguïté produit** : livrer le scope le plus étroit qui règle le problème réel, et signaler l'ambiguïté dans la PR — plutôt que d'inventer une réponse. C'est ce qui a le mieux fonctionné sur les phases 0 à 11.
