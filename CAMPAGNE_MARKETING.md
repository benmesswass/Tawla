# Campagne marketing & acquisition — Tawla

*Rédigé le 2026-08-28. Doc de pilotage du chantier marketing, même esprit que
`MARCHE_FRANCE.md` pour le chantier France : renvoie vers des documents
détaillés plutôt que de tout dupliquer.*

## 0. Ce que ce fichier est — et ce qu'il n'est pas

**`ROADMAP.md` pilote le code produit et la mise en ligne.** Rien ici ne le
remplace, ne le réordonne, ne le contredit — les phases 19bis à 24
continuent dans leur ordre, avec leur règle (« une seule phase de code avant
la mise en ligne, et plus rien ensuite avant le premier pilote »). Une
session qui cherche « la prochaine tâche codable » va toujours dans
`ROADMAP.md` en premier.

Ce fichier-ci est le **programme du seul chantier marketing/acquisition**, à
travailler à côté, jamais à la place. Il ne pilote aucune tâche produit — il
outille les tâches 🧑 déjà écrites dans `ROADMAP.md` (Phases 21, 23, 24) et
prépare la seule vraie campagne publique (Ramadan, Horizon 2), sans jamais
en avancer le déclenchement.

## 1. Ce qui est déjà tranché — voir `.agents/product-marketing.md`

Positionnement, ICP, différenciation, ton de marque : tout est dans
`.agents/product-marketing.md`, lu automatiquement par les autres skills
marketing. Résumé en une phrase, pour ne pas avoir à l'ouvrir : **on vend un
service d'installation en personne à des restaurants et brasseries, jamais un
logiciel en libre-service à des petits cafés** — face à Digital Menu (19-49
DT, libre-service), Scanny (+caisse) et Menu-QR (entrée de gamme), aucun des
trois ne se déplace.

## 2. Garde-fous absolus (rappel — voir la mission d'origine pour le détail)

- **Aucun chiffre, témoignage ou verbatim inventé.** `PILOT_RESULTS`
  (`frontend/lib/offer.ts`) reste vide tant qu'aucun relevé réel n'existe.
- **`terrain/*.md` ne se remplit jamais depuis une session** — données de
  terrain saisies à la main par Wassim.
- **La cible ne s'élargit jamais aux petits cafés.**
- **Le prix ne bouge jamais** dans le discours — seulement du temps gratuit
  en échange de références (`PREMIERES_VENTES.md` #6, repris dans
  `PARRAINAGE.md`).
- **Toute dépense publicitaire réelle, création de compte pub, achat de
  domaine ou de visibilité reste 🧑**, à Wassim seul. Ce chantier livre des
  plans prêts à exécuter, jamais l'exécution.
- **Toute modification de code suit le Workflow PR standard** de
  `CLAUDE.md` : branche dédiée, CI verte, jamais de merge sans l'accord
  explicite de Wassim.

## 3. Les trois horizons

Les horizons sont déclenchés par les **jalons réels de `ROADMAP.md`**, pas
par les dates seules — les dates ci-dessous sont celles déjà écrites dans
`ROADMAP.md` (calendrier à rebours de Ramadan) et `PREMIERES_VENTES.md` §2,
pas des dates nouvelles.

### Horizon 0 — maintenant → mise en ligne (Phase 20)

**Dépense : zéro. Objectif : l'arme de vente est prête avant que la porte
d'un restaurant ne s'ouvre.**

| Livrable | Fichier | Statut |
|---|---|---|
| Positionnement, ICP, différenciation | `.agents/product-marketing.md` | Fait (cette session) |
| Argumentaire imprimable | `ARGUMENTAIRE_RESTAURATEUR.md` | Fait (cette session) |
| Canaux professionnels réels | `CANAUX_ACQUISITION.md` | Fait (cette session) |
| Plan de ciblage publicitaire Horizon 1 | `CIBLAGE_PUBLICITAIRE.md` | Fait, **pas activé** |
| Mécanique de parrainage | `PARRAINAGE.md` | Proposition, en attente du premier pilote |
| Pages publiques qualifiantes | Voir § 5 | PR séparée, en attente de revue |

**Canal (ORB) :** uniquement **owned** — le site public existant. Aucun
canal rented/borrowed avant la Phase 21 : rien à annoncer tant que le
produit n'est pas en ligne.

**Sortie d'horizon :** Phase 20 cochée dans `ROADMAP.md` (domaine réel,
sauvegarde restaurée, déclaration INPDP déposée) — critère produit, pas
marketing. Rien ici ne l'accélère.

### Horizon 1 — sept. 2026 → janv. 2027 (Phases 21, 23, 24)

**Le moteur reste le démarchage en personne. Le marketing l'outille, il ne
le remplace jamais par du volume** — piège n°1 de `terrain/PARCOURS.md`.

