# Tawla France — dossier de cadrage et roadmap du marché français

Écrit le **2026-08-24**, à la demande de Wassim, sur `main` au commit `8197ab0`
(état du dépôt inspecté module par module, voir Annexe A pour l'inventaire
`fichier:ligne`).

**Objet** : ouvrir un second marché — la France, puis éventuellement l'Union
européenne — avec le même produit que Tawla Tunisie, une URL globale qui
demande au visiteur son pays et le renvoie vers le bon service, et la liste
exhaustive de ce qu'il faut **retirer**, **modifier** et **ajouter** pour que
le produit tunisien devienne un produit français.

---

## 0. Ce que ce fichier est — et ce qu'il n'est pas

`ROADMAP.md` **pilote le code produit et la mise en ligne du produit
tunisien**. Rien ici ne le remplace, ne le réordonne et ne le contredit : les
phases 19bis à 24 continuent de s'exécuter dans leur ordre, avec leur règle
(« une seule phase de code avant la mise en ligne, et plus rien ensuite avant
le premier pilote »).

Ce fichier-ci est un **programme de marché**, pas une roadmap produit
concurrente. **F0 a été tranchée par Wassim le 2026-08-24** (voir la phase F0
plus bas pour le détail des quatre décisions) : scénario **C**, les deux
marchés en parallèle, sans attendre un jalon tunisien. Une session qui
démarre et cherche « la prochaine tâche de code produit » va toujours dans
`ROADMAP.md` en priorité — ce fichier reste le programme du seul chantier
France, à travailler à côté. (Le design du parcours client a, lui, sa propre
roadmap depuis le 2026-09-01 : [`ROADMAP_DESIGN.md`](./ROADMAP_DESIGN.md).)

**Ce qui rend le scénario C jouable aujourd'hui, et pourrait cesser de
l'être** : au 2026-08-24, `ROADMAP.md` ne contient plus aucune tâche non
cochée qui ne soit marquée 🧑 — hébergement, domaine, entretiens, compte
Konnect, pilotes, tout demande une action réelle de Wassim, aucune ligne de
code n'attend. Le risque de dilution que le §1 décrit pour le scénario C ne
s'est donc pas encore matérialisé : il n'y a rien à disputer entre les deux
chantiers **côté code**. Le jour où une tâche codable rouvre en Tunisie
(après un déblocage 🧑), la question de la priorité entre les deux devra être
retranchée à ce moment-là — pas supposée réglée par cette note.

---

## 1. L'avertissement à lire avant tout le reste

Le dépôt contient déjà une décision écrite qui recouvre exactement ce sujet.
`ROADMAP.md`, § « Hors périmètre, définitivement » :

> **Expansion régionale** (Algérie, Maroc, Libye) — seul chemin compatible avec
> une levée, donc hors sujet depuis le cadrage « entreprise rentable et non
> diluée ». Trois conquêtes commerciales distinctes pour un fondateur seul.

La France est le **même type de décision**, avec des arguments plus forts dans
les deux sens. Il faut donc la trancher franchement plutôt que de l'ouvrir en
douce.

### Ce qui rend la France plus attirante que la Tunisie

| Fait | Conséquence |
|---|---|
| Panier moyen 3 à 5 fois supérieur | Une commande perdue coûte 25-40 €, pas 25 DT. L'argument de vente du produit — « une commande perdue par semaine paie l'abonnement » — devient **beaucoup** plus facile à gagner |
| Prix d'abonnement acceptable 3 à 6 fois supérieur | 45 clients à 120 DT ≈ 65 k DT/an. 45 clients à 89 € ≈ 48 k€/an, soit ~160 k DT |
| Wassim y est déjà (Darna vise « la diaspora France ») | Les déplacements d'installation, le compte bancaire, la structure, l'expert-comptable : le coût d'entrée logistique est déjà partiellement payé |
| Marché prouvé et éduqué | Sunday revendique ~1 500 restaurants en France et a levé 21 M$ en novembre 2025 pour doubler d'ici l'été 2026. Personne n'a plus à expliquer ce qu'est une commande par QR |
| Un segment que personne ne sert bien | Les restaurants à clientèle maghrébine (couscous, grillades, salons de thé) : bilingue **fr/ar déjà codé**, mode Ramadan et pré-commande iftar **déjà codés**, et aucun acteur français ne les a construits. C'est la seule chose que Tawla a et que Sunday n'a pas |

### Ce qui rend la France beaucoup plus dure que la Tunisie

