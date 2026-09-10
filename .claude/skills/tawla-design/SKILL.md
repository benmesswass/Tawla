---
name: tawla-design
description: Règles de design visuel du frontend Tawla — à charger avant toute modification de l'apparence ou des interactions dans frontend/ (composants, pages, globals.css, tailwind.config.js) : couleur, typographie, espacement, rayons, élévation, états de composant, mouvement, contraste. Complète la skill officielle frontend-design, qui suppose une identité à inventer alors que celle de Tawla est déjà décidée.
---

# Design du frontend Tawla

La skill officielle `frontend-design` demande de choisir une palette, des
polices et une direction artistique propres au brief. **Ce n'est pas le travail
ici.** Tawla a une identité arrêtée, cohérente, et qui tient : son problème
n'est pas la charte, c'est que trois axes du système n'ont jamais été définis et
que rien ne bouge quand l'état change.

Garder de `frontend-design` : la discipline anti-template, la retenue (« retirer
un accessoire avant de sortir »), le plancher de qualité (responsive, focus
clavier visible, `prefers-reduced-motion`), l'exigence sur la copie. Ignorer :
l'étape « invente une palette et un couple de polices ».

## Ce qui est déjà décidé — ne pas rouvrir

| Axe | Où | Règle |
|---|---|---|
| Couleur | `frontend/app/globals.css` (13 jetons) + `tailwind.config.js` | Aucune couleur nouvelle. `semoule`/`semoule-raised` fonds, `espresso`/`encre` encre, et **trois accents seulement** : `harissa` (action), `menthe` (validé, sans urgence), `laiton` (attente, encaissement, fidélité) |
| Polices | `frontend/lib/fonts.ts` | Lalezar en affichage (nom du restaurant, total), Hanken Grotesk en texte, Cairo pour le texte arabe. Lalezar reste la police d'affichage même en arabe |
| Écran sombre | dérivés `*-on-espresso` de `globals.css` | La cuisine et les tickets ont déjà leur palette. Ne pas en inventer une seconde |

**La règle la plus violée** — elle est écrite dans le commentaire de
`components/ui/Button.tsx` mais pas appliquée : *un seul harissa cliquable par
zone de décision*. Un prix de plat n'est pas une action ; il passe en espresso,
le bouton garde le rouge.

## Les axes du système — utiliser les jetons, jamais une valeur en dur

Relevé au 2026-09-09, avant les jetons : 25 tailles de texte distinctes en dur
(de 9 à 28 px, par pas de 0,5) sur 198 occurrences, 9 rayons dont 6
arbitraires, 7 traitements d'ombre mêlant défauts Tailwind et valeurs à la
main. Les jetons ci-dessous existent depuis le 2026-09-10 : **une valeur en dur
est désormais un bug**, exactement comme une couleur en dur.

Les usages antérieurs ne sont pas réécrits d'un coup — ils migrent quand la
page qui les porte est reprise. Du code neuf, lui, n'a aucune raison d'y
échapper.

- **Typographie** (`fontSize` de `tailwind.config.js`) — `text-affiche-xl`
  (34/1.05), `text-affiche` (28/1.05), `text-titre` (19/1.25), `text-corps`
  (15/1.5), `text-etiquette` (13/1.35), `text-legende` (12/1.4),
  `text-surtitre` (11 · .14em, majuscules). Sept tailles : ce qui sépare le
  texte courant du texte appuyé est la **graisse**, pas la taille.
- **Espacement** — aucun jeton nouveau, et c'est volontaire : l'échelle par
  défaut de Tailwind est déjà en base 4 (`gap-1` = 4 px … `gap-12` = 48 px).
  Le travail n'est pas d'ajouter une échelle, c'est de **retirer** les
  `gap-[7px]` / `pt-[10px]` / `py-[11px]` qui la contournent.
- **Rayons** (`borderRadius`) — `rounded-champ` (6), `rounded-controle` (10),
  `rounded-carte` (14), `rounded-feuille` (20), `rounded-full` (pilule).
  Nommés par rôle et non par taille : « une carte de plat est-elle en `md` ou
  en `lg` ? » est une question sans réponse, et c'est de là que vient la
  dérive.
