# Chantier multi-établissements — roadmap et prompt d'exécution

Écrit le **2026-09-01**, sur `main` au commit `471e7d9` (état du dépôt
inspecté module par module : `tenants/models.py`, `staff/models.py`,
`staff/router.py`, `subscription.py`, `subscription_payments.py`,
`platform_admin/*`, `tests/test_isolation.py`).

**Objet** : faire passer « Multi-établissements (construit pour vous à la
demande) » — vendu dans le palier Business à 149 DT/mois — d'une promesse de
service manuel (Wassim relance `setup_restaurant.py` pour un 2ᵉ établissement
totalement indépendant, zéro lien avec le premier) à une vraie fonctionnalité
produit : un propriétaire peut accéder à plusieurs établissements sans
recréer un compte à chaque fois.

---

## 0. Ce que ce fichier est — et ce qu'il n'est pas

`ROADMAP.md` pilote le code produit. Ce fichier ne le remplace pas et ne le
réordonne pas : il ne s'ouvre que si Wassim décide explicitement de
prioriser ce chantier — voir §1. Tant que ce n'est pas le cas, ce fichier est
une spécification prête à l'emploi, pas une tâche en cours.

Ce fichier fait aussi office de **prompt d'exécution** : une session qui
attaque ce chantier doit le suivre phase par phase, dans l'ordre, sans sauter
les tests ni les vérifications fonctionnelles d'une phase pour « gagner du
temps » sur la suivante.

---

## 1. Pourquoi ce fichier existe maintenant

