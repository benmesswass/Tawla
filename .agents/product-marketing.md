# Product Marketing Context

*Last updated: 2026-08-28 — construit à partir de `ETUDE_MARCHE.md`,
`CLAUDE.md`, `ROADMAP.md`, `CONTEXT.md`, `REVUE_INVESTISSEURS.md` et
`PREMIERES_VENTES.md`. À mettre à jour dès que les 20 entretiens (Phase 21)
ou les 3 pilotes (Phase 23) produisent du langage client réel — plusieurs
sections ci-dessous sont volontairement vides en attendant, pour ne jamais
inventer une citation ou un chiffre.*

## Product Overview

**One-liner:** Le service de commande à table par QR code qui vient
s'installer chez vous, pas un logiciel de plus à configurer seul.

**What it does:** Le client scanne le QR de sa table, consulte le menu et
commande depuis son téléphone. La commande apparaît sur un écran partagé
consulté par tous les serveurs ; un serveur la prend en charge, la confirme à
table, puis elle part en temps réel sur l'écran cuisine. Le manager suit
l'activité globale (délai par étape, charge par serveur) et dispose d'une
page de preuve chiffrée (commandes perdues, délai commande → cuisine, panier
moyen).

**Product category:** Commande à table par QR code pour la restauration
(catégorie "menu digital QR" / "commande à table"), adjacente aux solutions
de caisse et de paiement restaurant sans en être une.

**Product type:** SaaS B2B vertical restauration, multi-tenant dès l'origine.

**Business model:** Abonnement mensuel à trois paliers — **Essentiel 49 DT,
Pro 89 DT, Business 149 DT** en Tunisie (décidé le 2026-08-26 ;
`core/markets.py::TUNISIA.tier_prices`), chacun incluant les fonctionnalités
du précédent. Mêmes montants posés en euros pour la France, **hypothèse de
départ non validée et non annoncée publiquement** (Phase F1). Vente
actuellement assistée par le fondateur (installation via
`scripts/setup_restaurant.py`), pas encore un vrai portail self-service à
grande échelle.

## Target Audience

**Target companies:** Restaurants et brasseries tunisiens de **6 tables et
plus**, dans les zones à forte densité et à fort tourisme (Tunis, La Marsa,
Sousse, Hammamet). Explicitement **pas** les petits cafés — ticket trop
faible pour le prix visé. Marché secondaire naissant, non validé sur le
terrain : restaurants et salons de thé en France à clientèle maghrébine.

**Decision-makers:** Le patron/gérant décide et paie, mais l'adoption réelle
dépend du serveur — premier saboteur potentiel de l'outil s'il n'est pas
convaincu avant l'installation.

**Primary use case:** Éliminer les commandes perdues ou oubliées pendant le
coup de feu, et donner au patron une preuve chiffrée de ce qui se passe en
salle, au lieu d'une impression.

**Jobs to be done:**
- Ne plus perdre de commande ni de client pendant un service chargé
- Voir, en chiffres, où l'argent et le temps se perdent (délai commande →
  cuisine, panier moyen, performance par serveur)
- Professionnaliser le service sans remplacer les serveurs ni l'ambiance du
  restaurant

**Use cases:**
- Iftar de Ramadan : toutes les tables commandent à la même minute, la
  pré-commande absorbe le pic
- Terrasse : tables loin du comptoir, commandes les plus souvent perdues, QR
  naturellement accepté dehors
- Fin de mois : rapport par serveur comme base objective de prime

## Personas

| Persona | Cares about | Challenge | Value we promise |
|---|---|---|---|
| Patron/gérant (décideur + payeur) | Chiffre d'affaires, réputation, ne pas perdre un client | Ne voit jamais le vrai coût des commandes perdues, pilote à l'impression | Preuve chiffrée + service installé clé en main |
| Serveur (utilisateur quotidien, saboteur potentiel) | Garder la main sur le service, le pourboire, ne pas user sa batterie/son forfait perso | Craint d'être surveillé, remplacé, ou de subir un outil de plus | Il confirme, il ne saisit plus — plus de tables tenues, rapport jamais affiché en salle |
| Cuisine | Lisibilité des commandes, éviter les allers-retours | Tickets illisibles, ruptures signalées trop tard | Écran temps réel, rupture de stock en un clic |