| Fait | Conséquence |
|---|---|
| **Tout restaurant français a déjà une caisse certifiée** (L'Addition, Tiller/SumUp, Zelty, Lightspeed, Innovorder, Popina…) | Tawla n'entre pas dans un vide, il entre en **double saisie**. C'est le premier motif de refus, et il est technique, pas commercial. En Tunisie « intégration caisse » est classée « Sous condition » ; en France, c'est le prix d'entrée |
| **Contrainte fiscale sur les logiciels qui enregistrent des règlements** (art. 286-I-3° bis CGI, dit « NF525 ») | Tawla enregistre aujourd'hui des règlements (espèces, carte, terminal, pourboire). En l'état, il tombe potentiellement dans le champ. Voir §3.1 — c'est le vrai bloquant du marché français |
| Le différenciateur tunisien s'effondre | « Un éditeur en libre-service ne viendra jamais chez vous » : en France, Sunday **vient**, avec des commerciaux terrain et des équipes de déploiement. La proposition de valeur doit être re-dérivée, pas traduite |
| Le coût du service inclus explose | Une journée d'installation en France coûte ce que coûte une journée en France. Le modèle « 45 clients servis par un fondateur seul » n'a pas la même arithmétique |
| RGPD, TVA multi-taux, note obligatoire, facturation électronique, accessibilité | Cinq chantiers de conformité, dont trois touchent le code (voir §3.1) |
| La fenêtre Ramadan 2027 | Chaque semaine passée sur la France est une semaine retirée aux 20 entretiens tunisiens. Le calendrier de `ROADMAP.md` n'a « plus de marge » depuis le 15 août |

### Les trois scénarios, et celui que je recommande

| | Scénario | Ce que ça veut dire | Coût du pari |
|---|---|---|---|
| **A** | **La France remplace la Tunisie** | On arrête les phases 21-24, on jette la fenêtre Ramadan, on redémarre les entretiens en France | Perte de 12 mois de travail commercial préparé, dans un marché 10× plus concurrentiel. À ne faire que si les 20 entretiens tunisiens disent non |
| **B** | **La France suit la Tunisie** ✅ recommandé | On finit `ROADMAP.md` jusqu'au premier client payant (Phase 24), et **pendant ce temps** on ne fait de la France que ce qui ne coûte presque rien : F0 (décision), F1 (entretiens France, sans code), F2 (cadrage juridique) | On garde la fenêtre Ramadan, on apprend le métier sur un marché indulgent, et on entre en France avec deux clients payants et des chiffres relevés — la seule chose qui ouvre une porte en France |
| **C** | **Les deux en parallèle, tout de suite** | Deux marchés, deux conformités, deux tarifs, deux argumentaires, un fondateur | C'est le scénario qui échoue. `ROADMAP.md` § mode d'emploi point 5 le dit déjà pour un seul marché : « un chantier à la fois » |

**Recommandation : B.** Et ce fichier est écrit pour B — d'où le gel du §0, et
d'où l'ordre des phases : les trois premières (F0, F1, F2) ne contiennent
**aucune ligne de code** et peuvent tourner en parallèle des phases tunisiennes
sans rien leur retirer d'autre que des soirées.

Une nuance honnête, à trancher par Wassim et pas par moi : si les 20 entretiens
tunisiens (Phase 21) donnent un prix médian accepté très bas — disons sous
60 DT — alors le scénario A cesse d'être un abandon et devient une correction.
La Phase 21 est donc, aussi, l'instrument de décision de ce fichier.

---

## 2. Ce qui transfère tel quel — environ 80 % du produit

À ne surtout pas réécrire. C'est ce qui rend le scénario B jouable : le cœur du
produit est **agnostique du pays**.

| Ce qui transfère | Où |
|---|---|
| Machine à états de la commande et transitions contrôlées | `orders/service.py::ALLOWED_TRANSITIONS` |
| Écran serveur partagé, prise en charge (claim), écran cuisine temps réel | `orders/`, `notifications/` |
| WebSocket natif, reconnexion, rechargement au montage | `notifications/manager.py`, `lib/useReconnectingSocket.ts` |
| File hors ligne, commande idempotente (`client_order_id`) | `menu/[qrToken]/page.tsx`, `orders/models.py` |
| Token QR opaque, `public_token` de commande, surface publique fermée | `tables/models.py`, `orders/models.py` |
| Multi-tenant (`restaurant_id` partout), isolation testée | tout le backend, `tests/test_isolation.py` |
| Plan de salle, zones, couverts, vue serveur en direct | `components/plan/`, `tables/` |
| Page de preuve (commandes perdues, délai, panier moyen) | `stats/service.py`, `/dashboard/preuve` |
| Vente incitative « avec ce plat » et sa mesure (`from_suggestion`) | `menu/suggestions.py`, `orders/models.py` |
| Établissement de démonstration jetable + visite guidée | `demo/`, `components/visite/` |
| Chevalets QR imprimables, kit d'installation, import CSV | `tables/poster.py`, `scripts/setup_restaurant.py`, `menu/csv_import.py` |
| Alembic seule voie du schéma, test de conformité modèles/migrations | `alembic/`, `tests/test_migrations.py` |
| Gating par palier d'abonnement | `core/subscription.py` |
| Prix figé sur `OrderItem`, rate limiting, JWT + rôles, chiffrement au repos | transverse |

**Conséquence de cadrage** : le travail français n'est pas « réécrire Tawla ».
C'est **une couche marché** (§4), **une conformité** (§3.1) et **une
distribution** (§6, phases F1/F8). Dans cet ordre d'importance décroissante en
volume de code, et croissante en risque d'échec.

---

## 3. Les différences, classées par ce qu'elles coûtent

### 3.1 Différences légales et fiscales — les vrais bloquants

Ces cinq points ne sont pas des fonctionnalités. Ce sont des conditions pour
avoir le droit de vendre. Aucun ne doit être tranché par une session Claude :
tous demandent un **expert-comptable** et, pour le premier, probablement un
**avocat fiscaliste**. Ce qui suit est un état des lieux sourcé, pas un avis
juridique.

#### (1) Logiciel de caisse — l'obligation de conformité fiscale ⛔

**Le fait.** Depuis le 1ᵉʳ janvier 2018 (art. 286-I-3° bis du CGI), un
assujetti à la TVA qui enregistre les **règlements de ses clients
particuliers** au moyen d'un logiciel ou système de caisse doit pouvoir
justifier que ce logiciel satisfait aux conditions dites **ISCA** :
inaltérabilité, sécurisation, conservation, archivage. La preuve se fait soit
par un **certificat** délivré par un organisme accrédité (NF525 / LNE), soit par
une **attestation individuelle de l'éditeur**. Sanction : 7 500 € par logiciel
non conforme, avec mise en conformité sous 60 jours.

**Ce qui a bougé récemment, et qui compte.** La loi de finances pour 2025 avait
supprimé l'attestation éditeur (échéance ramenée puis repoussée à août 2026) ;
la **loi de finances pour 2026 (loi n° 2026-103 du 19 février 2026, art. 125) a
rétabli l'attestation individuelle de l'éditeur**. Autrement dit : au moment où
ce fichier est écrit, un éditeur peut de nouveau attester lui-même de la
conformité de son logiciel, sans passer par un organisme accrédité. **Ce point a
changé deux fois en dix-huit mois : il doit être revérifié le jour où F2
s'ouvre, jamais recopié depuis ici.**

**Où Tawla se situe aujourd'hui.** Le produit enregistre des règlements :
`PaymentMethod.CASH`, `CARD`, `CARD_TERMINAL`, `payment_status`, `tip_amount`,
la recette du jour (`RecetteDuJour`), l'encaissement par serveur
(`/dashboard/equipe`). Il coche donc les critères d'un système qui « enregistre
les règlements ». Il ne fait en revanche **aucun** des quatre I-S-C-A : pas de
journal inaltérable, pas de chaînage des écritures, pas de clôture
journalière/mensuelle/annuelle, pas d'archivage signé, pas de numérotation
continue des tickets.

**Les deux stratégies possibles, à trancher en F2 :**

| | Stratégie | Ce qu'elle implique | Mon avis |
|---|---|---|---|
| **S1** | **Ne pas être un système de caisse.** Tawla prend la commande et l'envoie en cuisine ; l'encaissement reste dans la caisse du restaurant | Retirer du marché français : paiement carte en ligne, paiement espèces, terminal, pourboire, recette du jour, encaissé par serveur. Et donc : **intégration caisse obligatoire** (§3.2) | ✅ Pour entrer. C'est aussi ce que le marché demande (personne ne remplace sa caisse) |
| **S2** | **Être conforme.** Journal inaltérable chaîné, clôtures Z/JJ/MM/AA, archivage, tickets numérotés, attestation éditeur | Un vrai chantier d'ingénierie (estimé 4-8 semaines à plein temps), plus une responsabilité juridique permanente portée par Wassim | Plus tard, et seulement si un client le demande en le payant |

**Conséquence directe sur la roadmap** : la stratégie S1 **retire des
fonctionnalités du produit français**. C'est contre-intuitif et c'est le point
le plus important de tout ce fichier : le produit français est, au premier jour,
**plus petit** que le produit tunisien.

#### (2) RGPD — remplace intégralement la loi 2004-63 et l'INPDP

`ROADMAP.md` Phase 20 prévoit une déclaration INPDP. Sans objet en France.
À la place :

- **Registre des traitements** (art. 30) — Tawla est *sous-traitant* du
  restaurant, qui est *responsable de traitement*. Les deux registres existent.
- **Contrat de sous-traitance (art. 28)** signé avec **chaque** restaurant.
  C'est un document contractuel, pas une case à cocher : sans lui, aucun
  restaurant un peu structuré ne signe.
- **Liste publiée des sous-traitants ultérieurs** (hébergeur, Resend, Stripe,
  service de push) et **hébergement dans l'UE** — voir §3.3.
- **Durées de conservation** documentées par donnée. Le code en a déjà une
  (`loyalty/service.py:19`, `RETENTION_WITHOUT_ORDER = 730 jours`) et une purge
  réelle (`scripts/purge_donnees_personnelles.py`) : c'est un très bon point de
  départ, il manque le tableau et la base légale de chacune.
- **Droits des personnes** : accès, rectification, effacement, portabilité,
  opposition — avec une adresse qui répond sous un mois. Aujourd'hui : rien.
- **Fidélité par numéro de téléphone** (`LoyaltyMember`) : consentement libre,
  spécifique, éclairé et **révocable**, finalité unique, pas de prospection sans
  consentement distinct. La date de naissance (réduction anniversaire) est une
  donnée à finalité étroite — la garder demande de la justifier.
- **Cookies** : Tawla n'utilise aujourd'hui que du `localStorage` fonctionnel
  (locale, panier, file hors ligne, jetons). **Aucun traceur.** C'est un argument
  commercial réel en France, à écrire noir sur blanc sur la page publique — et
  une raison de ne jamais y ajouter Google Analytics sans réfléchir.
- Le texte de `lib/i18n/privacy.ts` est bon dans l'esprit mais rédigé pour la
  loi tunisienne : à réécrire, pas à traduire.

#### (3) TVA et note client — ça touche le code

- **La note est obligatoire dès 25 € TTC** (arrêté n° 83-50/A du 3 octobre 1983)
  et doit mentionner le détail par prestation, le prix unitaire, et **le total
  HT et TTC**.
- La restauration applique **plusieurs taux** dans la même addition (règle
  générale : 10 % sur place, 20 % sur les boissons alcoolisées, 5,5 % sur
  certains produits à emporter — **à faire confirmer par l'expert-comptable**,
  la frontière est un piège classique).
- **Le code actuel ne connaît pas la TVA.** `MenuItem.price` est un prix unique,
  `core/invoice.py` produit une facture PDF sans aucune ventilation, en « DT ».

→ Chantier concret : colonne `vat_rate` (et `vat_rate_takeaway`) sur `MenuItem`,
migration, ventilation par taux dans la note, HT/TVA/TTC, numérotation. Voir F5.

#### (4) Facturation électronique — pour les factures de Wassim, pas du produit

Calendrier français : **réception obligatoire pour toutes les entreprises au
1ᵉʳ septembre 2026** ; émission obligatoire pour les GE/ETI à la même date, et
pour les **PME/TPE au 1ᵉʳ septembre 2027**, via une **Plateforme Agréée (PA)**.

Concrètement : les factures d'abonnement Tawla → restaurants (B2B) devront
transiter par une plateforme agréée d'ici septembre 2027, et Wassim devra
pouvoir **recevoir** des factures électroniques dès septembre 2026. Ce n'est pas
du code produit, c'est de l'administratif d'entreprise — mais ça a une date, et
elle est proche.

#### (5) Accessibilité numérique (European Accessibility Act)

En vigueur depuis le **28 juin 2025**. Les **micro-entreprises de services**
(moins de 10 salariés **et** CA ou bilan ≤ 2 M€) en sont exemptées — ce qui
couvre Tawla et la grande majorité de ses clients cibles. Deux réserves :

1. L'exemption se perd si le seuil est franchi.
2. Un client **groupe** ou **chaîne** n'est, lui, pas exempté, et son service
   auprès du public passe par l'écran de Tawla. Le jour où on démarche des
   groupes, l'accessibilité (EN 301 549 / RGAA) devient une exigence d'appel
   d'offres.

→ Classé « Sous condition » (§7), avec pour déclencheur : le premier prospect de
plus de 10 salariés.

#### (6) Statistiques individuelles par serveur — le point que personne n'anticipe

`/dashboard/equipe` produit un rapport nominatif par serveur (commandes prises,
montant encaissé), pensé comme « base des primes de rendement ». En France, un
dispositif de suivi individualisé de l'activité des salariés relève du Code du
travail et de la doctrine CNIL : information préalable des salariés,
consultation du CSE quand il existe (obligatoire à partir de 11 salariés),
proportionnalité, finalité déclarée, durée limitée.

Le code a déjà le bon réflexe (« jamais de statistiques nominatives en salle »,
Phase 14.2). Il manque : agrégat par défaut, nominatif activable par le manager
**après** avoir coché une notice d'information, aucun classement, et une durée
de conservation courte. Sinon c'est une objection frontale au premier rendez-vous
avec un patron qui a un DRH — ou un délégué du personnel.

### 3.2 Différences produit — retirer, adapter, ajouter

Verdict par fonctionnalité, sur l'état réel du code.

#### À retirer du marché français (ou à désactiver par drapeau de marché)

| Fonctionnalité | Où | Pourquoi |
|---|---|---|
| Anecdotes culturelles tunisiennes | `lib/culturalFacts.ts` | Contenu tunisien (couscous UNESCO, lablabi, Deglet Nour) affiché au client pendant l'attente. À remplacer par du contenu du restaurant (« notre plat du jour », « d'où vient notre viande ») ou à retirer |
| Catégorie « Ftour » | `lib/menuCategories.ts:6` | Sans objet hors Ramadan tunisien. Remplacée par « Formules », « Vins », « À emporter » |
| Derja tunisienne | `lib/i18n/ar.ts` | Un client marocain ou algérien à Paris ne lit pas la derja tunisienne. Si l'arabe est gardé (et il devrait l'être, §6 F1), c'est en **arabe littéraire** |
| `is_halal` par défaut à `true` | `menu/models.py:71` | En Tunisie le champ signale l'exception ; en France c'est l'inverse. Défaut `false`, et le champ devient un **marqueur positif** parmi d'autres (végétarien, vegan, sans gluten) |
| Konnect (abonnement **et** paiement carte client) | `core/konnect.py`, `Restaurant.konnect_*` | Passerelle tunisienne, TND en millimes. Aucun usage possible en euros |
| Paiement, pourboire, recette, encaissement par serveur | `orders/service.py`, `RecetteDuJour`, `MaSoiree` | **Seulement si la stratégie S1 est retenue** (§3.1) — c'est le prix à payer pour ne pas être un système de caisse |
| Déclaration INPDP | `ROADMAP.md` Phase 20 | Remplacée par le RGPD (§3.1) |

