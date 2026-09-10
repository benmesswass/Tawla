# Tawla — Principes de motion design

Né le **2026-09-09** d'une lecture image par image d'une capture d'écran de
**Tricount (bunq)** fournie par Wassim (40 s, 60 i/s, iPhone). La vidéo sert
de référence **d'interaction et de motion uniquement** : ni sa charte, ni son
thème sombre, ni ses libellés, ni ses écrans ne sont repris. Les durées et
courbes ci-dessous sont mesurées sur cette capture, pas estimées.

**Ce fichier ne remplace pas [`ROADMAP_DESIGN.md`](./ROADMAP_DESIGN.md).**
ROADMAP_DESIGN.md décide *quoi* montrer au client (la photo, la bannière, la
barre de catégories). Ce fichier décide *comment* l'interface bouge quand on
s'en sert. Les deux se lisent avant de toucher au parcours client.

## Constat qui fonde ce fichier

Le budget d'animation de Tawla est **inversé**. Relevé sur
`frontend/app/**` + `frontend/components/**` au 2026-09-09 :

| Ce qui est animé aujourd'hui | Occurrences |
|---|---|
| `animate-celebration-pop` / `-fade` (fin de commande) | 8 |
| `animate-confetti` | 3 |
| `animate-cart-bump` | 3 |
| `animate-tw-pulse` / `-v` / `pulse-ring` / `plan-respire` | 8 |

| Ce qui n'est pas animé du tout | État |
|---|---|
| Ouverture / fermeture des modales et feuilles (`fixed inset-0`, 4 occurrences) | apparition sèche |
| Passage d'une page à l'autre | aucun |
| Ligne de plat qui s'agrandit à l'ajout au panier (quantité + note + « à partager ») | saut de ~250 px |
| Barre de panier qui apparaît en bas | apparition sèche |
| Total qui change | remplacement sec |
| Pastille de catégorie active | `transition-colors` seul, pas de glissement |
| État pressé d'un bouton | `transition-colors`, sauf `active:translate-y` du bouton primaire |

Autrement dit : Tawla anime **la décoration** (confettis, pulsations
d'attente) et **rien de ce qui change d'état**. La référence fait exactement
l'inverse — elle n'a **aucune** animation décorative, pas même sur son écran
de succès, et anime **chaque** changement d'état. C'est là qu'est l'écart de
finition, pas dans le nombre d'animations.

Corollaire, et c'est contre-intuitif : appliquer ce fichier va **retirer** de
l'animation à Tawla (les confettis, les pulsations permanentes) autant qu'en
ajouter.

## Jetons de mouvement

À ajouter dans `frontend/app/globals.css` à côté des jetons de couleur, et à
exposer dans `tailwind.config.js` (`transitionDuration`, `transitionTimingFunction`)
pour être utilisables en classes.

```css
/* Durées — quatre, pas plus. Une valeur en dur dans un composant est un bug. */
--motion-micro:  120ms; /* retour au doigt : pression, survol, couleur */
--motion-fast:   180ms; /* petit déplacement dans l'écran : pastille, bascule */
--motion-normal: 280ms; /* arrivée d'une couche : feuille, modale, page, reflux */
--motion-slow:   400ms; /* réservé à la couverture du menu, une fois par visite */

/* Sorties : toujours plus courtes que les entrées. On attend pour voir
   arriver, jamais pour voir partir. */
--motion-exit:   200ms;

/* Courbes. Trois, chacune avec un rôle exclusif. */
--ease-enter: cubic-bezier(.32, .72, 0, 1);  /* ce qui arrive : départ franc, arrivée posée */
--ease-exit:  cubic-bezier(.4, 0, 1, 1);     /* ce qui part : accélère et disparaît */
--ease-move:  cubic-bezier(.4, 0, .2, 1);    /* ce qui se déplace sans arriver ni partir */
```

Pas de ressort (`spring`) : CSS n'en a pas, et la librairie qui en fournissait
a été retirée (voir ci-dessous). Le rebond reste de toute façon réservé à ce
que le doigt tient physiquement — le glisser d'une table sur le plan de salle,
le carrousel de la home, tous deux écrits à la main. Partout ailleurs il
ajoute du délai sans ajouter d'information.

## Motion : essayé, mesuré, retiré (2026-09-10)

Motion (paquet `motion`, v13) a été adopté le 2026-09-10 sur décision de
Wassim, puis **retiré le même jour** après mesure. Le raisonnement est
consigné ici pour qu'on ne le rejoue pas.

**Ce qui a été mesuré** sur la route du menu client (`next build`, puis gzip
des morceaux listés par `app-build-manifest.json`) :

| | Premier chargement | Moteur | Total par ouverture |
|---|---|---|---|
| Avec Motion | 166,7 kB gz | + 49,5 kB gz | **216,2 kB** |
| Sans Motion | 147,7 kB gz | — | **147,7 kB** |

Soit **+68 kB gzip par ouverture, +46 % de JS**, sur la seule page qu'un
inconnu charge sur un réseau qu'on ne choisit pas.

**Pourquoi le différé ne sauvait rien.** `LazyMotion` appelle son chargeur au
**montage**, pas à la première animation : le morceau du moteur partait à
131 ms, juste après `loadEventEnd`, à chaque ouverture, que le convive anime
quelque chose ou non. Et le repousser plus loin est impossible : un composant
`m.*` privé de son moteur applique son `initial` en style inline et n'anime
jamais. Vérifié sur un build où le moteur n'arrivait pas — le panneau du plat
restait à `height: 0; opacity: 0` et la barre de panier hors écran
(`y = 1114` dans une fenêtre de 1100 px). Le convive ajoute un plat et ne voit
rien. Ce n'est pas une optimisation, c'est un défaut.

**Ce qu'on a gardé, en CSS** (voir le bloc « Carte client » de
`frontend/app/globals.css`) : les quatre mouvements d'état de la carte, avec
deux renoncements assumés — les *sorties* de la ligne dépliée et du pas de
quantité ne sont pas animées (CSS ne peut pas animer un nœud que React a
retiré), et le total entre en fondu au lieu de se croiser avec l'ancienne
valeur.