## Problems & Pain Points

**Core problem:** Une commande oubliée ou perdue pendant le coup de feu — et
aucune preuve, avant Tawla, que ça arrive ni combien ça coûte.

**Why alternatives fall short:**
- Le papier/l'oral/le groupe WhatsApp du resto (le vrai concurrent n°1 par
  volume, cf. `ETUDE_MARCHE.md` §1.5) : aucune preuve, aucune trace, dépend de
  la mémoire du serveur
- Digital Menu / Scanny / Menu-QR (concurrents logiciels tunisiens
  directs) : self-service pur — le restaurateur saisit sa carte et imprime
  ses QR lui-même, sans accompagnement humain sur site à aucun palier
  (vérifié 2026-08-28)

**What it costs them:** Une commande perdue par semaine ≈ le prix de
l'abonnement (panier moyen ~25 DT/commande — hypothèse à remplacer par le
premier chiffre réel relevé en pilote, jamais à citer comme un fait avant
ça).

**Emotional tension:** Le patron sait que ça arrive sans jamais pouvoir le
prouver ni le chiffrer ; peur, à l'inverse, de payer pour un outil que
l'équipe contourne en trois services si le serveur n'a pas été convaincu en
premier.

## Competitive Landscape

**Direct (Tunisie) :** Digital Menu (19/29/39/49 DT selon 4 paliers, écran
cuisine et commande client à partir de 29-39 DT, fidélité + IA + marketing au
palier le plus cher), Scanny (+ module de caisse propriétaire, homologation
fiscale NACEF non confirmée), Menu-QR (entrée de gamme, mais commande client
réelle malgré ce positionnement). Les trois sont des outils self-service :
aucun accompagnement humain sur site trouvé, à aucun palier, chez aucun des
trois (vérifié 2026-08-28, `ETUDE_MARCHE.md` §1-2).

**Secondaire :** Éditeurs de caisse tunisiens (La Caisse, Megasoft, INNOVA
SOFT, ASM) — aucun module de commande client par QR confirmé à ce jour, mais
zone à resurveiller (généralisation de l'homologation NACEF au 1er juillet
2026 force une nouvelle version chez tous). En France, systèmes de caisse
déjà installés partout (L'Addition, Zelty, Lightspeed, Innovorder, Popina,
Tiller/SumUp) : Tawla y entrerait en double-saisie, pas dans un vide.

**Indirect :** Le statu quo — carnet papier, appel du serveur, commande
orale. Concurrent dominant réel par déduction logique (aucun des logiciels
concurrents ne publie de chiffre de clientèle, face à un marché tunisien de
~40 000 à 48 000 cafés/restaurants).

**France (secondaire, non prioritaire) :** Sunday — paiement/checkout QR,
3 000+ restaurants dont ~1 500 en France, levée de 21 M$/18 M€ en novembre
2025, objectif de doubler d'ici l'été 2026 (bilan non publié à ce jour) —
vient avec des équipes commerciales terrain, aucune spécificité communautaire
trouvée. idmenu.fr (25-35 €/mois, concurrent QR direct, moins cher que
l'hypothèse de prix Tawla France).

## Differentiation

**Key differentiators:**
- Accompagnement humain sur site à l'installation (carte saisie pour le
  restaurateur, QR imprimés et livrés, équipe formée en salle, joignable
  pendant le service) — vérifié absent chez les 3 concurrents tunisiens
  directs, à tous les paliers
- Mesure chiffrée avant/après (commandes perdues, délai commande → cuisine,
  panier moyen) — personne d'autre sur le marché tunisien ne l'outille
- Rapport par serveur comme base de prime — le différenciateur le plus fort
  pour la cible 6 tables et plus, réservé au palier Business, absent de tous
  les concurrents vérifiés