- **Élévation** (`boxShadow`) — `shadow-pose` (séparateur), `shadow-carte`
  (plat, ticket), `shadow-barre` (barre de panier — elle porte vers le **haut**),
  `shadow-couche` (feuille, modale). Chaque niveau dit une distance à la page.
  Une carte de plat ne porte jamais l'ombre d'une modale : c'est exactement ce
  que produisent les `shadow-lg`/`shadow-xl` posés au cas par cas.
- **Mouvement** (`transitionDuration` / `transitionTimingFunction`) —
  `duration-micro|rapide|normal|lent|sortie` et
  `ease-entree|sortie|deplacement`. Côté JS, `lib/mouvement.ts`.

## Mouvement

Lire **`MOTION_DESIGN.md`** à la racine ([PR #187](https://github.com/benmesswass/Tawla/pull/187)) avant d'animer quoi que ce soit. En résumé :

- Le budget d'animation est **inversé** : ~22 usages sur la décoration
  (confettis, `celebration-pop`, `cart-bump`, pulsations permanentes) et 0 sur
  ce qui change d'état. **Animer le changement d'état, pas la décoration.**
- Quatre durées (`--motion-micro` 120 / `fast` 180 / `normal` 280 / `slow` 400)
  et trois courbes (`--ease-enter` / `--ease-exit` / `--ease-move`), chacune
  avec un rôle exclusif. Toute sortie est plus courte que son entrée (200 ms).
- Pas de ressort en CSS. Le rebond n'appartient qu'à ce que le doigt tient : le
  glisser d'une table sur le plan de salle, le carrousel de la home.
- La table « ce qu'on n'animera pas » de `MOTION_DESIGN.md` est une décision
  prise, pas une suggestion : pas d'apparition en cascade dans les modales, pas
  de translation plein écran sur la vitrine, pas de pulsation permanente, pas
  d'animation de survol pensée pour le mobile.

## États de composant

Un composant interactif se livre avec **tous** ses états : `default`, `hover`
(souris seulement), `pressed`, `focus-visible`, `loading`, `success` si
l'action le justifie, `disabled`. Aujourd'hui seul `ui/Button` variante
`primary` a un état pressé, et le frontend compte **123 `<button>` écrits à la
main** contre 16 fichiers qui importent `ui/Button`. Passer par `ui/Button`,
`ui/Card`, `ui/Badge` plutôt que réécrire ; si le composant partagé ne suffit
pas, l'étendre là-bas.

L'état pressé porte sur **la cible entière**, jamais sur son seul texte, et se
perçoit comme instantané (`--motion-micro`).

## Plancher d'accessibilité

Deux défauts mesurés le 2026-09-09, à corriger avec les jetons et **pas plus
tard** — ce sont des défauts produit, donc exempts du verrou « nomme le
restaurateur » de `CLAUDE.md` :

| Couple | Mesuré | Correctif |
|---|---|---|
| `--semoule` sur `--harissa` | 3,97:1 | `#fff` sur harissa = 4,55 ; ou `--harissa-dark` = 5,17 |
| `--ink-faint` sur `--semoule` | 3,78:1 (4,34 sur blanc) | `#786250` = 5,00 sur semoule, 5,74 sur blanc |

Seuil AA pour du texte courant : 4,5:1. Vérifier tout nouveau couple, ne pas
l'estimer à l'œil.

Le reste du plancher : un `:focus-visible` visible sur chaque cible cliquable
(il n'y en a que 6 dans tout le frontend, tous dans le CSS du plan de salle) ;
`prefers-reduced-motion: reduce` étendu à chaque nouvelle animation, ce qui veut
dire **l'état final immédiatement**, jamais « pas d'état final » — une modale
sans animation d'entrée s'ouvre quand même.

## Dépendances d'UI

- **Pas de shadcn/ui, ni aucune librairie de composants.** Le frontend est du
  Tailwind nu sur variables CSS, avec `components/ui/*` écrits à la main. Une
  librairie apporterait sa propre charte à recouvrir et son propre système de
  jetons à concilier — pour remplacer 5 composants de 8 à 50 lignes.
- **Motion est installé** (paquet `motion`, v13). Décision de Wassim le
  2026-09-10, qui revient sur le « pas de librairie d'animation par défaut »
  écrit ici la veille. Le coût était réel, il est traité plutôt qu'accepté :
  `components/ui/Mouvement.tsx` charge le moteur **en différé**
  (`LazyMotion features={() => import(…)}`) et refuse le paquet complet
  (`strict`), de sorte que le HTML de la carte arrive sans lui.
  - Importer les éléments depuis **`motion/react-m`** (`import * as m from
    "motion/react-m"` — en v13 ce sous-chemin exporte `div`, `button`… et non
    un objet `m`), jamais `motion.*` : `strict` fait échouer le rendu, exprès.
  - `LazyMotion`, `AnimatePresence`, `MotionConfig`, `useReducedMotion`
    viennent de `motion/react`.
  - Le socle charge `domAnimation` (animation, survol/pression,
    `AnimatePresence`). Le glisser et les animations de layout sont dans
    `domMax` : à charger localement là où ils servent (plan de salle,
    carrousel), pas pour tout le monde.
  - Durées, courbes et ressorts viennent de **`lib/mouvement.ts`**, jamais
    d'un littéral. Le fichier est le miroir JS des variables CSS : modifier
    l'un sans l'autre désaccorde une animation CSS et une animation Motion sur
    le même geste.
  - Ce qu'un `:hover`/`:active` CSS fait déjà, il continue de le faire. Motion
    sert à ce que CSS ne sait pas faire : sortie d'un élément démonté,
    animation de layout, transition d'élément partagé, geste.

Rouvrir le premier point est une décision de Wassim, pas un choix
d'implémentation.

## Une page à la fois, et une critique après chaque page

Règle posée par Wassim le 2026-09-10. **Jamais « refais tout le frontend »** :
un seul écran par PR, dans cet ordre — socle (fait), vue carte du menu client,
panier + envoi, suivi + paiement, `/staff`, `/kitchen`, `/dashboard` et ses
sous-pages, `/login` + `/signup`, vitrine. La vitrine passe en dernier : elle a
déjà été travaillée par les phases D2 et D2bis.

Une page n'est finie qu'après ces deux passes, dans l'ordre :

1. **Cohérence avec le système.** Relire la zone reprise et remplacer ce qui
   contourne les jetons (`text-[12.5px]`, `rounded-[10px]`, `gap-[7px]`, un
   accent posé en texte). Le périmètre de la passe est la zone redessinée, pas
   le fichier entier — sinon le diff devient illisible.
2. **Critique de product designer senior.** Arrêter de raisonner en
   développeur et regarder l'écran comme s'il était présenté pour la première
   fois. Passer en revue : ce qui paraît cheap, générique ou « généré par IA » ;
   la hiérarchie ; les espacements incohérents ; ce qui est trop lourd ou trop
   faible ; les interactions manquantes ; les animations à ajouter **et celles
   à retirer** ; le mobile ; l'accessibilité ; et les endroits où
   l'utilisateur peut hésiter.

   Classer en **P0** (doit être corrigé), **P1** (amélioration importante),
   **P2** (polish). **Implémenter P0 et P1 seulement**, et laisser les P2
   écrits dans la PR. Pas de liste de cinquante points : si tout est P0, rien
   ne l'est.

Les défauts trouvés par cette critique se corrigent **dans la même PR** que la
page — une critique dont les P0 partent dans un ticket séparé ne sert à rien.

## Gouvernance

`ROADMAP_DESIGN.md` décide **quoi** montrer au client, `MOTION_DESIGN.md`
**comment** ça bouge, cette skill **avec quelles valeurs**. Aucun des trois ne
réordonne `ROADMAP.md`. Et le verrou de `CLAUDE.md` s'applique : une
*fonctionnalité* visuelle nouvelle doit nommer le restaurateur qui la demande ;
un *défaut* (« le produit fait faux ») en est exempt. La frontière compte.
