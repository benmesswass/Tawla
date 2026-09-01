# Tawla — Roadmap Design

Née le **2026-09-01** d'un comparatif visuel entre Tawla et son concurrent
digitalmenu.tn (tour des deux sites, démos comprises, relevé technique des
animations dans les feuilles de style des deux sites).

**Ce fichier ne remplace pas [`ROADMAP.md`](./ROADMAP.md).** Il pilote le
design du parcours client, en parallèle, sans réordonner les phases 19bis à
24. Une session qui cherche la prochaine tâche de **code produit ou de mise
en ligne** va dans `ROADMAP.md`. Une session qui travaille le **visuel du
menu client ou de la vitrine** vient ici.

## Constat qui fonde cette roadmap

L'écart avec digitalmenu.tn n'est pas une question de charte — les tokens
`--harissa` / `--semoule` / `--menthe` / `--laiton` de Tawla tiennent la
route. L'écart est un écran vide : le menu client part du principe que le
patron ajoutera les photos plus tard, et 0 règle CSS `transition`/`animation`
n'a été détectée sur le site vitrine, contre 279 éléments animés (AOS,
fondus, pulses) chez le concurrent.

## Objectif

**Un menu client qui se vend par la photo autant que par le prix**, sans
copier la gamification ni le positionnement multi-métiers de digitalMenu —
les deux vont à l'encontre du positionnement de Tawla (« le serveur garde la
main », salle avec service à table).

## Phase D1 — La photo par défaut

C'est l'écart qui compte : une fiche plat sans photo a l'air inachevée face
à un concurrent qui en montre systématiquement, même en démo générique.

- [x] Photo obligatoire à la création d'un plat, ou pack de visuels
      génériques par catégorie proposé en attendant que le patron envoie les
      siens — décidé 🧑 : pack générique (photo obligatoire aurait bloqué les
      comptes Essentiel, l'upload étant verrouillé Pro, et cassé l'import CSV
      en masse). Icônes par catégorie plutôt que fausses photos génériques —
      une icône ne prétend jamais être le plat réel (PR #121)
- [x] Bannière de couverture en tête du menu client (photo du lieu + logo
      rond), à la place du bandeau texte seul actuel
      (`frontend/app/menu/[qrToken]/page.tsx`) — repli identique à l'écran
      actuel tant qu'aucune couverture n'est envoyée ; upload ouvert à tous
      les paliers, pas verrouillé Pro contrairement à la photo des plats
      (PR #121)
- [ ] Icônes réseaux sociaux du restaurant dans l'en-tête du menu client, si
      renseignés au profil établissement

## Phase D1bis — Avis Google après paiement (Pro+)

Idée de Wassim (2026-09-01), insérée ici plutôt qu'en D2 pour ne pas
renumeroter ce qui suit — même logique que la Phase 19bis de `ROADMAP.md`.

- [ ] Une fois le paiement de l'addition confirmé côté client, une modale
      s'ouvre automatiquement pour proposer un avis Google, avec un lien
      direct vers la fiche Google Maps du restaurant. Réservé au palier Pro
      et au-dessus (à vérifier via `require_tier`/`effective_tier`, comme le
      mode Ramadan). Nouveau champ (ex. `google_review_url`) sur
      `Restaurant`, nullable — la modale ne s'affiche que si le manager l'a
      renseigné ET que son palier l'autorise.

## Phase D2 — Navigation et micro-interactions

- [ ] Barre de catégories collante en haut du menu client pendant le scroll,
      catégorie visible surlignée (le concurrent l'a, Tawla affiche une
      liste plate sans repère de position)
- [ ] Transitions de base sur les boutons/liens du site vitrine
      (0.15–0.25s, easing standard) et un léger fondu d'apparition au scroll
      sur les 3 blocs de bénéfices de la home

## Phase D3 — Preuve sociale publique

Bloqué tant qu'aucun chiffre réel n'existe — ne jamais inventer une valeur
« avant/après » (même règle que `ROADMAP.md` §23.2).

- [ ] Extraire une version publique de `/dashboard/preuve` pour la home,
      une fois qu'un pilote réel (Phase 23 de `ROADMAP.md`) a des chiffres
      mesurés et l'accord écrit pour être cité

## À ne pas importer de digitalMenu

Vu et délibérément écarté — à ne pas reproposer sans un déclencheur nommé,
même logique que `ROADMAP.md` § Sous condition :

| Ce qui est tentant | Pourquoi on ne le fait pas |
|---|---|
| Gamification (roulette, ventes flash, pop-ups, happy hours) | Contredit « le serveur garde la main » — Tawla vend du contrôle de salle, pas de l'engagement client automatisé |
| Positionnement multi-métiers (café / fast-food / hôtel / resto) | La niche « salle avec service à table » est un choix de positionnement, pas un manque à combler |

## Comment travailler cette roadmap

1. Une tâche = une branche = une PR, CI verte avant merge — même discipline
   que `ROADMAP.md`.
2. Cocher `[x]` avec le numéro de PR.
3. Rien ici ne passe avant une tâche non cochée de `ROADMAP.md` marquée
   comme bloquante pour la mise en ligne ou le premier pilote.
4. Phase D3 ne se code pas avant que la donnée réelle qu'elle affiche existe
   — même règle que `ROADMAP.md` §23.2 sur les données de terrain.