- Bilingue fr/ar + mode Ramadan/pré-commande iftar déjà codés — avantage
  saisonnier fort et vérifié en Tunisie ; en France, angle de niche
  (restaurants à clientèle maghrébine) **non encore validé par un entretien
  terrain**, à traiter comme une hypothèse

**How we do it differently:** Le fondateur vient sur place installer, former
l'équipe pendant un service réel, et reste joignable — pas un modèle
self-service pur comme les trois concurrents tunisiens directs.

**Why that's better:** Lève le frein d'installation le plus courant (la
complexité perçue de saisir sa carte et gérer ses QR soi-même) et transforme
un argument de vente (« vous perdez des commandes ») en preuve mesurée
plutôt qu'en promesse.

**Why customers choose us:** Ils n'achètent pas un logiciel de plus, ils
achètent quelqu'un qui vient s'occuper du problème avec eux.

## Objections

| Objection | Response |
|---|---|
| « Digital Menu est moins cher (19-49 DT) » | Vrai en façade seulement au palier Essentiel, où Tawla est à parité — pas en dessous — du palier le plus riche de Digital Menu. À partir de Pro/Business, le prix reflète un service (installation, mesure, rapport par serveur) qu'aucun concurrent ne livre. Ne jamais comparer sans nommer le palier |
| « Ça va remplacer mes serveurs ? » | Non — le serveur confirme, il ne saisit plus ; il garde la main et tient plus de tables en même temps |
| « Et si le Wi-Fi tombe en plein service ? » | Repli papier déjà prévu, à répéter à l'équipe avant l'ouverture, jamais découvert le soir même |

**Anti-persona:** Petits cafés d'une seule salle (ticket trop faible pour
justifier Pro/Business) ; tout établissement sans Wi-Fi ou réseau fiable à
table (à disqualifier à la porte, ne jamais installer même si le patron
insiste).

## Switching Dynamics

**Push:** Commandes perdues répétées, aucune preuve pour en parler à
l'équipe, tickets illisibles en cuisine, aucune visibilité sur qui performe.

**Pull:** Preuve chiffrée + installation clé en main + rien à saisir
soi-même.

**Habit:** Le carnet papier et l'oral fonctionnent « à peu près » — le coût
reste invisible tant que personne ne le mesure.

**Anxiety:** Le serveur va-t-il saboter l'outil (batterie, forfait perso,
sentiment de surveillance) ? Le Wi-Fi va-t-il tenir un vendredi soir plein ?

## Customer Language

**How they describe the problem:** *(vide — à recueillir aux 20 entretiens de
la Phase 21, ne jamais inventer une citation en attendant)*

**How they describe us:** *(vide — idem, à recueillir en pilote, Phase 23)*

**Words to use:** commande perdue, preuve, service inclus, installé pour
vous, accompagnement, joignable pendant le service.

**Words to avoid:** « logiciel » ou « application » en position centrale
(préférer « service ») ; « révolutionnaire », « disruptif », tout
superlatif non prouvé ; jamais un chiffre ou témoignage pilote inventé
(`PILOT_RESULTS` reste vide tant qu'aucun chiffre réel n'existe).

**Glossary:**

| Term | Meaning |
|---|---|
| Commande perdue | Une commande annulée — définition unique (`stats/service.py::cancelled_orders`) |
| Palier (Essentiel/Pro/Business) | Niveau d'abonnement, chacun incluant les fonctionnalités du précédent |
| Prise en charge (claim) | L'action par laquelle un serveur retire une commande du pool partagé pour se l'attribuer |
| Marché (tn/fr) | Configuration pays unique — devise, fuseau, prix des paliers, TVA, fournisseur de paiement |

## Brand Voice

**Tone:** Direct, factuel, jamais survendu — cohérent avec la règle interne
« ne jamais inventer un chiffre pilote ou un témoignage ».