**À quelle condition Motion revient.** Un besoin que CSS ne sait pas couvrir
*et* sur une route qui n'est pas le menu client : une transition d'élément
partagé, une animation de layout, un glisser au doigt — donc plutôt le plan de
salle ou le tableau de bord, chargés une fois par service sur les appareils du
restaurant. Le remettre est `npm i motion` plus une quinzaine de lignes de
provider ; ce n'est pas ce coût-là qui doit peser dans la décision, c'est les
68 kB sur le téléphone du convive.

## Ce que CSS garde, et ce qui justifierait autre chose

- **CSS garde tout ce qu'il sait faire** : survol, état pressé, changement de
  couleur, apparition d'un élément qui reste monté, transition de hauteur via
  `grid-template-rows: 0fr → 1fr`. Un retour au doigt passé par JS arrive
  toujours plus tard qu'un `:active`.
- **Ce que CSS ne sait pas faire** : la sortie d'un élément qu'on démonte,
  l'animation de layout, la transition d'élément partagé, le geste. Quand un
  de ces besoins se présente, la question se repose — avec les chiffres
  ci-dessus sous les yeux.

Un détail de vérification, pour la prochaine fois : **le panneau navigateur de
la session gèle les horloges d'animation** (`document.visibilityState` vaut
`hidden`, `document.timeline.currentTime` reste à 0). Une animation y paraît
bloquée à son état de départ. Pour la contrôler malgré ça, forcer la tête de
lecture (`element.getAnimations()[0].currentTime = 280`) et lire le style
calculé, ou neutraliser la transition et lire la valeur cible.

## Les sept principes

Chaque principe : ce que fait la référence (mesuré), pourquoi, ce que ça donne
chez Tawla.

### 1. Une couche qui arrive fait reculer celle du dessous

Référence : à l'ouverture d'une feuille, la liste derrière passe à
`scale(.93)`, ses coins s'arrondissent, elle s'assombrit — pendant que la
feuille monte de `translateY(100%)` à `0`. Les deux mouvements durent le même
temps (~320 ms) et partagent la même courbe. Mesuré : ~10 images à 30 i/s
pour l'essentiel du trajet, puis ~5 images de dépôt, sans rebond.

Pourquoi : le recul dit « ta page est toujours là, derrière ». Sans lui, une
feuille est un écran de remplacement et on ne sait plus par où revenir.