#### À adapter

| Sujet | État actuel | Cible française |
|---|---|---|
| **Monnaie** | `toFixed(3)` + `"DT"` en dur dans ~20 fichiers (Annexe A), `tnd_to_millimes()`, `TIER_PRICES_TND`, `priceDT` | `12,50 €` : 2 décimales, virgule décimale, espace insécable avant le symbole. **Un seul formateur**, alimenté par la couche marché |
| **Fuseau horaire** | `core/dates.py:9` : `TUNIS = timezone(timedelta(hours=1))`, avec le commentaire « la Tunisie n'applique plus l'heure d'été depuis 2009 » | **La France, si.** Un décalage fixe serait faux 7 mois par an : les journées de service, les stats et la page de preuve décaleraient d'une heure d'avril à octobre. Passage obligatoire à `zoneinfo` (`Europe/Paris`) |
| **Journée de service** | `SERVICE_DAY_START_HOUR = 5` (`dates.py:19`) | Probablement encore valable, mais c'est une hypothèse tunisienne : à reconfronter au premier pilote français (un restaurant qui ferme à 23 h n'a pas le même besoin qu'un service de nuit) |
| **Seuil d'alerte serveur** | `ATTENTE_ALERTE_MINUTES = 10 min` (`frontend/app/staff/page.tsx` — depuis le 2026-08-28, plus un seuil de « commande perdue » côté backend, seulement une alerte visuelle sur l'écran serveur) | Idem : une brasserie parisienne au service de midi n'a pas la même tolérance. À confronter, pas à recopier |
| **Mode Ramadan / iftar** | `Restaurant.ramadan_mode_enabled`, `iftar_time`, `Order.scheduled_for` | **Ne pas retirer.** À rendre optionnel par établissement, et à repositionner : c'est l'unique fonctionnalité que Tawla a et que Sunday n'a pas, sur un segment français réel (§6 F1). Le mécanisme `scheduled_for` sert aussi de commande programmée générique |
| **Allergènes** | Texte libre (`menu/models.py:67`) | En France l'information allergènes est **obligatoire** (réglementation INCO, 14 allergènes). Passage à une **liste structurée** — d'obligation légale à argument de vente |
| **Pourboire** | 0 / 5 % / 10 % (`menu/[qrToken]/page.tsx:1215`) | La suggestion en pourcentage est un usage nord-américain. En France : montants ronds (sans / 1 € / 2 € / autre). Et sujet à la stratégie S1 |
| **Fidélité** | Téléphone + 10 commandes = article offert (`loyalty/models.py:11`) | Le mécanisme tient, l'encadrement change : consentement RGPD explicite, durée, et un e-mail est souvent mieux accepté qu'un numéro en France |
| **Chevalet QR** | Bilingue fr/ar avec police Kufi (`tables/poster.py`) | Français seul par défaut, anglais optionnel (touristes), arabe seulement sur le segment concerné |
| **Démo** | Restaurant « Dar Chaabane », carte tunisienne (`demo/service.py:158`) | Brasserie française : formule du jour, entrée/plat/dessert, carte des vins. Un restaurateur français qui voit une carte tunisienne en démo comprend que le produit n'est pas pour lui, en trois secondes |
| **Visite guidée** | 20 étapes, contenu tunisien (`lib/visite/etapes.ts`) | Moteur conservé tel quel (excellent), contenu par marché |
| **Prix des paliers** | 49 / 89 / 149 DT | À re-dériver, jamais à convertir (§3.4) |
| **Politique de confidentialité** | fr/ar, loi 2004-63 (`lib/i18n/privacy.ts`) | Réécriture RGPD complète |
| **Page publique** | Copie déjà neutre côté marché/segment depuis le retour démo 2026-08-31 (plus de mention de la Tunisie ni d'un seuil de tables), `contact@tawla.tn` reste en dur (`app/page.tsx`) | Mentions légales et e-mail restent à changer (§3.4) ; la copie elle-même n'a plus besoin de réécriture par marché |

#### À ajouter — ce que le marché français exige et que le produit n'a pas

Classé par ce que coûte l'absence, du plus cher au moins cher.

| # | Manque | Pourquoi c'est bloquant en France |
|---|---|---|
| **A1** | **Intégration caisse / envoi vers l'existant** | Tout restaurant français a déjà une caisse certifiée. Sans intégration, Tawla crée de la double saisie — le motif de refus n° 1. Cible réaliste au départ : **une seule** intégration, celle du premier pilote, plus une impression cuisine |
| **A2** | **Options et suppléments sur un article** (cuisson, accompagnement au choix, sauce, taille, « sans oignons ») | Aujourd'hui il n'y a qu'une note en texte libre (`OrderItem.notes`, 300 caractères). Un steak sans cuisson ne part pas en cuisine en France. C'est le manque **fonctionnel** le plus grave |
| **A3** | **Formules / menu du jour** (entrée + plat + dessert, formule midi) | Le produit dominant du déjeuner français. Classé « Sous condition » dans `ROADMAP.md` pour la Tunisie ; en France c'est structurant |
| **A4** | **TVA multi-taux + note conforme** | §3.1 (3). Colonne sur `MenuItem`, ventilation, HT/TVA/TTC, seuil 25 € |
| **A5** | **Addition au niveau de la table + paiement par convive** | Sunday a fait de « chacun paie sa part » son produit. Aujourd'hui `payment_status` vit sur `Order` et `SplitBill` n'est qu'un **calculateur indicatif** (son propre commentaire le dit). Sous S1 le sujet disparaît ; sous S2 il devient prioritaire |
| **A6** | **Allergènes structurés (INCO)** + mentions « fait maison », origine des viandes | Obligation légale + confiance client |
| **A7** | **Demande d'avis Google après le service** | Argument de vente central des concurrents français, coût de développement faible, valeur perçue forte |
| **A8** | **Titres-restaurant** | Plus de 75 % des titres sont dématérialisés en 2026, plafond légal 25 €/jour, commissions émetteur de 3 à 5 %. **Recommandation : ne pas l'intégrer en ligne** — le titre se règle au comptoir sur le terminal du restaurant. Mais la question sera posée à chaque rendez-vous : il faut une réponse préparée, pas un silence |
| **A9** | **Anglais** au parcours client | Zones touristiques. Le dictionnaire existe déjà en deux langues, en ajouter une troisième est mécanique |
| **A10** | **Multi-établissements sous un même compte** | Les groupes de 2 à 10 adresses sont courants en France. Classé « Sous condition » pour la Tunisie ; en France ça arrivera plus tôt |
| **A11** | **Sélecteur de pays sur l'URL globale** | La demande explicite de Wassim — spécifiée en §5, livrée en F4 |

### 3.3 Différences techniques

| Sujet | Tunisie | France | Impact |
|---|---|---|---|
| **Hébergement** | Render/Railway + Vercel, région indifférente | **Union européenne obligatoire en pratique** (RGPD : transfert hors UE possible mais à encadrer et à justifier — un restaurateur ne signera pas un DPA qui parle de clauses contractuelles types). Options : Render/Railway région Francfort, ou Scaleway / Clever Cloud / OVH pour pouvoir écrire « hébergé en France » | Déploiement séparé, base séparée |
| **Base de données** | Une base | **Une base par marché.** Ce n'est pas une préférence : c'est la conséquence de la résidence des données et de l'isolation des pannes | Deux Postgres, deux sauvegardes, deux restaurations testées |
| **Instance backend** | Une seule (WebSocket + limiteur en mémoire) | Une seule **par marché**. La contrainte est inchangée, elle est simplement doublée | — |
| **Fuseau** | Décalage fixe +1 | `zoneinfo`, heure d'été | Correctif à faire **avant** le premier pilote français |
| **Envoi d'e-mails** | Resend, `contact@tawla.tn` | Domaine français, SPF/DKIM/DMARC à refaire, et la mention RGPD dans le pied de page | Configuration |
| **Passerelle de paiement** | Konnect (TND, millimes) | **Stripe Connect** recommandé — le restaurant est le marchand, Tawla ne touche jamais les fonds. C'est exactement le modèle déjà retenu pour Konnect (« chaque restaurant connecte son propre wallet », `Restaurant.konnect_api_key_encrypted`), donc le patron de code transfère | Nouvel adaptateur, ancien conservé |
| **Statut réglementaire du paiement** | Non traité | Encaisser pour le compte d'un tiers en France ⇒ statut d'agent/établissement de paiement. **À éviter absolument** en gardant le restaurant marchand de bout en bout | Choix d'architecture, pas d'implémentation |
| **CI** | Une pipeline | Inchangée — un seul dépôt (§4) | — |
| **Tests** | 299 tests backend, **zéro test frontend** | La couche marché est exactement le genre de code qui casse en silence (mauvaise devise, mauvais taux de TVA). Des tests de la couche marché sont **obligatoires**, y compris côté frontend pour le formateur monétaire | Nouvelle exigence |

### 3.4 Différences commerciales

#### Le prix ne se convertit pas, il se re-dérive

Convertir 50/100/150 DT donne ≈ 15/30/45 €. **Ce serait une erreur de
positionnement** : en France, 15 €/mois classe le produit dans la catégorie
« menu PDF avec un QR code », qui se vend déjà 25 à 35 €/mois sans commande ni
écran cuisine. Un prix trop bas rend le service inclus impossible à financer et
signale un produit jetable.

Repères du marché français, à confronter en F1 :

| Catégorie | Repère observé | Ce qui est vendu |
|---|---|---|
| Menu digital passif | 25 à 35 €/mois | Une carte en ligne derrière un QR |
| Commande + paiement à table | Modèles mixtes : abonnement, ou commission sur les paiements, ou frais au client final | Sunday (~1 500 restaurants en France), Qwick Order (abonnement + 0,10-0,15 € par paiement), TastyCloud (paliers) |
| Caisse + écosystème | Plusieurs dizaines à centaines d'€/mois | L'Addition, Tiller/SumUp, Zelty, Lightspeed, Innovorder |

**Hypothèse de départ à tester, jamais à annoncer avant F1** : 49 / 89 / 149 €
HT/mois, service d'installation inclus, sans commission sur les commandes.
L'argument reste celui qui marche déjà : *le produit mesure les commandes
perdues et les affiche*. À 30 € de panier moyen, **une commande perdue par
semaine paie l'abonnement**, et ce n'est pas une promesse — c'est un chiffre que
l'écran affiche avec sa définition.

La règle de `ROADMAP.md` reste : **le prix ne bouge jamais une fois annoncé à un
restaurateur ; le périmètre, oui.**

#### La proposition de valeur doit changer d'axe

| | Tunisie | France |
|---|---|---|
| Différenciateur principal | « On vient chez vous » — un éditeur libre-service ne le fera jamais | **Ne tient plus** : les concurrents financés viennent aussi |
| Axe de remplacement n° 1 | — | **La mesure avant/après.** Personne d'autre ne vend « voici combien de commandes vous perdiez, voici combien vous en perdez maintenant » |
| Axe de remplacement n° 2 | — | **Le segment maghrébin** : bilingue fr/ar, mode Ramadan et pré-commande iftar déjà codés. Un patron de restaurant à Barbès, à la Guillotière ou à Marseille n'a aujourd'hui **aucune** solution qui parle la langue de sa salle |
| Axe de remplacement n° 3 | — | **Zéro traceur, zéro cookie, hébergé en UE**, le restaurant reste marchand et encaisse en direct. C'est vrai dans le code, et c'est vendable |
| Ce qui ne marchera pas | — | Se comparer à Sunday sur le paiement. Ils ont quatre ans d'avance, des fonds, et le paiement est exactement ce que la stratégie S1 nous fait retirer |

#### Le brief de marque

« Tawla » (طاولة, « table ») est un bon nom en Tunisie et un nom neutre mais
opaque en France. Trois questions à trancher (🧑) :

1. Garde-t-on le nom sur les deux marchés ? (cohérence, un seul actif de marque)
2. Recherche d'antériorité **INPI** en classes 9 et 42 — obligatoire avant toute
   dépense de marque.
3. Domaines : `tawla.fr`, `tawla.eu`, et un domaine **hub** neutre pour le
   sélecteur de pays (§5). `tawla.com` est cité dans `AUDIT_COUTS_PRODUCTION.md`
   comme filet — c'est le candidat naturel pour le hub.

---

## 4. Architecture : deux marchés sans faire deux produits

### Les trois options

| | Option | Ce que ça donne | Verdict |
|---|---|---|---|
| **A** | **Deux dépôts** (fork) | Démarrage immédiat, divergence irréversible en trois mois. Chaque correctif de sécurité à faire deux fois, par un fondateur seul | ❌ Rejeté |
| **B** | **Un dépôt, une couche marché, deux déploiements** | `MARKET=tn\|fr` en variable d'environnement. Un backend + un frontend par marché, une base par marché, **une seule** CI et une seule base de code | ✅ **Retenu** |
| **C** | **Un déploiement, `Restaurant.market`** | Un seul service pour les deux pays | ❌ Rejeté : données françaises hors UE ou données tunisiennes dans l'UE, une panne tunisienne coupe les clients français, et la contrainte « une seule instance backend » (WebSocket en mémoire) devient un plafond commun |

### Ce que la couche marché doit contenir — et rien d'autre

Un module unique, côté backend (`app/core/markets.py`) et son miroir côté
frontend (`lib/market.ts`), chargé **une fois** au démarrage depuis `MARKET` :

```
Market
├── code                 "tn" | "fr"
├── devise               symbole, décimales (3 | 2), séparateur, position
├── fuseau               ZoneInfo("Africa/Tunis") | ZoneInfo("Europe/Paris")
├── paliers              prix + contenu de l'offre (remplace TIER_PRICES_TND / offer.ts)
├── paiement             adaptateur "konnect" | "stripe" | "aucun"
├── tva                  taux applicables, seuil de note obligatoire (25 € en FR)
├── langues              ["fr","ar"] | ["fr","en"] (+ "ar" optionnel par établissement)
├── fonctionnalites      ramadan, halal, fidélité, pourboire, encaissement… (drapeaux)
├── textes légaux        confidentialité, CGV, mentions légales, DPA
└── contenus             démo, visite guidée, anecdotes, chevalet QR, catégories de carte
```

**Règle durable à écrire dans `CLAUDE.md` le jour où F3 est livrée** : plus
jamais de devise, de fuseau, de taux, de prix ni de texte légal en dur dans un
composant ou un service. Tout passe par la couche marché. C'est la seule
protection contre la divergence, et elle ne tient que si elle est vérifiée par
un test (un test qui balaie le code à la recherche de `"DT"`, `€`, `toFixed(3)`
hors du formateur, coûte dix lignes et rend la règle réelle).

### Le port de paiement

`orders/service.py` importe aujourd'hui `core/konnect.py` directement (7
symboles). À extraire en interface :