| Période | Jalon `ROADMAP.md` | Ce que le marketing fait en soutien |
|---|---|---|
| Fin août – septembre | Phase 21 : 20 entretiens | `ARGUMENTAIRE_RESTAURATEUR.md` pour les conversations qui suivent un bon entretien ; `CIBLAGE_PUBLICITAIRE.md` Vague 1 (Tunis + La Marsa) activée en synchronisation avec la tournée à pied, jamais avant ; `CANAUX_ACQUISITION.md` pour compléter la liste de 40 adresses via les canaux professionnels réels identifiés |
| Octobre – novembre | Phase 23 : 3 pilotes, 4 semaines chacun | `CIBLAGE_PUBLICITAIRE.md` Vagues 2 (Sousse) et 3 (Hammamet) ; dès qu'un premier pilote a ses chiffres avant/après sur `/dashboard/preuve`, `PARRAINAGE.md` Étape 2 (référence citable) s'active pour ce pilote |
| Décembre – janvier 2027 | Phase 24 : 2 clients payants | `PARRAINAGE.md` Étape 3 (apporteur) pour les pilotes devenus clients ; premières lignes réelles dans `PILOT_RESULTS` (`frontend/lib/offer.ts`) — **à saisir uniquement avec l'accord écrit du patron et le chiffre réellement mesuré**, en PR de code séparée le moment venu |

**Canal (ORB) :** **owned** (le site, avec `PILOT_RESULTS` qui se remplit
progressivement) + **rented**, mais minuscule et local
(`CIBLAGE_PUBLICITAIRE.md` — Meta uniquement, ~390 DT sur tout l'horizon,
jamais pour attirer du volume, seulement des rendez-vous qualifiés) +
**borrowed**, dès que les associations/salons réels identifiés dans
`CANAUX_ACQUISITION.md` s'y prêtent.

**Sortie d'horizon :** Phase 24 cochée — deux pilotes passés au payant,
première facture encaissée.

### Horizon 2 — Ramadan, février – mars 2027

**La seule vraie campagne publique — et elle ne s'écrit pas avant d'avoir
de quoi la remplir.**

**Condition de déclenchement, stricte :** `PILOT_RESULTS` contient des
chiffres réels et le patron pilote a donné son accord écrit pour les
publier (`PARRAINAGE.md` Étape 2) — sans ça, il n'y a rien à montrer que la
promesse déjà faite et non tenue par tout le monde.

**Ce que cet horizon change par rapport à l'Horizon 1**, une fois la
condition remplie :
- Budget publicitaire plus large que les ~390 DT de test — à chiffrer dans
  un document séparé, écrit **une fois** `PILOT_RESULTS` rempli, jamais
  avant : un budget dimensionné sur des chiffres qui n'existent pas encore
  serait deviné, pas planifié.
- Angle saisonnier déjà écrit dans `PREMIERES_VENTES.md` #7 : « dans trois
  semaines, toutes vos tables commanderont à la même minute — combien de
  commandes perdez-vous ce soir-là ? ». Mode Ramadan et pré-commande iftar,
  déjà construits, argument qu'aucun concurrent tunisien connu n'a à ce
  jour (à revérifier juste avant l'horizon — les positionnements bougent).
- **Canal (ORB) borrowed** devient enfin activable : la presse économique
  tunisienne qui couvre déjà ce secteur (`webmanagercenter.com`,
  `businessnews.com.tn`, sources déjà citées dans
  `REVUE_INVESTISSEURS.md`) est un relais plausible **une fois qu'il y a une
  histoire réelle à raconter** — deux clients payants, des chiffres
  mesurés. Personne à contacter tant que ce n'est pas vrai.
- Le budget grandit, la discipline de ciblage reste la même.

**Ce document ne va pas plus loin ici** : le plan chiffré de l'Horizon 2 est
un chantier à ouvrir en janvier 2027, avec les vrais chiffres en main — pas
une extrapolation écrite aujourd'hui sur des pilotes qui n'existent pas.

## 4. Documents détaillés

| Document | Contenu |
|---|---|
| [`.agents/product-marketing.md`](./.agents/product-marketing.md) | Positionnement, ICP, différenciation, objections, ton de marque |
| [`ARGUMENTAIRE_RESTAURATEUR.md`](./ARGUMENTAIRE_RESTAURATEUR.md) | Argumentaire de vente en personne, une page |
| [`CANAUX_ACQUISITION.md`](./CANAUX_ACQUISITION.md) | Associations CHR, salons B2B, groupes pro, veille concurrentielle — sources citées |
| [`CIBLAGE_PUBLICITAIRE.md`](./CIBLAGE_PUBLICITAIRE.md) | Plan Meta Ads hyper-local Horizon 1, chiffré, prêt à activer |
| [`PARRAINAGE.md`](./PARRAINAGE.md) | Pilote satisfait → référence citable → apporteur |

## 5. Ce qui a touché le code

**Pages publiques (accueil, `/signup`) : qualifier plutôt qu'attirer large.**
L'inscription en self-service ouvre la porte aux petits établissements que
la stratégie exclut — correctifs implémentés dans une **branche et une PR
séparées** de la PR documentaire (`CLAUDE.md`, Workflow PR) :
[PR #105](https://github.com/benmesswass/Tawla/pull/105),
`claude/tawla-homepage-signup-cro`. Détail des trois correctifs dans la
description de cette PR, pour ne pas la dupliquer ici. Ni cette PR ni celle
qui porte ce fichier ne sont à merger sans l'accord explicite de Wassim.

## 6. Ce qui reste 🧑, jamais cette session

Créer les comptes publicitaires et payer, valider tout budget réel, mener
les 20 entretiens et les remplir dans `terrain/`, choisir les 3 pilotes,
signer les accords (pilote et parrainage), décider si/quand l'Horizon 1 ou
2 se déclenche réellement, écrire le budget chiffré réel de l'Horizon 2.
Tout est prêt pour que le jour où Wassim dit « go », il n'y ait plus qu'à
exécuter.