Tawla : les 4 modales du parcours client (`role="dialog"`, déjà en
`items-end sm:items-center` — donc déjà feuille sur téléphone, boîte centrée
sur écran large). Le recul s'applique au conteneur de page, pas au `<body>`.
`--motion-normal` + `--ease-enter` à l'ouverture, `--motion-exit` +
`--ease-exit` à la fermeture.

### 2. Le contenu de la couche arrive d'un bloc

Référence : les trois lignes de la feuille « Ajouter » ne se décalent pas les
unes après les autres — elles sont déjà en place dans la feuille qui monte.
Aucun *stagger*.

Pourquoi : la feuille est déjà le mouvement. Décaler ses enfants ajoute
150–300 ms avant que le contenu soit lisible, pour zéro information.

Tawla : conséquence directe — `.plat-apparait` (décalage en cascade des plats
à l'arrivée de la carte, Phase D2) est à **conserver** parce qu'il joue au
premier chargement d'une longue liste, mais à ne **pas** étendre au contenu
des modales.

### 3. Le passage d'un écran à l'autre glisse, avec parallaxe

Référence : l'écran qui arrive translate de `100%` à `0` ; celui qui part ne
recule que de ~30 % de la largeur, pas de 100 %. Durée ~280 ms, pas de fondu
— translation pure.

Pourquoi : la parallaxe hiérarchise. L'écran qui part reste « en dessous »
dans la pile, ce qui rend le retour évident.

Tawla, avec une réserve : c'est un **site web**, pas une application native.
Une translation horizontale de 100 % de la fenêtre sur un écran de bureau est
un effet de diaporama, pas une navigation. Retenu donc pour les vues empilées
*à l'intérieur* du parcours client (carte → panier → suivi → paiement, qui
sont déjà des vues plein écran de la même page), et **rejeté** pour la
navigation entre pages du site vitrine, où un fondu court (`--motion-fast`)
suffit.

### 4. La pression répond avant tout le reste

Référence : le bouton rond de fermeture prend un fond plus clair **à
l'appui**, avant même que l'action se produise. Idem pour les lignes de
liste : la ligne entière s'éclaircit sous le doigt.

Pourquoi : c'est le seul retour qui doit être perçu comme instantané. Au-delà
de ~120 ms, l'utilisateur appuie une seconde fois.

Tawla : `--motion-micro`, et la zone pressée est **la cible entière**, pas
seulement son texte. Aujourd'hui seul `ui/Button` variante `primary` a un
état pressé (`active:translate-y-[2px]`) ; les 123 `<button>` écrits à la
main dans `app/` et `components/` n'en ont aucun. C'est le premier chantier
du système, avant toute animation d'arrivée.

### 5. Un reflux se joue, il ne saute pas

Référence : quand le pavé numérique se referme, la section « Diviser » et le
bouton « Ajouter » ne réapparaissent pas d'un coup — ils montent dans
l'espace libéré, en même temps que le clavier descend.

Pourquoi : un saut de mise en page force l'œil à retrouver sa place. Une
montée le porte.

Tawla : c'est le défaut le plus visible du menu client aujourd'hui. Ajouter
un plat déplie la ligne (quantité, note pour la cuisine, « à partager »)
d'environ 250 px d'un coup, et pousse toute la carte vers le bas sans
transition. Même chose pour la barre de panier en bas, qui apparaît sèchement.
`--motion-normal` + `--ease-enter` sur la hauteur et l'opacité des champs
révélés.

### 6. Une valeur qui change se remplace en fondu

Référence : décocher un participant fait disparaître son montant en fondu et
recalculer celui de l'autre dans le même temps (~150–200 ms), jamais un
remplacement sec de chiffre.

Pourquoi : le fondu prouve que c'est bien **le clic** qui a changé le nombre.
Un chiffre qui se substitue instantanément se lit comme un rafraîchissement
de données, pas comme une conséquence.

Tawla : le total de la barre de panier, les parts de `SplitBill.tsx`, le
compteur de quantité. `--motion-fast`. Avec `font-variant-numeric:
tabular-nums` déjà en place à ces endroits, la largeur ne bouge pas pendant le
fondu.

### 7. Un succès est une arrivée franche, pas une fête