```
PaymentProvider (port)
├── init_payment(montant, devise, retour, webhook) -> (url, ref)
├── get_payment(ref)                               -> statut, montant atteint
├── verify_webhook(payload, signature)             -> bool
└── supports_refund()                              -> bool
    ├── KonnectProvider  (existant, TND, millimes)
    ├── StripeProvider   (écrit 2026-09-01, EUR, Connect — le restaurant est marchand)
    └── NullProvider     (mode S1 : aucun encaissement dans Tawla)
```

`NullProvider` n'est pas un bouche-trou : c'est **le** mode par défaut du marché
français sous la stratégie S1 (§3.1).

### Ce que ça coûte

| Chantier | Estimation | Remarque |
|---|---|---|
| Couche marché + formateur monétaire + fuseau | 3-5 jours | Le formateur touche ~20 fichiers, mécanique mais à tester |
| Extraction du port de paiement | 2-3 jours | Le code est déjà bien isolé |
| Contenus par marché (démo, visite, chevalet, catégories, textes) | 3-4 jours | Surtout de la rédaction |
| Sélecteur de pays + domaines + SEO (§5) | 2-3 jours | Voir F4 |
| **Sous-total « rendre deux marchés possibles »** | **~2 semaines** | Sans aucune fonctionnalité française |
| Adaptations produit France (A2, A3, A4, A6, A7) | 3-4 semaines | Sans A1 (intégration caisse), sans A5 |
| Intégration caisse (A1), une seule cible | 2-4 semaines | Dépend entièrement de l'API du partenaire — inchiffrable avant F1 |

---

## 5. Le sélecteur de pays — spécification

C'est la demande explicite de Wassim : *« l'URL globale doit rediriger vers le
choix du pays, puis vers le bon projet »*. Livré en **F4**.

### La règle qui prime sur tout le reste

> **Le parcours client ne passe JAMAIS par le sélecteur.**

Un client attablé qui scanne le QR de sa table doit arriver sur le menu, point.
Lui demander son pays devant son assiette, c'est ajouter un écran entre lui et
sa commande — exactement ce que le produit vend le contraire. Les chevalets QR
portent l'URL **du service de leur marché** (`tawla.fr/menu/<token>`,
`tawla.tn/menu/<token>`), jamais celle du hub. Un test automatisé doit
verrouiller cette règle, sinon elle sera cassée un jour par une redirection
« pratique ».

### Comportement

| Cas | Comportement |
|---|---|
| Arrivée sur le hub, aucun choix mémorisé | Page de choix : deux options claires (Tunisie / France), rendues côté serveur, en `<a href>` réels — fonctionne sans JavaScript |
| Pays détecté par l'en-tête `CF-IPCountry` | Sert **uniquement** à mettre l'option probable en premier et à la marquer « détecté ». **Jamais de redirection automatique silencieuse** : mauvaise pour le référencement (contenu masqué au robot), et fausse pour un Tunisien en France ou un Français en Tunisie |
| Choix effectué | Cookie `tawla-market` (1 an, `SameSite=Lax`, sans donnée personnelle), puis redirection **302** vers le domaine du marché |
| Retour sur le hub avec un cookie | Redirection immédiate, avec un lien « changer de pays » visible sur la page d'arrivée |
| `?market=fr` dans l'URL | Force le marché et écrase le cookie — indispensable pour les tests, les démonstrations et les liens de campagne |
| Sur un site de marché, avec un `CF-IPCountry` d'un autre pays | Bandeau discret et fermable : « Vous semblez être en France — voir Tawla France ». Fermable pour toujours (`localStorage`), jamais bloquant |
| `/menu/<token>` sur le mauvais marché | 404 normale. Aucune tentative de « retrouver » la commande sur l'autre service : ce serait une fuite d'existence de ressource entre deux bases |

### Référencement et technique

- `hreflang` : `fr-TN` ↔ `fr-FR` croisés, `x-default` sur le hub.
- `canonical` propre à chaque marché, `sitemap.xml` et `robots.txt` par marché.
- Le hub est **léger** : une page statique, aucun appel API, aucun accès base.
  Il ne doit jamais pouvoir tomber en même temps qu'un backend.
- Deux implémentations possibles : une page statique sur l'hébergeur du
  frontend, ou un Cloudflare Worker (moins de latence, `CF-IPCountry` natif).
  **Recommandation : la page statique** — moins de pièces mobiles, et le hub
  n'est pas un chemin critique de service.
- Accessibilité : cibles tactiles ≥ 44 px, contraste, navigation clavier,
  `lang` correct. Un sélecteur de pays est typiquement l'écran qu'on bâcle.
- Mesure : un compteur agrégé (« combien ont choisi FR ») **sans traceur** —
  sinon on perd l'argument « zéro cookie » du §3.4 pour un chiffre de vanité.

### Critère de sortie de F4

Depuis un téléphone : le hub propose les deux pays, le choix mène au bon
service, le retour est direct, `?market=` force le marché, **et le scan d'un QR
de table n'affiche jamais le sélecteur**, cookie effacé ou non.

---

## 6. La roadmap France, phase par phase

Convention identique à `ROADMAP.md` : 🧑 = demande une décision, un compte réel
ou une présence physique de Wassim ; ⛔ = bloqué sur un arbitrage produit. Une
case cochée doit citer la PR qui l'a livrée.

