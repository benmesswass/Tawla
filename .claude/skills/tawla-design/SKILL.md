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

## Les axes qui manquent — les compléter, pas improviser

Relevé au 2026-09-09 : 25 tailles de texte distinctes en dur (de 9 à 28 px, par
pas de 0,5) sur 198 occurrences, 9 rayons dont 6 arbitraires, 7 traitements
d'ombre mêlant défauts Tailwind et valeurs à la main. Une nouvelle valeur en dur
aggrave le problème.

- **Typographie** — 8 rôles : `display-xl` (Lalezar 34/1.05), `display-l`
  (Lalezar 28/1.05), `title` (700 · 19/1.25), `body-strong` (600 · 15/1.5),
  `body` (400 · 15/1.5), `label` (600 · 13/1.35), `caption` (500 · 12/1.4),
  `overline` (600 · 11 · .14em majuscules). Les paliers à 0,5 px d'écart ne se
  distinguent pas à l'œil, seulement dans le diff.
- **Espacement** — base 4 : 4 / 8 / 12 / 16 / 24 / 32 / 48.
- **Rayons** — 6 (champ), 10 (bouton), 14 (carte), 20 (feuille, coins hauts),
  `999px` (pilule).
- **Élévation** — 4 niveaux qui disent la distance à la page : posé
  (séparateur), carte (plat, ticket), collé (barre de panier), couche (feuille,
  modale). Une carte de plat ne porte jamais l'ombre d'une modale — c'est ce
  que produisent les `shadow-lg`/`shadow-xl` posés au cas par cas.

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

## Ne pas ajouter de dépendance d'UI

- **Pas de shadcn/ui, ni aucune librairie de composants.** Le frontend est du
  Tailwind nu sur variables CSS, avec `components/ui/*` écrits à la main. Une
  librairie apporterait sa propre charte à recouvrir et son propre système de
  jetons à concilier — pour remplacer 5 composants de 8 à 50 lignes.
- **Pas de Motion / framer-motion par défaut** (~35 ko compressés sur la page
  qu'un client charge sur le réseau du restaurant, avec le téléphone qu'il a).
  Les sept principes de `MOTION_DESIGN.md` sont tous faisables en CSS. Motion ne
  se justifierait que pour l'animation de sortie d'un élément retiré d'une liste
  ou une transition d'élément partagé — deux besoins que le menu n'a pas.

Si l'un de ces deux points doit être rouvert, c'est une décision de Wassim, pas
un choix d'implémentation.

## Gouvernance

`ROADMAP_DESIGN.md` décide **quoi** montrer au client, `MOTION_DESIGN.md`
**comment** ça bouge, cette skill **avec quelles valeurs**. Aucun des trois ne
réordonne `ROADMAP.md`. Et le verrou de `CLAUDE.md` s'applique : une
*fonctionnalité* visuelle nouvelle doit nommer le restaurateur qui la demande ;
un *défaut* (« le produit fait faux ») en est exempt. La frontière compte.