**Style:** Concret, orienté preuve et bénéfice patron plutôt que
fonctionnalité technique. Le prix ne bouge jamais une fois annoncé ; le
périmètre, oui.

**Personality:** Rigoureux, artisanal, présent sur le terrain, honnête sur
ses limites (« pas d'intégration caisse aujourd'hui, et je ne vous le
promets pas »).

## Proof Points

**Metrics:** Aucune donnée pilote réelle à ce jour — `PILOT_RESULTS`
(`frontend/lib/offer.ts`) est vide volontairement. La Phase 23 doit le
remplir avec des chiffres relevés chez un établissement ayant donné son
accord écrit pour être cité.

**Customers:** Aucun client payant à ce jour. Objectif : deux avant Ramadan
2027 (`ROADMAP.md`).

**Testimonials:** Aucun — ne jamais en inventer, sous aucun prétexte.

**Value themes:**

| Theme | Proof |
|---|---|
| Zéro commande perdue | Mesuré et affiché sur `/dashboard/preuve` (définition unique) — pas encore de chiffre pilote réel |
| Service, pas logiciel | Aucun des 3 concurrents tunisiens vérifiés n'offre d'installation humaine sur site, à aucun palier (`ETUDE_MARCHE.md`, 2026-08-28) |
| Rapport par serveur | Fonctionnalité absente de tous les concurrents tunisiens vérifiés ; réservée au palier Business côté Tawla |

## Goals

**Business goal:** Deux restaurants qui paient réellement l'abonnement, avant
Ramadan 2027 (`ROADMAP.md`).

**Conversion action:** Un rendez-vous terrain qui débouche sur un pilote
gratuit de 4 semaines, avec accord écrit (droit de citer le nom, droit de
publier les chiffres mesurés).

**Current metrics:** 0 client payant, 0 pilote actif au 2026-08-28 ; 20
entretiens (Phase 21) et 3 pilotes (Phase 23) à venir.

---

## Positionnement (issu de `ETUDE_MARCHE.md`, 2026-08-28)

**Énoncé canonique — Tunisie, cible prioritaire (restaurants 6 tables et
plus) :**

> Pour les restaurants et brasseries tunisiens de 6 tables et plus (Tunis, La
> Marsa, Sousse, Hammamet), qui perdent des commandes — et de l'argent — à
> chaque coup de feu sans jamais pouvoir le prouver, Tawla est le service de
> commande par QR code livré avec un accompagnement humain sur place — carte
> saisie pour vous, QR imprimés et livrés, équipe formée sur place, joignable
> pendant le service — qui élimine les commandes oubliées et transforme
> chaque service en chiffres. Contrairement à Digital Menu, Scanny et Menu-QR
> — trois outils en libre-service où le restaurateur saisit sa carte, imprime
> ses QR et se débrouille seul — Tawla ne vend pas un logiciel, elle vend
> quelqu'un qui vient, forme l'équipe pendant un service réel, et reste
> joignable un vendredi soir.

Ne tient, prix à l'appui, que pour les paliers **Pro** et **Business** —
jamais Essentiel, dont le seul argument défendable est le service inclus, pas
l'écart de prix (`ETUDE_MARCHE.md` §2.1, §7).

**Variante courte — niche France (secondaire, hypothèse non validée sur le
terrain) :**

> Pour les restaurants et salons de thé en France à clientèle maghrébine, qui
> ne trouvent dans aucune solution installée une expérience pensée pour leur
> carte et leur calendrier, Tawla est la commande à table par QR déjà
> bilingue français/arabe, avec mode Ramadan et pré-commande iftar —
> contrairement à Sunday, qui arrive en force commerciale mais sans
> spécificité communautaire.

À qualifier systématiquement tant que la Phase F1 n'a pas eu lieu : ni
boulevard vide, ni segment déjà perdu — deux acteurs adjacents (Temtem One en
livraison, Hal'Rezo en réservation/fidélité) montrent que le public est déjà
identifié par d'autres, sans qu'aucun n'ait construit la commande à table
elle-même.