**Les trois premières phases ne contiennent aucune ligne de code.** C'est
délibéré : elles peuvent tourner en parallèle des phases tunisiennes sans leur
retirer une seule journée de développement, et elles peuvent conclure « on ne va
pas en France », ce qui serait un excellent résultat pour un coût nul.

---

### Phase F0 — La décision (tranchée le 2026-08-24)

- [x] **Scénario retenu : C — les deux marchés en parallèle, tout de suite.**
  Décision explicite de Wassim, sans attendre un jalon tunisien. Le §1
  documente pourquoi ce scénario est normalement le plus risqué des trois
  (« un fondateur, deux marchés ») — retenu quand même, en connaissance de
  cause. Voir §0 pour ce qui atténue ce risque **dans l'état actuel** du
  dépôt : `ROADMAP.md` n'a plus aucune tâche codable non cochée en ce moment,
  donc ce chantier ne dispute encore rien à la Tunisie côté code
- [x] **Déclencheur : aucun.** « Moi et maintenant » — pas de date, pas
  d'événement tunisien à attendre. F1 et F2 s'ouvrent avec cette décision
- [x] **Budget : aucun plafond fixé.** On avance au cas par cas plutôt que sur
  un montant arrêté à l'avance — décision explicite, pas un oubli
- [x] **Marque : ouverte**, « MyTable » proposé par Wassim comme piste sérieuse
  pour le nom international — **à confirmer par une recherche de
  disponibilité avant tout engagement**, voir la note ci-dessous. Rien
  n'élimine « Tawla » côté tunisien dans tous les cas : la question ouverte
  porte seulement sur le nom du marché français/international
- [x] Renvoi posé dans `ROADMAP.md` (§ documents fondateurs, § hors périmètre)
  et dans `CLAUDE.md` (§ Roadmap) — PR #84

> **Sur « MyTable »** : l'idée tient conceptuellement — traduction directe de
> Tawla (« la table »), compréhensible sans effort dans toute l'Europe, garde
> le fil entre les deux marchés. Le risque est réel et concret : c'est un nom
> de forme très générique (« My + nom commun », le schéma de MyFitnessPal,
> MyHeritage…), le genre de nom qui a de bonnes chances d'être déjà pris —
> comme marque, comme domaine, ou comme produit concurrent quelque part dans
> la restauration digitale. **Prochaine action concrète, avant tout
> engagement de communication ou de code sur ce nom** : vérifier la
> disponibilité de `mytable.fr` / `.com` / `.eu`, et lancer une recherche
> d'antériorité INPI en classes 9 et 42 — exactement la case que F0 posait
> déjà pour « Tawla ». Candidats de repli à garder en tête si « MyTable » est
> pris : une variante moins générique du même axe (ex. composé avec « table »
> et un second mot distinctif), à chercher seulement si la vérification
> échoue

**F0 est tranchée. F1 et F2 sont ouvertes dès maintenant.**

---

### Phase F1 — Vingt entretiens de restaurateurs français 🧑

Même méthode que la Phase 21 tunisienne (`terrain/GUIDE_ENTRETIEN.md` : obtenir
le rendez-vous, ne jamais montrer l'application avant la fin, poser la question
de prix franchement). Les questions, elles, changent — voir **Annexe B**.

- [ ] 20 entretiens, dans **deux** segments distincts, et le noter à chaque fois 🧑
  - **Segment 1 — brasserie / bistrot de quartier**, 8 à 20 tables, avec terrasse
  - **Segment 2 — restaurant à clientèle maghrébine** (couscous, grillades, salon de thé), là où le bilingue fr/ar et le mode Ramadan ont une valeur que personne d'autre n'offre
- [ ] Relever pour **chacun** : quelle caisse, quel terminal, quel émetteur de titres-restaurant, quelle solution QR déjà en place, combien elle coûte 🧑
- [ ] Poser la question qui décide de tout : **« si je vous donne un outil qui ne parle pas à votre caisse, vous le prenez ? »** 🧑
- [ ] Créer `terrain/ENTRETIENS_FR.md` sur le modèle du fichier tunisien, et le remplir **sur place** — jamais depuis une session 🧑
- [ ] Écrire la synthèse : les trois douleurs les plus citées, le prix médian accepté, la réaction à 89 €, et **quel segment répond le mieux** 🧑

**Critère de sortie** : savoir si le segment 2 (maghrébin) répond mieux que le
segment 1. C'est la réponse qui décide de tout le positionnement français — et
elle ne se devine pas depuis un dépôt de code.

**Ce qui doit faire abandonner** : si plus de 15 des 20 disent que sans
intégration caisse ils ne prennent rien, alors le marché français coûte
« intégration caisse » **avant** le premier euro, et il faut retourner en F0.

---

### Phase F2 — Cadrage juridique et fiscal 🧑 (avec des professionnels, pas avec Claude)

- [ ] Rendez-vous **expert-comptable** français spécialisé restauration/SaaS 🧑
- [ ] Trancher la question du logiciel de caisse (§3.1) : **S1 (ne pas encaisser)** ou **S2 (être conforme)**, par écrit 🧑 ⛔
- [ ] Faire confirmer les taux de TVA applicables et la frontière sur place / à emporter / alcools 🧑
- [ ] Faire confirmer les mentions obligatoires de la note client (seuil 25 € TTC, arrêté du 3 octobre 1983) 🧑
- [ ] Choisir la structure (micro-entreprise, SASU…), le régime de TVA, et la facturation des abonnements 🧑
- [ ] Se préparer à la facturation électronique : **réception dès septembre 2026**, émission PME **septembre 2027** — choisir une plateforme agréée 🧑
- [ ] Faire relire le montage de paiement : garantir que le restaurant reste **marchand**, et que Tawla n'encaisse jamais pour le compte d'un tiers 🧑
- [ ] Rédiger les trois documents contractuels : **CGV SaaS**, **contrat de sous-traitance RGPD (art. 28)**, **convention de pilote** 🧑
- [ ] **Revérifier l'état du droit sur l'attestation éditeur** — il a changé deux fois en dix-huit mois (§3.1) 🧑

**Critère de sortie** : une note écrite d'une page qui dit « Tawla France
encaisse / n'encaisse pas », et la liste des fonctionnalités que cette réponse
retire ou ajoute. **Toute la Phase F5 en dépend.**

---

### Phase F3 — La couche marché (premier code)

Ne s'ouvre qu'après F2 : coder la couche marché avant de savoir si le marché
français encaisse, c'est coder les mauvais drapeaux.

