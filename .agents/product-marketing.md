# Product Marketing Context — Tawla

*Dernière mise à jour : 2026-08-28. Rédigé à partir de `REVUE_INVESTISSEURS.md`
(13 août) et `PREMIERES_VENTES.md` (14 août), déjà tranchés par Wassim — ce
document ne réinvente pas le positionnement, il le rend réutilisable par les
autres skills marketing. Le prix cité est le prix réellement codé aujourd'hui
(Phase 22, PR #63/#91), pas celui — périmé — de `PREMIERES_VENTES.md`.*

## Product Overview

**One-liner :** la commande à table par QR code pour restaurants —
vendue avec quelqu'un qui vient l'installer, jamais en libre-service.

**Ce que ça fait :** le client scanne le QR de sa table, compose son panier et
valide. La commande arrive sur un écran partagé consulté par tous les
serveurs ; un serveur la prend en charge, la confirme à table, puis elle part
en temps réel sur l'écran cuisine. Le manager suit l'activité de la journée
(ventes du jour, temps d'attente moyen, charge par serveur) et les preuves de
service (commandes perdues, panier moyen) sur `/dashboard/preuve`.

**Catégorie (le rayon où on nous cherche) :** logiciel de commande à table
par QR code pour la restauration — même rayon que Digital Menu, Scanny,
Menu-QR. Termes de recherche probables : « menu digital QR code restaurant
Tunisie », « commande à table QR code », « logiciel commande restaurant ».

**Type de produit :** SaaS à haut contact — abonnement logiciel, mais vendu et
livré comme un service d'installation en personne. C'est la case que
personne d'autre sur ce marché ne coche (cf. Différenciation).

**Modèle économique :** abonnement mensuel, trois paliers publics **Essentiel
49 DT / Pro 89 DT / Business 149 DT** (`frontend/lib/offer.ts`,
`core/markets.py::TUNISIA.tier_prices`), gating réel par fonctionnalité,
aucune commission sur les commandes. Paiement carte du loyer entre client et
restaurant hors sujet — l'abonnement Tawla se règle par carte via Konnect une
fois le compte ouvert (Phase 22 🧑), en mode démonstration en attendant. Vendu
en personne pour les 45-90 premiers clients, jamais par volume publicitaire
(cf. `REVUE_INVESTISSEURS.md` tableau stratégie prix).

## Target Audience

**Cible :** restaurants et brasseries, répartis quartier / centre-ville / zone
touristique. **Jamais les petits cafés** : ticket trop faible pour justifier le prix, et
c'est la pente qui transforme une entreprise rentable en travail mal payé
(`PREMIERES_VENTES.md` #10 « Ce qu'il ne faut pas faire »). Le palier
Essentiel existe au catalogue (pour un petit café, une seule salle) mais n'est
**pas** la cible commerciale activement démarchée.

Signal positif le plus fort : **une terrasse**. Tables loin du comptoir =
serveur qui marche le plus = commandes perdues au maximum, et le QR y est
naturellement accepté.

**Décideur :** le patron/gérant — structure assez petite pour qu'il soit à la
fois champion, décideur et payeur. Mais la vente a un second public qui peut
faire échouer l'outil après la signature : le serveur (cf. Personas).

**Job to be done principal :** ne plus perdre une commande pendant le coup de
feu, et voir enfin, sans le demander à personne, ce que le service a
réellement encaissé aujourd'hui.

**Jobs to be done :**
- Empêcher qu'une commande se perde entre la salle et la cuisine pendant le rush
- Voir ses ventes du jour sans attendre la caisse ou le comptable
- Avoir un chiffre objectif (temps d'attente, charge par serveur) pour asseoir une prime, pas une impression

**Scénarios d'usage :** le vendredi soir plein ; la terrasse loin du
comptoir ; l'iftar de Ramadan, où toutes les tables commandent à la même
minute — le seul moment où la démonstration se fait toute seule.

## Personas

Structure TPE : les rôles classiques se recouvrent. Deux personas suffisent,
pas cinq.

| Persona | Cares about | Challenge | Valeur promise |
|---|---|---|---|
| **Patron / gérant** (décideur, payeur, champion) | Ne plus perdre de commandes, voir son chiffre, garder la main sur sa salle | N'a ni le temps ni l'appétence technique pour s'auto-installer un logiciel | Installation, carte saisie, QR imprimés, formation — zéro friction technique de son côté |
| **Serveur** (utilisateur, bloqueur potentiel) | Ne pas être surveillé, ne pas user son forfait/sa batterie personnels, garder son autonomie en salle | Un outil imposé peut être vécu comme une surveillance ou une charge en plus | Il confirme, il ne subit pas : « tu ne prends plus les commandes, tu les confirmes » — et les stats servent une prime, jamais un classement public |

## Problems & Pain Points

**Problème central :** pendant un coup de feu, des commandes se perdent entre
la salle et la cuisine — oubliées, mal transmises à la voix, notées sur un
carnet illisible — et le patron n'a aucune visibilité en temps réel sur ce qui
se passe en salle ni sur ce qu'il a encaissé dans la journée.

**Pourquoi les alternatives ne suffisent pas :**
- Le carnet + la voix : gratuit en apparence, cause exactement la douleur qu'on vend.
- Digital Menu / Scanny / Menu-QR : logiciels **en libre-service** à 19-49 DT — le restaurateur saisit sa carte lui-même, imprime ses QR lui-même, se débrouille seul. Personne à appeler un vendredi soir si ça bloque.
- Embaucher plus de personnel : coûteux, ne corrige pas l'oubli lui-même.

**Ce que ça coûte :** une commande perdue est une vente ratée et un client qui
ne revient pas — et qui le raconte aux autres patrons du quartier. Sans
visibilité sur le chiffre du jour, le tableau de bord (s'il existe) reste une
curiosité qu'on n'ouvre jamais, et un outil qu'on n'ouvre pas est un
abonnement qu'on résilie.

**Tension émotionnelle :** peur de perdre la main sur sa salle (au profit du
client ou du logiciel), méfiance envers une techno qu'il faudrait installer et
apprendre seul, peur que l'équipe de salle sabote l'outil sans jamais dire
pourquoi.

## Competitive Landscape

**Direct :**
- **Digital Menu** — 19 DT (light) / 29 DT (serveur) / 39 DT (commande à table) / 49 DT (premium). Écran cuisine, priorisation, zones, **postes de production** (stations cuisine séparées — Tawla n'a qu'une seule file), fidélité, stats personnel. Modèle libre-service : falls short parce qu'il ne vient jamais sur place.
- **Scanny** — même catégorie, + caisse connectée. Falls short pour la même raison : pas d'accompagnement humain, et l'intégration caisse est un autre chantier que Tawla assume ne pas avoir.
- **Menu-QR** — entrée de gamme, positionnement low-cost. Falls short sur le service, encore plus que les deux précédents.

**Secondaire :** le carnet papier + la mémoire du serveur — la vraie
concurrence dans 100 % des cas avant la première visite commerciale.

**Indirect :** embaucher plus de personnel de salle pour courir plus vite —
coûteux, ne résout pas l'oubli, aggrave la marge.

## Differentiation

**Différenciateurs clés :**
- Installation, carte saisie, QR imprimés livrés, formation sur place et support joignable pendant le service — **aucun des trois concurrents ne le fait**, ils vendent un lien à configurer seul.
- Mode Ramadan + pré-commande iftar, déjà construits — argument saisonnier qu'aucun concurrent tunisien connu n'a construit à ce jour (à vérifier à nouveau juste avant l'Horizon 2, les positionnements bougent).
- Pool partagé + prise en charge nominative : base d'une prime pour le patron, jamais affichée en salle — un vrai parti pris d'organisation, pas juste une fonctionnalité.

**Comment on le fait différemment :** on vient chez le patron avec sa propre
carte déjà chargée, on forme son équipe pendant un service réel, on reste
joignable — au lieu de lui envoyer un lien à paramétrer seul.

**Pourquoi c'est mieux :** ça retire au patron la seule chose qu'il redoute
vraiment (la friction technique), et ça rend la comparaison de prix caduque —
il ne compare plus deux logiciels, il compare un logiciel à un service.

**Pourquoi les clients nous choisissent :** parce qu'ils n'achètent pas un
abonnement SaaS de plus, ils achètent une tranquillité d'esprit pour le
prochain coup de feu.

**Ce que Tawla n'a pas, et l'assume en rendez-vous** (`PREMIERES_VENTES.md`
§1) — à ne jamais cacher, à dire avant qu'on le demande :
- Pas d'intégration caisse — la vraie douleur du patron, mais un autre produit : « pas aujourd'hui, et je ne vous le promets pas ».
- Paiement carte simulé tant que le compte Konnect Tawla n'est pas ouvert.
- Pas de postes de production séparés (une seule file cuisine) — Digital Menu l'a, Tawla non.
- Pas de formules / menus du jour — à construire seulement si les entretiens le font remonter spontanément.
- Addition par commande, pas par table — grince si une table commande en deux temps ; à trancher seulement si plusieurs des vingt entretiens le mentionnent spontanément (`ROADMAP.md` § Sous condition).

## Objections & Anti-Personas

| Objection | Réponse |
|---|---|
| « C'est trop cher, Digital Menu est à 29 DT » | Ne jamais comparer deux logiciels : décrire ce qui est inclus (installation, carte saisie, QR livrés, formation, support) que le concurrent ne fait jamais. Rendre la comparaison de prix impossible plutôt que de la gagner. |
| « Ça va remplacer mes serveurs ? » | Non — le serveur confirme toujours avant que quoi que ce soit parte en cuisine. Ça l'accélère, ça ne le retire pas. |
| « Mon wifi n'est pas terrible » | Disqualifier franchement avant toute démo : sans réseau fiable à toutes les tables, ne pas installer, même si le patron insiste. Le produit fonctionnera mal, et c'est notre faute qu'on retiendra. |

**Anti-persona :** petits cafés de moins de six tables ; établissement sans
wifi/réseau fiable à toutes les tables ; patron qui veut un outil gratuit ou
low-cost sans accepter d'accompagnement ; demande immédiate de multi-
établissements ou d'intégration caisse (hors périmètre tant qu'un client
réel ne l'a pas demandé, cf. `ROADMAP.md` § Sous condition).

## Switching Dynamics (JTBD, quatre forces)

**Push (ce qui pousse à partir du carnet) :** commandes perdues pendant le
rush, aucune visibilité sur le chiffre du jour, allers-retours en cuisine,
carnet illisible en pleine soirée.

**Pull (ce qui attire vers Tawla) :** installation clé en main, formation sur
place, support joignable, mode Ramadan + pré-commande iftar.

**Habit (ce qui retient au statu quo) :** le carnet « marche à peu près »,
l'équipe est rodée dessus, tout changement de routine en salle fait peur
avant le premier service.

**Anxiety (ce qui inquiète dans le changement) :** peur que les serveurs
sabotent ou contournent l'outil ; peur de payer pour quelque chose qui finit
au fond d'un tiroir ; peur de la panne réseau en plein coup de feu (réponse :
le repli papier, à répéter avec l'équipe **avant** d'en avoir besoin).

## Customer Language

**Comment les patrons décrivent le problème :** section volontairement vide
au 2026-08-28 — zéro entretien mené (`terrain/ENTRETIENS.md`). La question
d'ouverture des vingt entretiens (« qu'est-ce qui vous fait perdre de
l'argent chaque semaine ? », `terrain/GUIDE_ENTRETIEN.md`) est posée
exactement pour capter ce langage verbatim. **À densifier après la Phase 21,
jamais en l'inventant d'ici là.**

**Comment ils décrivent Tawla :** idem, inconnu tant qu'aucun entretien n'a
eu lieu.

**Mots à utiliser :** « commande » (jamais « ticket », cf. `CONTEXT.md`),
« service », « salle », « patron »/« gérant » (jamais « utilisateur »),
« on vient », « on installe », « on reste joignable ».

**Mots à éviter en ouverture d'entretien** (orientent la réponse, cf.
`terrain/GUIDE_ENTRETIEN.md`) : « QR code », « digitalisation ». Dans toute
la copie : « utilisateur », « plateforme SaaS », jargon technique.

**Glossaire** (repris de `CONTEXT.md`, qui fait foi) :

| Terme | Sens |
|---|---|
| Commande | Ce qu'un client compose et valide depuis son téléphone. Jamais « ticket ». |
| Prise en charge (Claim) | Un serveur retire une commande du pool partagé pour se l'attribuer. |
| Commande perdue | Une commande **annulée** — définition unique depuis le 2026-08-28. N'inclut plus une commande simplement lente à être prise en charge. |
| Temps d'attente | Délai moyen commande → prise en charge par un serveur. Chiffre de tête secondaire du tableau de bord depuis le 2026-08-28. |
| Ventes du jour | Chiffre de tête **principal** du tableau de bord depuis le 2026-08-28 — commandes réellement réglées aujourd'hui. |
| Charge active | Nombre de tables qu'un serveur a actuellement sur les bras, à l'instant présent. |
| Palier d'abonnement | Essentiel / Pro / Business, chacun incluant les fonctionnalités du précédent. |
| Journée de service | Période de service bornée à une heure fixe (5h du matin), pas minuit calendaire. |

## Brand Voice

**Ton :** direct, sans jargon, un peu fier — tunisien assumé (dérija,
harissa comme couleur de marque), jamais corporate.

**Style :** phrases courtes, concret, toujours du point de vue du patron
(« ce qu'il voit » plutôt que « ce que fait le produit » — cf. la structure
même de `PREMIERES_VENTES.md` §1).

**Personnalité (3-5 adjectifs) :** artisan, présent, honnête (assume ce qui
manque plutôt que de survendre), tunisien, sans chichis.

## Proof Points

**Métriques :** aucune à ce jour. `PILOT_RESULTS` (`frontend/lib/offer.ts`)
est vide **exprès** — zéro pilote, zéro chiffre réel mesuré. Ne jamais en
inventer un, même à titre d'exemple : remplacer par
`[à remplacer par le chiffre réel du premier pilote]` partout où c'est
tentant.

**Clients :** aucun à ce jour.

**Témoignages :** aucun à ce jour.

**Ce qui est démontrable aujourd'hui, faute de chiffres clients :** le
mécanisme lui-même — le produit **mesure** la commande perdue et le temps
d'attente au lieu de les deviner, et le mode Ramadan + pré-commande iftar
existent et fonctionnent déjà, avant même le premier pilote.

## Goals

**Objectif business (celui qui compte, cf. `ROADMAP.md`) :** deux
restaurants qui paient, avant Ramadan 2027 — pas une note de jury, qui suit
sans se piloter directement.

**Action de conversion principale, par horizon :**
- Horizon 0/1 (maintenant → janvier 2027) : obtenir un rendez-vous en personne, puis un accord de pilote signé. **Jamais** un signup en ligne comme objectif premier.
- Horizon 2 (Ramadan, fév.-mars 2027) : signup en ligne qualifié, appuyé sur des chiffres de pilotes réels.

**Métriques actuelles (2026-08-28) :** 0/20 entretiens menés, 0/3 pilotes,
0/2 clients payants, 0 DT de revenu récurrent. C'est l'état réel, pas un
retard à cacher — `REVUE_INVESTISSEURS.md` le nomme déjà : « le facteur
limitant n'est plus la technique ni le marché, c'est l'accès au marché ».
