# Mécanique de parrainage — d'un pilote satisfait à un apporteur

*Rédigé le 2026-08-28. Proposition, pas une décision : aucun pilote réel
n'existe (`terrain/PILOTES.md` est un modèle vide), donc rien ici ne
s'applique avant que la Phase 23 en produise un premier. À valider par
Wassim avant d'être proposé à un vrai patron — en particulier le § 3
(récompense), qui touche un engagement financier ou de temps réel.*

## Pourquoi ça compte plus que pour un logiciel ordinaire

`PREMIERES_VENTES.md` #2 le dit déjà : « les patrons se connaissent, se
parlent, et se recommandent entre eux plus efficacement que n'importe quelle
démarche commerciale ». Ce document ne fait que donner une forme répétable à
ce que la stratégie de vente en personne suppose déjà — il ne change rien à
la doctrine du prix ni à la cible.

**Règle qui traverse tout le document, sans exception** : la contrepartie
d'un parrainage est **du temps, du statut ou de la visibilité — jamais une
remise**. `PREMIERES_VENTES.md` #6 : « le prix ne bouge jamais, le périmètre
oui ». Une ristourne de parrainage tuerait le positionnement aussi sûrement
qu'une remise de négociation.

## Les trois étapes

### Étape 1 — Pilote (déjà entièrement spécifiée, rien à ajouter ici)

L'accord écrit d'une page de la Phase 23.1 (`ROADMAP.md`,
`terrain/PARCOURS.md` Étape 4) couvre déjà : quatre semaines d'usage
effectif, droit de citer le nom, droit de publier les chiffres mesurés, en
échange de l'installation, la formation, les chevalets et le support. **Ce
document ne modifie pas cet accord** — il commence après.

### Étape 2 — Référence citable

**Déclencheur :** les quatre semaines sont passées, les métriques
avant/après existent sur `/dashboard/preuve` (Phase 23.2-23.4), et le patron
dit oui quand on lui montre le chiffre.

**Ce que ça débloque, déjà prévu ailleurs, listé ici pour mémoire :**
- Une ligne dans `PILOT_RESULTS` (`frontend/lib/offer.ts`) — nom de
  l'établissement, métrique, valeur mesurée.
- Sa phrase, dans ses mots, pour répondre à « pourquoi toi et pas Digital
  Menu à 39 DT » (Phase 23.4).

**Ce que ce document ajoute — le demander explicitement, pas le supposer :**
au moment où le patron dit oui au chiffre, poser la question de l'étape 3
tout de suite, dans la même conversation. C'est le moment où il est le plus
convaincu qu'il ne le sera jamais.

### Étape 3 — Apporteur

**Déclencheur :** la référence est citable (étape 2) ET le patron a
explicitement accepté d'introduire Tawla à d'autres restaurateurs — un
« oui, je peux vous citer » ne vaut pas un « oui, je vais vous
recommander ». Les deux se demandent séparément.

**Ce qu'on lui demande, par ordre de facilité croissante pour lui :**

1. **L'introduction chaude** — deux ou trois noms de patrons qu'il connaît,
   avec l'autorisation de dire « c'est [son nom] qui m'envoie ». Le
   mécanisme le plus fort et le moins coûteux pour lui : il ne fait rien de
   plus qu'une phrase.
2. **La vitrine vivante** — proposer d'amener un prospect voir l'outil
   tourner chez lui, pendant un service réel, avec de vrais clients.
   Contrepartie naturelle pour lui : du passage supplémentaire un soir
   creux, pas seulement un service rendu à Tawla. À caler avec lui à
   l'avance, jamais improvisé sur place.
3. **Le témoignage réutilisable** — une citation courte ou une photo,
   au-delà du chiffre déjà couvert par l'accord pilote, pour l'Horizon 2
   (Ramadan). Seulement si l'accord initial ou un accord complémentaire le
   couvre explicitement — ne jamais réutiliser au-delà de ce qui a été
   signé.

**Récompense — à choisir par Wassim, jamais une remise :**

| Option | Ce que ça coûte à Wassim | Ce que ça vaut pour le patron |
|---|---|---|
| Statut « établissement fondateur » — mention permanente comme premier pilote, sur la page publique | Rien de monétaire | Reconnaissance, valorisable auprès de ses propres clients |
| Un mois du palier supérieur offert par introduction convertie en client payant | Un mois de palier, pas un rabais permanent | Concret, temporaire, ne touche jamais le prix affiché |
| Accès en premier aux nouvelles fonctionnalités (ex. futures fonctionnalités France si pertinent, nouveauté Ramadan) | Temps de coordination | Se sent traité comme un partenaire, pas un numéro de compte |

Choisir **une** option avant de la proposer à un vrai pilote, l'écrire, s'y
tenir pour tous les pilotes suivants de la même façon — l'incohérence entre
deux patrons qui se parlent coûterait plus cher que l'avantage lui-même.

## Ce que ce document ne fait pas

- Il n'invente aucun chiffre, aucun nom, aucun témoignage — tout reste
  vide tant qu'un vrai pilote n'existe pas.
- Il ne touche pas à l'accord écrit de la Phase 23.1, il s'ajoute après.
- Il ne fixe pas la récompense finale — seulement les options, à trancher
  par Wassim avant la première conversation où la question se posera pour
  de vrai.
- Le suivi réel (qui a été demandé, qui a dit oui) se consigne dans
  `terrain/PILOTES.md` comme le reste du suivi pilote — pas ici, et jamais
  depuis une session.