- [x] `app/core/markets.py` + `lib/market.ts` : devise, fuseau, langues, drapeaux, paliers, TVA, textes — [PR #88](https://github.com/benmesswass/Tawla/pull/88)
- [x] **Formateur monétaire unique** des deux côtés, et suppression des ~20 `toFixed(3)` / `"DT"` en dur (Annexe A). Test qui échoue si un nouveau apparaît — [PR #88](https://github.com/benmesswass/Tawla/pull/88)
- [x] **Fuseau par `zoneinfo`** — `Europe/Paris` avec heure d'été. Test qui prouve qu'une commande du 15 juillet tombe dans la bonne journée de service (`core/dates.py:9`) — [PR #89](https://github.com/benmesswass/Tawla/pull/89)
- [x] Extraire le **port de paiement** (§4) : `KonnectProvider`, `NullProvider`, interface commune, `orders/service.py` ne connaît plus Konnect — [PR #90](https://github.com/benmesswass/Tawla/pull/90)
- [x] Paliers déplacés dans la couche marché (`core/subscription.py:33`, `lib/offer.ts`) — [PR #91](https://github.com/benmesswass/Tawla/pull/91). Scope réduit au prix : `name`/`tagline`/`features` restent la copie tunisienne, le contenu de l'offre par marché reste la ligne suivante, non encore fait
- Contenus par marché — découpé en étapes, comme F4 (démo/visite guidée touchent une zone où la marque française n'est pas encore tranchée, §3.4, 🧑)
  - [x] Catégories de carte : « Ftour » remplacé par « Formules »/« Vins »/« À emporter » (`lib/market.ts::menuCategories`) — étape 6, [PR #96](https://github.com/benmesswass/Tawla/pull/96)
  - [x] Démo (brasserie française, formule du jour, carte des vins — plus jamais « Dar Chaabane ») — étape 7, [PR #97](https://github.com/benmesswass/Tawla/pull/97)
  - [x] Visite guidée — scope réduit : deux inexactitudes corrigées (prix de palier resté en dur, une promesse d'arabe non conditionnelle), pas la refonte de positionnement/paiement — bloquée sur le brief de marque (§3.4) et S1/S2 (§3.1), encore ouverts — étape 8, [PR #98](https://github.com/benmesswass/Tawla/pull/98)
  - [ ] Anecdotes d'attente (`lib/culturalFacts.ts`) — remplacer par du contenu propre au restaurant, ou retirer par drapeau de marché
  - [ ] Chevalet QR (français seul par défaut, anglais optionnel, arabe seulement sur le segment concerné)
- [ ] `MARKET=tn` par défaut : **le produit tunisien ne change pas de comportement**, et la suite de tests existante le prouve
- [x] Écrire la règle « plus jamais de devise/fuseau/taux en dur » dans `CLAUDE.md` — [PR #89](https://github.com/benmesswass/Tawla/pull/89)

**Critère de sortie** : `MARKET=tn` — les 299 tests passent sans modification.
`MARKET=fr` — l'application démarre, affiche des euros, tourne à l'heure de
Paris, et n'expose aucun moyen de paiement.

---

### Phase F4 — L'URL globale et le sélecteur de pays

Spécification complète en §5. Peut se faire avant F5 : elle ne dépend d'aucune
décision produit, seulement des domaines (F0).

- [ ] Réserver les domaines : hub + `tawla.fr` (ou la marque retenue en F0) 🧑
- [x] Page de choix statique, rendue serveur, sans JavaScript obligatoire — `app/choisir-pays` (étape 1, [PR #92](https://github.com/benmesswass/Tawla/pull/92))
- [x] Cookie `tawla-market` (1 an), `?market=` qui force — `app/api/choisir-marche` (étape 1, [PR #92](https://github.com/benmesswass/Tawla/pull/92))
- [x] `CF-IPCountry` pour **ordonner** les options, jamais pour rediriger — `lib/geoMarket.ts` (`x-vercel-ip-country` géré en repli, l'hébergeur réel du frontend) (étape 1, [PR #92](https://github.com/benmesswass/Tawla/pull/92))
- [x] Bandeau fermable « vous semblez être ailleurs » sur chaque marché — `components/BandeauAutreMarche.tsx`, détection via une route API dédiée (`app/api/geo`) pour ne pas sortir tout le site du rendu statique (étape 2, [PR #93](https://github.com/benmesswass/Tawla/pull/93))
- [x] **Test automatisé : `/menu/<token>` n'affiche jamais le sélecteur**, cookie présent ou non — `lib/marketBanner.ts::selecteurAutorise()` + `marketBanner.test.ts`, vérifié aussi par Playwright (bandeau invisible sur `/menu/xxx` même avec en-tête de géoloc simulé) (étape 2, [PR #93](https://github.com/benmesswass/Tawla/pull/93))
- [ ] Lien « changer de pays » visible en permanence (pas seulement quand le bandeau se déclenche) — pas de footer partagé existant sur le site pour l'accrocher proprement, chantier à part
- [x] `hreflang`, `canonical`, `sitemap`, `robots` par marché — `app/robots.ts`, `app/sitemap.ts` (limité aux pages commerciales statiques, volontairement sans les pages `/menu/<token>` par établissement), `alternates` sur `app/page.tsx` (`fr-TN`↔`fr-FR`). `x-default` sur le hub non fait : le hub n'a pas encore son propre domaine (🧑, item juste au-dessus), le poser depuis un déploiement de marché serait trompeur (étape 3, [PR #94](https://github.com/benmesswass/Tawla/pull/94))
- [x] Vérifier l'accessibilité de la page de choix (clavier, contraste, cibles tactiles) — navigation clavier vérifiée par Playwright (Tab atteint les deux options dans le bon ordre, Entrée active), contraste du badge « Détecté » recalculé et corrigé (3.97:1 → 6.0:1, sous puis au-dessus du seuil AA), cibles tactiles déjà ≥56px depuis l'étape 1 (étape 3, [PR #94](https://github.com/benmesswass/Tawla/pull/94))

**Critère de sortie** : celui du §5, vérifié depuis un téléphone réel.

---

### Phase F5 — Les adaptations produit indispensables

Le contenu exact de cette phase **dépend de la réponse de F2**. Les deux
variantes sont écrites ici pour qu'aucune session n'ait à improviser.

**Commun aux deux variantes**

- [x] **A2 — Options et suppléments** sur un article (cuisson, accompagnement, sauce, taille) : nouveau modèle, migration, écran manager, parcours client, affichage cuisine. *Le manque fonctionnel le plus grave (§3.2)* — [PR #87](https://github.com/benmesswass/Tawla/pull/87). v1 : un seul jeu de choix par article au panier (pas de lignes multiples pour deux combinaisons différentes du même plat)
- [ ] **A3 — Formules** (entrée + plat + dessert, formule midi) : composition, prix de la formule, affichage
- [ ] **A6 — Allergènes structurés** (14 allergènes INCO) en remplacement du texte libre (`menu/models.py:67`), `is_halal` par défaut à `false` en France (`menu/models.py:71`) — **reste ouvert**. Le volet « marqueurs » est livré différemment de la spec d'origine : plutôt qu'une liste figée (végétarien/vegan/sans gluten/halal), [PR #87](https://github.com/benmesswass/Tawla/pull/87) donne au manager un **vocabulaire de régimes libre par restaurant** (décision de Wassim, 2026-08-26 — halal n'est pas central hors de Tunisie), coexistant avec `is_halal` plutôt que de le remplacer
- [ ] **A9 — Anglais** au parcours client (`lib/i18n/en.ts`, même forme que `fr.ts`)
- [ ] Arabe **littéraire** proposé en option par établissement, plutôt que la derja tunisienne
- [ ] Mode Ramadan et pré-commande **conservés**, activables par établissement, repositionnés (§3.2)
- [ ] Réécriture RGPD de `lib/i18n/privacy.ts` + page **mentions légales** + page **CGV**
- [ ] Réglage de l'agrégation par défaut du rapport d'équipe + notice d'information des salariés (§3.1 (6))

**Si S1 — Tawla n'encaisse pas** (le plus probable)

- [ ] Retirer du marché français : paiement carte en ligne, espèces, terminal, pourboire, recette du jour, encaissé par serveur — par **drapeau de marché**, jamais par suppression de code (la Tunisie s'en sert)
- [ ] **A1 — Intégration caisse** : une seule cible, celle du premier pilote de F1. À défaut, impression cuisine
- [ ] Réécrire la promesse publique : « Tawla ne remplace pas votre caisse, il remplit votre cuisine » 🧑

**Si S2 — Tawla encaisse et devient conforme**

- [x] **A4 — TVA multi-taux** : `MenuItem.vat_category` (une CLÉ de `Market.vat_rates` — "sur_place"/"a_emporter"/"alcool" — jamais le taux lui-même en dur, migration), copié figé sur `OrderItem.vat_category` à la commande (même principe que `menu_item_name`/`unit_price` : un article reclassé après coup ne change jamais une facture déjà émise), ventilation HT/TVA/TTC PAR TAUX RÉELLEMENT PRÉSENT dans la commande (`core/invoice.py::_vat_rate_for`, une ligne par taux + un total si plus d'un taux). Null = "sur_place" par défaut, sans effet sur la Tunisie (`vat_rates=None`). **Pas encore réglable depuis le dashboard manager** — API/migration seulement, l'UI reste à faire ([PR #TODO](https://github.com/benmesswass/Tawla/pull/148))
- [x] Détail des articles, prix unitaire, totaux HT/TVA/TTC — déjà livré (PR #142, PR #143), ventilé par taux depuis A4 ci-dessus
- [x] **Numérotation continue** — séquence par restaurant (`InvoiceCounter`, `core/invoice_number.py`), format `F<année>-<5 chiffres>`, attribuée une seule fois au paiement confirmé (les 4 chemins : carte, carte physique, espèces, webhook Stripe), immuable ensuite, millésime pris sur la journée de SERVICE (fuseau du marché). Mention obligatoire ajoutée au-delà du seuil (`Market.invoice_threshold`, 25 € TTC en France) sur la note elle-même ([PR #147](https://github.com/benmesswass/Tawla/pull/147))
- [ ] **UI manager pour `vat_category`** — aujourd'hui réglable seulement via l'API (`PATCH /menu-items/{id}`), aucun contrôle sur `frontend/app/dashboard/page.tsx`. Défaut "sur_place" reste correct pour la quasi-totalité de la carte ; seule l'alcool a besoin d'être signalée à la main en attendant
- [ ] Note conforme (art. 289 CGI / arrêté du 3 octobre 1983) : détail, prix unitaire, HT/TVA/TTC et numérotation continue sont TOUS livrés désormais — reste la vérification en conditions réelles sur un restaurant qui vend effectivement de l'alcool
- [ ] **A5 — Addition par table et paiement par convive** (aujourd'hui `payment_status` est porté par `Order`, et `SplitBill` n'est qu'un calculateur)
- [ ] **Conditions ISCA** : journal inaltérable chaîné, clôtures Z/JJ/MM/AA, archivage, attestation éditeur 🧑 ⛔
- [ ] **A8 — Titres-restaurant** : réponse écrite pour les rendez-vous, intégration seulement si un pilote la paie
- [ ] Pourboire en montants ronds (0 / 1 € / 2 € / autre) plutôt qu'en pourcentages (`menu/[qrToken]/page.tsx:1215`)

**Dans les deux cas, en fin de phase**

- [ ] **A7 — Demande d'avis Google** après le service (faible coût, forte valeur perçue en France)
- [ ] Démo française : brasserie, formule du jour, carte des vins — plus jamais « Dar Chaabane » sur le marché français (`demo/service.py:158`)

---

### Phase F6 — Le paiement français (uniquement si S2)

- [x] Ouvrir le compte **Stripe** 🧑 — fait le 2026-09-01 (Wassim), compte "TAWLA" activé (identité + IBAN acceptés côté Stripe)
- [x] `StripeProvider` derrière le port de F3 — **Connect (Direct Charges), le restaurant est le marchand**, Tawla ne touche jamais les fonds. `core/stripe_gateway.py` + `StripeProvider` (2026-09-01) : mêmes garanties que Konnect (dégradation gracieuse, `PAYMENT_MODE=stripe` explicite requis — c'est le drapeau démo/prod de l'Annexe C2), testé unitairement (monkeypatch, aucun appel réseau réel). `FRANCE.payment_provider` bascule sur `"stripe"`
- [x] Connexion du compte par chaque restaurant depuis son dashboard — migration `Restaurant.stripe_account_id` (en clair, pas chiffré : pas un secret, voir son docstring dans `models.py`), endpoint `POST /{restaurant_id}/stripe-connect/start` (Account Links, onboarding hébergé par Stripe — jamais de formulaire local, contrairement à Konnect), bouton dashboard manager. **Vérifié en conditions réelles le 2026-09-01/02** contre le compte Stripe de test de Wassim, onboarding complété (données de test) jusqu'au badge "Connecté"
- [x] Abonnement Tawla payé en euros — **récurrent** (mode Netflix : facturation automatique chaque mois tant que le restaurant ne se désabonne pas lui-même, retour utilisateur 2026-09-02), pas un simple virement/facture manuelle. Konnect exclu de ce modèle : pas de carte enregistrée, pas de récurrence dans son API — reste Stripe/France uniquement.
  - `Restaurant.stripe_customer_id`/`stripe_subscription_id` (migration, en clair — pas des secrets), `stripe_gateway.create_subscription_checkout_session` (mode `subscription`, prix recalculé serveur comme partout ailleurs), `create_billing_portal_session` (portail Stripe hébergé — annuler/changer de moyen de paiement sans écran à maintenir côté Tawla)
  - Webhook unique `POST /api/v1/restaurants/stripe-subscription-webhook` (`handle_stripe_subscription_event`, signature vérifiée via `STRIPE_WEBHOOK_SECRET`) : `checkout.session.completed` (lie le restaurant au client/abonnement Stripe), `invoice.paid` (chaque échéance, `subscription_period_end` relu depuis Stripe — jamais un `+30 jours` calculé nous-mêmes), `customer.subscription.deleted` (annulation — efface juste `stripe_subscription_id`, la dégradation à Essentiel se fait ensuite toute seule via `effective_tier()`, comme un renouvellement Konnect manqué)
  - **Vérifié le 2026-09-02** : création de session récurrente réelle contre le compte Stripe de test (200, vraie URL Checkout) ; les trois évènements webhook testés en isolation avec des évènements synthétiques (liaison, renouvellement avec relecture `current_period_end`, annulation) — tous corrects. **Non vérifiable en local** : la livraison réelle Stripe → serveur (Stripe ne joint pas `localhost` ; ni Stripe CLI ni tunnel disponibles sur ce poste) — à confirmer une fois l'endpoint déclaré côté tableau de bord Stripe (prod ou via `stripe listen`)
- [x] Montant revérifié côté serveur avant règlement (paiement carte du CLIENT, Connect — pas l'abonnement Tawla ci-dessus) — **flux complet vérifié en conditions réelles le 2026-09-02** : commande créée → `pay/card` → vraie session Stripe Checkout → paiement par carte de test (4242...) → `settle_card_payment` réinterroge Stripe (pas de confiance aveugle au retour client) → commande marquée payée en base (`payment_status=paid`, `paid_at` renseigné). Reste ouvert : la vérification de **signature webhook Connect** elle-même (route + secret d'endpoint à déclarer côté tableau de bord Stripe) — le test ci-dessus est passé par le filet de sécurité `/pay/card/check` (retour client), pas par un webhook Stripe réel ; distinct du webhook d'abonnement ci-dessus, déjà câblé

---

### Phase F7 — Conformité et contrats avant le premier client 🧑

- [ ] Hébergement **UE** provisionné (backend, base, frontend) 🧑
- [ ] Registre des traitements écrit 🧑
- [ ] **DPA (art. 28)** prêt à signer, liste des sous-traitants ultérieurs publiée 🧑
- [ ] Tableau des durées de conservation par donnée, aligné sur le code (`loyalty/service.py:19`, purge existante) et vérifié par un test
- [ ] Procédure de réponse aux droits (accès, effacement, portabilité) — une adresse qui répond sous un mois 🧑
- [ ] Sauvegardes automatiques **et une restauration réellement effectuée** sur une base jetable — la ligne que `ROADMAP.md` désigne comme celle qu'on est tenté de sauter, et la seule qui prouve les autres 🧑
- [ ] Supervision `/health`, collecte des erreurs, monitoring externe 🧑
- [ ] Assurance RC professionnelle 🧑

---

### Phase F8 — Deux pilotes français, puis un client payant 🧑

Même discipline que la Phase 23 tunisienne, et pour la même raison : **c'est la
mesure « avant » qui rend la démonstration « après » vendable.**

- [ ] Disqualifier à la porte : moins de 8 tables, pas de réseau exploitable en salle 🧑
- [ ] Accord écrit d'une page : quatre semaines d'usage effectif, droit de citer, droit de publier les chiffres 🧑
- [ ] **Relever la semaine de référence à la main, avant activation** (commandes perdues par service, panier moyen) 🧑 — impossible à rattraper après
- [ ] Arriver avec **sa** carte déjà chargée (`setup_restaurant.py` + import CSV, déjà outillés) 🧑
- [ ] Former l'équipe sur place, dix minutes pendant un service creux 🧑
- [ ] Tenir un journal de pilote le soir même de chaque service observé 🧑
- [ ] Remplir les résultats de pilote (`PILOT_RESULTS`) avec des chiffres **réellement relevés**, chez un établissement qui a donné son accord écrit 🧑
- [ ] Premier abonnement français encaissé 🧑
- [ ] Mesurer les deux chiffres qui décident de la suite : durée réelle d'une installation, minutes de support par client et par semaine 🧑

**Critère de sortie** : un restaurant français qui paie, et un chiffre relevé
chez lui qu'on a le droit de citer.

---

## 7. Sous condition — ne pas ouvrir sans le déclencheur nommé

| Chantier | Déclencheur exact |
|---|---|
| **Deuxième et troisième intégration caisse** | Deux prospects perdus pour cette seule raison, sur la même caisse |
| **Conformité ISCA complète (S2)** | Un client qui la réclame **et** qui paie, ou l'abandon de la stratégie S1 |
| **Titres-restaurant en ligne** | Trois patrons qui le citent comme motif de refus, chiffres à l'appui |
| **Accessibilité RGAA / EN 301 549** | Le premier prospect de plus de 10 salariés (l'exemption micro-entreprise tombe) |
| **Multi-établissements** | Un groupe de 2 adresses ou plus qui signe |
| **Click & collect / à emporter** | Un pilote qui le demande — attention, ça change le taux de TVA |
| **Espagne / Belgique / Italie** | Deux clients payants en France, pas avant. La couche marché du F3 rend l'ajout mécanique ; c'est la distribution qui ne l'est pas |
| **Application mobile native** | Jamais sans un besoin nommé — le web installable (PWA) fait déjà le travail |

## 8. Hors périmètre France, définitivement

- **Réservation de table** — TheFork occupe la place, c'est un autre produit
- **Livraison / marketplace** — Uber Eats, Deliveroo : autre métier, autre économie
- **Devenir établissement de paiement** — le restaurant reste marchand, toujours (§3.3)
- **Concurrencer Sunday sur le paiement à table** — quatre ans d'avance, des fonds, et c'est exactement ce que S1 nous fait retirer
- **Traduire la derja tunisienne pour la France** — l'arabe français est littéraire ou dialectal maghrébin, jamais tunisien

## 9. Budget et calendrier

**Coûts récurrents supplémentaires**, en plus de la Tunisie (le hub est
négligeable) :

| Poste | Ordre de grandeur | Remarque |
|---|---|---|
| Backend + Postgres UE | ≈ 20-40 €/mois | Même dimensionnement qu'en Tunisie |
| Frontend | 0 à 20 €/mois | Selon le palier de l'hébergeur |
| Domaines (`.fr` + hub) | ≈ 30 €/an | |
| Expert-comptable | ≈ 100-200 €/mois | **Le vrai coût du marché français**, et il n'est pas optionnel |
| Structure, RC pro, plateforme de facturation | à chiffrer en F2 🧑 | |

Le poste dominant n'est pas technique. C'est le **temps** : F1 (20 entretiens) et
F8 (2 pilotes) sont des mois de terrain, pas des semaines de code.

**Calendrier, sous le scénario B** — les dates ne s'ouvrent que quand la ligne
tunisienne correspondante est atteinte, pas au calendrier :

| Quand | Phases France | Condition d'ouverture |
|---|---|---|
| Maintenant | F0 | Décision de Wassim |
| En parallèle des Phases 21-24 | F1, F2 | Ne consomme aucune journée de développement |
| Après le 2ᵉ client tunisien payant | F3, F4 | ~2 semaines de code |
| Ensuite | F5, F6, F7 | 4 à 8 semaines selon S1/S2 |
| Ensuite | F8 | 3 à 4 mois de terrain |

## 10. Les risques, et comment on saura qu'on s'est trompé

| Risque | Signal précoce | Ce qu'on fait |
|---|---|---|
| **La double saisie avec la caisse tue chaque rendez-vous** | Dès les 5 premiers entretiens de F1 | Retour en F0 : soit intégration caisse d'abord, soit abandon |
| **Le produit doit être plus petit qu'en Tunisie (S1)** | Décision de F2 | L'assumer et le vendre : « on ne touche pas à votre caisse » est un argument, pas une excuse |
| **Le prix français ne se trouve pas** | Réaction à 89 € en F1 | Ne jamais baisser le prix ; réduire le périmètre (règle de `ROADMAP.md`) |
| **Deux marchés diluent un fondateur seul** | Une semaine sans avancer ni sur l'un ni sur l'autre | Le scénario C est déjà classé perdant. Revenir à B, un chantier à la fois |
| **La conformité fiscale change encore** | Elle a changé deux fois en dix-huit mois | Ne jamais coder sur ce fichier : revérifier en F2, à la source |
| **La divergence des deux bases de code** | Un correctif appliqué à un seul marché | La couche marché du F3, et le test qui interdit le code en dur |
| **La note tunisienne baisse pendant qu'on regarde la France** | La grille de `ROADMAP.md` à la clôture de chaque phase | C'est le vrai coût du scénario C, et la raison du gel du §0 |

## 11. Sources

Consultées le 2026-08-24. Ce qui n'a pas pu être vérifié est écrit comme tel
dans le corps du document.

- Logiciel de caisse, certification et attestation éditeur : [leo2](https://www.leo2.fr/2025/02/10/systeme-de-caisse-la-certification-nf525-ou-lne-devient-obligatoire/), [Kohen Avocats](https://kohenavocats.fr/2026/05/05/logiciel-caisse-certifie-2026-autocertification-amende-controle-fiscal/), [Agiris](https://www.agiris.fr/articles/logiciel-de-caisse-certifie-nf525-lne-obligations)
- Note obligatoire dès 25 € TTC : [Arrêté n° 83-50/A du 3 octobre 1983, Légifrance](https://www.legifrance.gouv.fr/loda/id/JORFTEXT000000494187), [DGCCRF — restaurants, droits et obligations](https://www.economie.gouv.fr/dgccrf/les-fiches-pratiques/restaurants-droits-et-obligations-des-professionnels)
- Facturation électronique, calendrier 2026-2027 : [Pennylane](https://www.pennylane.com/fr/fiches-pratiques/facture-electronique/facturation-electronique-dates-cles-et-calendrier), [Cegid](https://www.cegid.com/fr/facture-electronique-obligatoire/calendrier-facture-electronique/)
- Accessibilité (European Accessibility Act) : [DGCCRF](https://www.economie.gouv.fr/dgccrf/les-fiches-pratiques/professionnels-vos-produits-et-services-doivent-etre-conformes-la-directive-accessibilite), [Bird & Bird](https://www.twobirds.com/fr/insights/2026/france/accessibilit-numrique--ce-qui-change-pour-les-sites-e-commerce-depuis-juin-2025)
- Titres-restaurant (dématérialisation, plafond, commissions) : [economie.gouv.fr](https://www.economie.gouv.fr/entreprises/gerer-ses-ressources-humaines-et-ses-salaries/titres-restaurant-les-5-informations-connaitre), [comparatif 2026](https://www.qvt-market.com/comparatif-des-emetteurs-de-titres-restaurant-2026-edenred-pluxee-swile-bimpli-up)
- Concurrence : [Sunday, levée et objectifs 2026 (Boursorama)](https://www.boursorama.com/actualite-economique/actualites/restauration-l-application-de-paiement-par-qr-code-sunday-veut-doubler-de-taille-en-2026-9c32a9621e69776fb2f936142df337ed), [sundayapp.com](https://sundayapp.com/fr/comment-fonctionne-le-paiement-par-qr-code/), [tarifs menu digital 25-35 €/mois](https://idmenu.fr/produit/abonnement-mensuel-menu-digital-qr-code/)

**Avertissement** : rien de ce qui précède n'est un avis juridique ou fiscal.
Les points de §3.1 doivent être confirmés en F2 par un professionnel français.
Le droit applicable au logiciel de caisse a changé deux fois entre 2025 et 2026.

---

## Annexe A — Inventaire du « Tunisie en dur » dans le code

Relevé le 2026-08-24 sur `main` (`8197ab0`). C'est la liste de travail de la
Phase F3 : chaque ligne est un endroit où le pays est écrit dans le code au lieu
d'être lu dans la configuration.

### Monnaie et format

| Fichier | Ce qui est en dur |
|---|---|
| `frontend/lib/i18n/fr.ts:9,54,56,58,61,111,115,116` | `currency: "DT"` et sept `toFixed(3)` dans les libellés |
| `frontend/lib/i18n/ar.ts:9,54,55,57,107,111,112` | Idem, en `د.ت` |
| `frontend/app/menu/[qrToken]/page.tsx:1123,1142,1150,1216,1401,1603,1732,1774` | Huit affichages de montant en `toFixed(3)` |
| `frontend/app/dashboard/page.tsx:783` · `preuve/page.tsx:37` · `equipe/page.tsx:62,207` · `staff/page.tsx:540,814` | Montants + `"DT"` |
| `frontend/app/admin/page.tsx:27` | `toFixed(2)` + `"DT"` — **déjà incohérent** avec le reste (3 décimales ailleurs) |
| `frontend/components/RecetteDuJour.tsx:20` · `MaSoiree.tsx:28` · `SplitBill.tsx:144` · `lib/shareCard.ts:145` | Montants |
| `backend/app/core/invoice.py:49,50,56,59,63` | Facture PDF entièrement en `DT`, **sans aucune ventilation de TVA** |
| `backend/app/core/subscription.py:33` | `TIER_PRICES_TND` |
| `backend/app/core/konnect.py` | `tnd_to_millimes()`, `"token": "TND"` |
| `frontend/lib/offer.ts:22,32,47,64` | `priceDT` : 50 / 100 / 150 |

### Temps

| Fichier | Ce qui est en dur |
|---|---|
| `backend/app/core/dates.py:9` | `TUNIS = timezone(timedelta(hours=1))` — **faux 7 mois par an en France** |
| `backend/app/core/dates.py:19` | `SERVICE_DAY_START_HOUR = 5` — hypothèse tunisienne à reconfronter |
| `frontend/app/staff/page.tsx` | `ATTENTE_ALERTE_MINUTES = 10 min` — idem |

### Culture, langue, contenu

| Fichier | Ce qui est en dur |
|---|---|
| `frontend/lib/culturalFacts.ts` | 8 anecdotes tunisiennes × 2 langues |
| `frontend/lib/menuCategories.ts:6` | Catégorie « Ftour » |
| `frontend/lib/i18n/ar.ts` | Derja tunisienne (pas de l'arabe standard) |
| `frontend/lib/fonts.ts` | Cairo (arabe) chargée systématiquement |
| `backend/app/modules/tables/poster.py:239` + blocs `_arabic()` | Chevalet bilingue fr/ar, « Propulsé par Tawla · tawla.tn » |
| `backend/app/modules/tables/qr_card.py` | Français seul, sans façonnage arabe (documenté) |
| `backend/app/modules/demo/service.py:158,181` | Démo « Dar Chaabane », e-mails `@…demo.tawla.tn` |
| `frontend/lib/visite/etapes.ts` | Contenu de la visite guidée, `tawla.tn` cité |
| `frontend/app/page.tsx` | `contact@tawla.tn` (la copie publique ne mentionne plus la Tunisie ni un seuil de tables — retour démo 2026-08-31) |
| `frontend/lib/shareCard.ts:12,19` | Pied de carte `tawla.tn` |

### Métier et droit

| Fichier | Ce qui est en dur |
|---|---|
| `backend/app/modules/menu/models.py:71` | `is_halal` par défaut à `True` (norme tunisienne) |
| `backend/app/modules/menu/models.py:67` | Allergènes en texte libre — insuffisant pour la réglementation INCO |
| `backend/app/modules/menu/csv_import.py:33` | Colonne CSV `halal` reconnue à l'import |
| `backend/app/modules/tenants/models.py:42,43` | `ramadan_mode_enabled`, `iftar_time` |
| `frontend/lib/i18n/privacy.ts` | Politique écrite pour la loi tunisienne 2004-63 |
| `backend/app/modules/loyalty/service.py:19` | `RETENTION_WITHOUT_ORDER = 730 j` — à justifier au regard du RGPD |
| `backend/app/core/config.py:44` | `vapid_contact_email = "contact@tawla.tn"` |
| `backend/app/core/konnect.py` (tout) + `Restaurant.konnect_*` | Passerelle tunisienne |
| `backend/app/modules/orders/models.py` (`PaymentMethod`, `tip_amount`) | Enregistrement des règlements — cœur de la question §3.1 |

---

## Annexe B — Le guide d'entretien français, en écart du guide tunisien

`terrain/GUIDE_ENTRETIEN.md` reste valable sur la **méthode** (obtenir le
rendez-vous, ne jamais montrer l'application avant la fin, poser la question de
prix franchement). Ce qui change, ce sont les questions — et une seule d'entre
elles peut renvoyer tout le projet en F0.

**Questions à ajouter**

1. **« Quelle caisse utilisez-vous ? »** — puis : *« si mon outil ne parle pas à
   votre caisse, vous le prenez quand même ? »*. **C'est la question qui décide
   du marché français.** Elle se pose tôt, et la réponse se note mot pour mot.
2. « Combien vous coûte votre solution actuelle, tout compris — abonnement,
   commissions, terminal ? »
3. « Vos clients paient en titres-restaurant ? Quelle proportion ? »
4. « Vous avez déjà été démarché par Sunday ou un équivalent ? Qu'est-ce qui
   vous a fait dire non — ou oui ? »
5. « Vos clients demandent-ils à payer chacun leur part ? »
6. « Comment gérez-vous aujourd'hui les allergènes, et les cuissons ? »
7. **Segment 2 seulement** : « une carte en arabe pour vos clients, ça change
   quelque chose ? » et « comment se passe le service pendant le Ramadan ? »

**Questions à retirer**

- Tout ce qui touche le mode Ramadan hors du segment 2.
- « Avez-vous du Wi-Fi à toutes les tables ? » — la 4G/5G française rend le
  critère de disqualification tunisien beaucoup moins discriminant. Le remplacer
  par : « y a-t-il des zones sans réseau — cave, salle du fond, terrasse
  couverte ? »

**Ce qu'il faut écouter, et qui n'apparaît dans aucune question** : à quel
moment le patron parle de sa caisse **spontanément**. S'il en parle avant qu'on
la mentionne, c'est que le sujet est central, et la stratégie S1 (§3.1) devient
non seulement acceptable mais **vendable**.

---

## Annexe C — Les décisions ouvertes pour Wassim 🧑

Aucune de ces questions ne peut être tranchée depuis une session Claude. Elles
sont listées ici pour qu'aucune ne se règle par défaut, en silence.

| # | Décision | Bloque | Statut |
|---|---|---|---|
| ~~C1~~ | ~~Scénario A, B ou C du §1~~ | — | ✅ Tranchée 2026-08-24 : **C** (§ Phase F0) |
| **C2** | S1 (ne pas encaisser) ou S2 (être conforme au fisc) | F5, F6, et la promesse commerciale | **Décision de travail de Wassim (2026-08-26) : S2** — construit techniquement en entier, mais l'encaissement réel reste **désactivé par défaut en production** (drapeau de marché, § « Le port de paiement ») tant que la confirmation professionnelle (expert-comptable, ISCA) n'est pas faite ; actif en démo. Ne remplace pas F2 : le rendez-vous comptable + la revérification ISCA restent dus avant toute activation réelle |
| **C3** | Segment prioritaire : brasserie de quartier, ou restaurants à clientèle maghrébine | Le positionnement, la démo, la langue, la carte | Ouverte — se tranche en F1, à l'écoute des entretiens |
| **C4** | La marque internationale : « Tawla » ou un autre nom ; recherche INPI ; domaines | F4 | Amorcée 2026-08-24 : « MyTable » proposé, disponibilité à vérifier (§ Phase F0) |
| **C5** | Le prix français (hypothèse 49/89/149 €, à ne pas annoncer avant F1) | F1 | Ouverte |
| **C6** | Structure juridique et hébergeur (« hébergé en France » comme argument, ou pas) | F2, F7 | Ouverte |
| **C7** | Le mode Ramadan reste-t-il visible sur le marché français, ou seulement sur le segment 2 ? | F5 | Ouverte |
| **C8** | Qui fait les 20 entretiens français, et quand | F1 | Ouverte — c'est la prochaine décision concrète, F1 est ouverte |

---

**Dernière mise à jour** : 2026-08-24. F0 tranchée (scénario C). Prochaine
action concrète : **C8** — caler les premiers entretiens F1 — et vérifier la
disponibilité de « MyTable » (C4) avant tout engagement dessus.
`ROADMAP.md` reste le fichier de pilotage prioritaire pour tout ce qui est
codable ; ce fichier pilote le chantier France en parallèle, pas à sa place.