Le 2026-09-01, le [commit 55a0514](https://github.com) (PR #119) a supprimé
la règle « toute proposition de fonctionnalité doit nommer le restaurateur
qui l'a demandée, sinon elle va en § Sous condition » — de `CLAUDE.md` et de
`ROADMAP.md`. La section `## Sous condition` de `ROADMAP.md` (avec sa ligne
« Multi-établissements sous un même compte » et son déclencheur « un client
qui possède deux établissements et le demande ») **existe encore dans le
fichier**, mais plus rien ne la fait respecter : c'est un reliquat, pas une
barrière.

Conséquence pratique : plus rien n'empêche techniquement d'ouvrir ce chantier
sans attendre un client nommé. Mais l'absence de la règle ne dispense pas de
la question qu'elle posait — piloter cette fonctionnalité doit venir d'un
choix produit assumé (`§2` ci-dessous), pas d'un vide de gouvernance.
**Ouvrir ce chantier reste une décision de Wassim, pas une déduction
automatique du retrait de la règle.**

---

## 2. Décisions produit — TRANCHÉES le 2026-09-01

Wassim a explicitement délégué ces trois choix au critère « le plus
technique et logique » plutôt qu'à un arbitrage commercial. Les trois
décisions ci-dessous sont donc **actées**, pas des recommandations en
attente — une session peut dépasser la Phase 1 sans repasser par cette
section.

1. **Facturation → (a) un abonnement par établissement.** `Restaurant` porte
   seul son `subscription_tier`, son `subscription_period_end` et ses clés
   Konnect ([tenants/models.py:60-99](backend/app/modules/tenants/models.py))
   — la facturation est structurellement par établissement dans le code
   actuel. Choisir (b) (un seul paiement 149 DT pour N sites) demanderait une
   nouvelle entité de facturation au-dessus de `Restaurant`, un chantier
   Konnect/webhook réécrit, et ne correspond à aucune promesse du texte de
   vente. (a) est la seule option qui ne demande aucun changement au modèle
   de paiement existant — c'est ce qui la rend techniquement supérieure, pas
   seulement plus simple.

2. **Nombre d'établissements → pas de limite dure en base, liaison manuelle
   uniquement.** Aucun flux self-service « + Ajouter un établissement »
   n'existe ni n'est prévu (§4) ; la liaison se fait via `platform_admin` ou
   `setup_restaurant.py`, donc une limite en base n'apporterait aucune
   garantie supplémentaire — le vrai contrôle est déjà le geste manuel de
   Wassim à chaque liaison.

3. **Périmètre V1 → Option A (comptes liés + sélecteur au login).** Option B
   (entité `Owner`, dashboard agrégé) ajoute une couche d'auth entière pour
   un besoin non encore observé chez un client réel. Option A atteint la
   promesse de vente (« accéder à plusieurs établissements ») avec un
   changement d'une seule contrainte SQL et d'un seul endpoint (§3, §5) —
   c'est le chemin qui minimise la surface de code touchée pour le même
   résultat fonctionnel, donc le choix le plus logique tant qu'aucune
   agrégation cross-site n'est requise.

---

## 3. Deux options d'architecture — Option A retenue (§2.3)

### Option A — comptes liés (choisie pour la V1)

Aucune nouvelle entité. `Staff` reste l'identité par établissement (un
manager peut avoir un rôle différent selon le site — c'est déjà le cas
aujourd'hui et ça doit le rester). On relâche uniquement la contrainte
`unique=True` sur `Staff.email` ([staff/models.py:22](backend/app/modules/staff/models.py:22)) en `unique(email, restaurant_id)`, ce qui
permet à la même personne d'avoir une ligne `Staff` par établissement,
partageant le même email. Le login (`staff/router.py::login`, aujourd'hui
`Staff.email == payload.email` — une seule ligne attendue) devient :
chercher **toutes** les lignes `Staff` actives pour cet email, vérifier le
mot de passe contre chacune, et si plus d'une correspond, renvoyer la liste
des établissements pour un écran de sélection **avant** d'émettre le JWT
habituel (`create_access_token(staff_id, restaurant_id, role)` — inchangé,
toujours scopé à un seul `restaurant_id`).

**Zéro changement** dans tout le reste du code : `get_current_staff`,
`require_tier`, tous les routers, toutes les permissions restent scopés à un
`restaurant_id` unique comme aujourd'hui. Le seul changement est au moment
du login.

**Limite connue, à assumer explicitement** : les mots de passe ne sont pas
synchronisés entre les lignes liées (chacune a son propre `password_hash`).
Changer son mot de passe sur l'établissement A ne le change pas sur B. C'est
un vrai défaut d'UX — acceptable pour une V1 construite « à la demande » et
accompagnée par Wassim, pas pour un self-service à grande échelle.

### Option B — vrai compte propriétaire unifié (hors scope V1)

Nouvelle entité `Owner` + table de liaison `owner_restaurant(owner_id,
restaurant_id)`, sur le modèle de `PlatformAdmin` ([platform_admin/models.py](backend/app/modules/platform_admin), déjà une identité
transversale aux restaurants dans le code actuel). Un `Owner` s'authentifie
une fois, choisit un établissement actif, et le backend émet un JWT scopé
comme avant. Permet en plus un vrai dashboard agrégé (réutilisant les
patterns d'agrégation déjà écrits dans `platform_admin/service.py`, mais
filtrés aux seuls établissements du propriétaire au lieu de tous). Résout
aussi la synchronisation de mot de passe. **Ne pas ouvrir sans un client réel
à 2+ sites qui bute concrètement sur la limite de l'Option A** — c'est
exactement le rôle qu'avait le déclencheur nommé dans l'ancienne règle,
même sans la règle elle-même.

---

## 4. Ce qu'on NE fait PAS dans cette V1 (Option A)

- **Ne pas** créer d'entité `Owner`/`Account` — c'est l'Option B, hors scope.
- **Ne pas** toucher à `subscription_payments.py` ni à la facturation
  Konnect — chaque établissement garde son propre `subscription_tier` et son
  propre cycle de paiement (décision §2.1a).
- **Ne pas** construire de flux self-service « + Ajouter un établissement »
  dans le dashboard client — la création d'un établissement lié reste
  manuelle, via `setup_restaurant.py` ou `platform_admin` (décision §2.2).
- **Ne pas** construire de vue agrégée multi-sites (stats combinées, rapport
  d'équipe combiné) — c'est l'Option B. La V1 ne fait que **switcher** entre
  des dashboards déjà existants, chacun scopé à un seul `restaurant_id` comme
  aujourd'hui.
- **Ne pas** relâcher `Staff.email` en unique globalement nul — la contrainte
  devient `unique(email, restaurant_id)`, jamais une absence totale de
  contrainte (ça casserait la détection de doublon dans `register`).
- **Ne pas** permettre à un `Staff` de voir les données d'un établissement
  auquel il n'est pas lié — le JWT reste scopé à un seul `restaurant_id`,
  choisi explicitement à la connexion. Zéro élargissement des permissions
  par rapport à aujourd'hui.
- **Ne pas** ajouter de tests de composants frontend — convention actuelle du
  dépôt (`reference_tawla_repo_conventions` : zéro test composant, seulement
  `lib/*.test.ts` en logique pure). Rester cohérent : tester la logique du
  switcher (pas de composant React) en pur, vérifier le reste en fonctionnel
  manuel (§7).
- **Ne pas** cocher une case sur une supposition — `ROADMAP.md` règle 6.

---

## 5. Étapes (Option A, dans l'ordre, une session ne saute pas de phase)

### Phase 1 — Modèle de données (ne dépend d'aucune décision produit)

- Migration Alembic (`cd backend && source .venv/bin/activate && alembic
  revision -m "staff email unique per restaurant"`) : remplacer l'index
  unique global sur `Staff.email` par un index unique composite
  `(email, restaurant_id)`.
- `Staff` modèle : documenter en commentaire (comme le reste du fichier) le
  changement de contrat — email unique **par établissement**, plus
  globalement.
- **Tests** : étendre `tests/test_isolation.py` avec un cas explicite — deux
  lignes `Staff` avec le même email, deux `restaurant_id` différents, deux
  mots de passe différents ; vérifier que la création des deux réussit
  (aujourd'hui elle échouerait sur la contrainte globale). Lancer
  `test_migrations.py` (`alembic upgrade head` doit matcher les modèles).

### Phase 2 — Login avec sélection d'établissement (dépend de la décision §2.1/§2.2 étant tranchées, même si cette phase ne touche pas à la facturation)

- `staff/router.py::login` : remplacer la recherche par email unique par une
  recherche de **toutes** les lignes `Staff` actives (`is_active=True`) pour
  cet email. Vérifier le mot de passe contre chaque ligne trouvée (jamais
  supposer qu'elles partagent le même hash).
  - 0 ligne ou mot de passe invalide partout → `INVALID_CREDENTIALS` comme
    aujourd'hui (garder le timing constant, comme `_DUMMY_HASH` le fait déjà
    pour `platform_admin/router.py`).
  - 1 ligne valide → comportement identique à aujourd'hui, JWT émis direct.
  - Plusieurs lignes valides → nouvelle réponse (pas un JWT) : liste des
    établissements liés (id, nom, slug) pour un écran de sélection, puis un
    second appel (nouvel endpoint, ex. `POST /auth/select-restaurant`) qui
    prend `staff_id` + le restaurant choisi et émet le JWT habituel.
- **Tests** : cas 0/1/plusieurs comptes liés, en extension de
  `backend/tests/test_staff_auth.py` (fichier existant qui couvre déjà
  `login`/`register`). Vérifier explicitement qu'un `staff_id` renvoyé par
  la première étape ne peut pas être utilisé pour choisir un établissement
  auquel il n'est **pas** lié (test négatif, pas juste le chemin heureux).

### Phase 3 — Frontend : écran de sélection

- `frontend/app/login/page.tsx` : gérer la nouvelle réponse « plusieurs
  établissements » avec un écran de choix simple (liste, clic, connexion)
  avant redirection vers `/dashboard`. Ne pas toucher `frontend/app/admin/login`
  — c'est le login `platform_admin`, une identité totalement séparée, hors
  scope de ce chantier.
- Pas de nouveau composant testé (convention §4) — vérification uniquement
  fonctionnelle (§7).

### Phase 4 — Bascule d'établissement sans se déconnecter (confort, si le temps le permet)

- Depuis `frontend/app/dashboard/page.tsx`, un lien « changer
  d'établissement » qui repasse par l'écran de sélection (Phase 3) sans
  redemander le mot de passe, tant que la session du navigateur est encore
  valide côté `staff_id` choisi en Phase 2. **Si ça complique l'auth JWT
  actuel (stateless, sans session serveur), reporter cette phase** — ce
  n'est pas dans la promesse de vente, seulement un confort.

---

## 6. Tests à écrire — récapitulatif

- `tests/test_isolation.py` : cas Phase 1 (deux `Staff`, même email, deux
  restaurants) — garantir qu'aucune isolation de données n'est cassée par le
  changement de contrainte (c'est le test qui existe déjà pour vérifier
  qu'un resto A ne voit jamais les données de B ; l'étendre, ne pas le
  dupliquer).
- Extension de `backend/tests/test_staff_auth.py` pour `staff/router.py::login` :
  0/1/plusieurs comptes liés, y compris le cas négatif (établissement non
  lié refusé à la sélection).
- `backend/tests/test_migrations.py` : doit rester vert après la migration
  Phase 1 (ne jamais l'éditer pour la faire passer — générer la migration
  correctement, voir `reference_tawla_repo_conventions`).
- Frontend : uniquement si une logique pure émerge (ex. un helper qui décide
  quel écran afficher selon la réponse de login) — dans `lib/*.test.ts`,
  jamais un test de composant (convention du dépôt).

---

## 7. Vérifications fonctionnelles (checklist manuelle, avant de cocher une case)

- [ ] Créer 2 restaurants de test, 1 `Staff` par resto avec le même email,
      mots de passe différents → login avec chaque mot de passe atterrit
      bien sur le bon établissement (pas de mélange).
- [ ] Même setup, mots de passe **identiques** sur les deux lignes → écran de
      sélection s'affiche, chaque choix mène au bon dashboard, données
      strictement isolées (vérifier qu'aucune commande/table du resto A
      n'apparaît côté B et inversement).
- [ ] Un `Staff` désactivé (`is_active=False`) sur un des deux établissements
      liés n'apparaît **pas** dans l'écran de sélection, et ne peut pas être
      choisi même en forgeant la requête (test au niveau API, pas juste UI).
- [ ] Régression : un compte `Staff` classique, non lié (email unique en
      pratique, un seul établissement) — le login se comporte exactement
      comme avant Phase 2, sans écran de sélection.
- [ ] Régression : `platform_admin` (identité totalement séparée) toujours
      fonctionnel, aucune interférence avec le nouveau flux `staff/login`.
- [ ] Chaque abonnement (`subscription_tier`, Konnect) reste bien
      **indépendant par établissement** après tout le chantier — pas de
      fuite où activer Business sur un site l'active sur l'autre.

---

## 8. Risques et pièges identifiés

- **Timing attack sur le login** : avec plusieurs lignes `Staff` à vérifier
  par email, le temps de réponse peut varier selon le nombre de comptes liés
  et fuiter de l'information. Vérifier tous les hash trouvés avant de
  répondre (jamais de retour anticipé au premier match), garder le
  `_DUMMY_HASH` pour le cas 0 ligne.
- **Confusion Staff lié vs Staff homonyme** : rien ne garantit qu'un même
  email = une même personne physique tant que c'est Wassim qui crée les
  liens à la main (`setup_restaurant.py`/`platform_admin`) — documenter que
  la responsabilité de ne pas lier deux personnes différentes avec le même
  email revient au processus manuel d'onboarding, pas à une vérification
  automatique.
- **`register` (self-service)** : vérifier que l'inscription self-service
  (`/auth/register`) ne permet pas de créer une 2ᵉ ligne `Staff` sur un
  email déjà utilisé ailleurs **sans passer par le processus manuel de
  liaison** — sinon n'importe qui peut se « lier » à un établissement
  existant juste en réutilisant un email public.

---

## 9. Rollback

Migration Phase 1 réversible (`downgrade()` restaure l'unique global — échoue
proprement si des doublons existent déjà, ce qui est le comportement voulu).
Phase 2 est un changement de comportement sur un seul endpoint (`login`) :
revert de commit suffit, aucune donnée n'est perdue en revenant en arrière
tant que la Phase 1 (contrainte assouplie) reste en place — un rollback
complet doit défaire les deux phases ensemble, pas seulement la Phase 2.

---

## 10. Definition of done (V1, Option A)

- [x] Les 3 décisions du §2 sont tranchées (2026-09-01, critère technique/
  logique délégué par Wassim) et écrites ici.
- [ ] Phases 1 à 3 livrées, testées (§6), vérifiées fonctionnellement (§7).
- Ce fichier mis à jour avec le(s) numéro(s) de PR par étape cochée — même
  convention que `ROADMAP.md` règle 4.
- La ligne « Multi-établissements » de la section `## Sous condition` de
  `ROADMAP.md` est retirée ou mise à jour avec un pointeur vers ce fichier
  (éviter d'avoir deux sources qui se contredisent sur l'état de cette
  fonctionnalité).