Référence, et c'est le point le plus important du lot : l'écran « Ton tricount
est prêt » **n'a aucune animation de célébration**. La coche verte est déjà à
sa taille finale quand l'écran entre ; c'est la translation de l'écran
(principe 3) qui porte la satisfaction. Seul détail ajouté : le bouton
d'action principale en bas arrive avec ~60–100 ms de retard sur le corps de
l'écran, ce qui amène l'œil sur l'étape suivante.

Pourquoi : la célébration est un coût pour l'utilisateur qui répète l'action.
Elle se paie une fois, à la première commande, pas à chaque tournée.

Tawla : `CelebrationOverlay.tsx` (confettis + `celebration-pop` +
`celebration-fade`) est à **réduire**, pas à étendre — décision à trancher
avec Wassim, parce qu'elle revient sur un choix déjà livré. Piste : garder la
célébration pour le tout premier envoi de commande d'un téléphone donné, et
s'en tenir à l'arrivée franche + le retard sur le bouton pour les suivantes.

## Ce qu'on n'animera pas

Même logique que la table « À ne pas importer de digitalMenu » de
`ROADMAP_DESIGN.md` — vu et écarté, à ne pas reproposer sans déclencheur
nommé.

| Ce qui est tentant | Pourquoi non |
|---|---|
| Apparition en cascade (*stagger*) du contenu des modales | Principe 2 : retarde la lecture sans rien expliquer |
| Pulsation permanente sur un élément d'attente | Une seule respire à la fois, et seulement si elle demande une action (déjà la règle de `.piece[data-urgente]`) |
| Translation horizontale plein écran entre pages du site vitrine | Principe 3 : effet de diaporama sur écran de bureau |
| Ressort / rebond sur une modale ou un bouton | Le rebond n'appartient qu'à ce que le doigt tient (plan de salle, carrousel) |
| Animation au survol sur téléphone | Il n'y a pas de survol : c'est l'état pressé qui compte (principe 4) |
| Parallaxe au défilement, révélation de section à l'entrée dans l'écran hors home | `.fondu-scroll` est déjà en place sur les 3 blocs de la home (Phase D2) et suffit ; le menu client se défile pour commander, pas pour être découvert |

## Accessibilité

`prefers-reduced-motion: reduce` neutralise **toutes** les animations de ce
fichier — la règle existe déjà dans `globals.css` pour les 6 animations
actuelles, elle est à étendre à chaque nouvelle. Neutraliser veut dire
« l'état final, immédiatement », jamais « pas d'état final » : une modale sans
animation d'entrée s'ouvre quand même.

Deux exigences qui vont avec, et qui manquent aujourd'hui :

- Un état `:focus-visible` visible sur chaque cible cliquable. Relevé au
  2026-09-09 : 6 `focus-visible` dans tout le frontend, tous dans le CSS du
  plan de salle. `ui/Button` n'en a pas.
- Aucune animation ne conditionne l'accès à une information : le contenu est
  dans le DOM et lisible avant, pendant et après.

Deux défauts de contraste relevés en mesurant la charte le 2026-09-09, hors
sujet motion mais à corriger avec les jetons puisqu'ils touchent les mêmes
fichiers — et exempts du verrou « nomme le restaurateur » de `CLAUDE.md`,
puisque c'est le produit qui fait faux :

| Couple | Mesuré | Où | Piste |
|---|---|---|---|
| `--semoule` sur `--harissa` | 3,97:1 | libellé de chaque bouton primaire, et `table.label` sous le nom du restaurant (le nom lui-même passe : 28 px = grand texte) | `#fff` sur harissa = 4,55 ; `--harissa-dark` = 5,17 |
| `--ink-faint` sur `--semoule` | 3,78:1 | 30 usages de 10,5 à 13 px (notes de plat, options, mentions du suivi) ; 4,34:1 sur fond blanc | `#786250` = 5,00 sur semoule, 5,74 sur blanc |

## Comment travailler ce fichier

1. Une tâche = une branche = une PR, CI verte avant merge — même discipline
   que `ROADMAP.md`.
2. Les jetons d'abord, les composants ensuite, les pages en dernier. Une
   animation écrite avant les jetons est une valeur en dur de plus.
3. Rien ici ne passe avant une tâche non cochée de `ROADMAP.md` marquée
   comme bloquante pour la mise en ligne ou le premier pilote.
