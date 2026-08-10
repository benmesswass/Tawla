# ROADMAP — resto-qr-menu

Issue de l'audit QA / Product Owner / Design du 2026-08-10. Traitement autonome
terminé le même jour : chaque case cochée = corrigé + revérifié (tests auto +
test manuel Playwright). Ordre = ordre de traitement réel (bloquants d'abord).

## Phase 1 — Bugs critiques (bloquants pilote)

- [x] Aucune récupération d'état côté serveur/cuisine au chargement —
      `GET /orders/by-restaurant/{id}/active` ajouté + appelé au montage de
      `staff/page.tsx` et `kitchen/page.tsx`, en complément du push
      WebSocket. Test : `test_active_orders_survive_a_late_or_refreshed_screen`.
- [x] Écran client bloquant sans retour sur erreur API — `loadError` (fatal,
      avec bouton Réessayer) séparé de `orderError` (bannière récupérable,
      panier conservé). Un article devenu indisponible est retiré du
      panier sans effacer le reste.

## Phase 2 — Bugs majeurs

- [x] Statut `served` câblé dans l'UI — nouvelle liste "Prêtes à servir" côté
      serveur (`staff/page.tsx`), alimentée par un broadcast `order.ready`.
- [x] Messages d'erreur API traduits — codes machine (`ITEM_UNAVAILABLE`,
      `INVALID_TABLE_CODE`...) renvoyés par le backend, traduits côté client
      dans `frontend/lib/errors.ts`.
- [x] Isolation restaurant vérifiée sur `assign-staff` (staff inexistant ou
      d'un autre restaurant → 404/409). Tests :
      `test_assign_staff_rejects_unknown_staff_id`,
      `test_assign_staff_rejects_staff_from_another_restaurant`.
- [x] `next` mis à jour 14.2.5 → 14.2.35 (corrige la CVE critique signalée).
      Note : `npm audit` liste encore des advisories "high" qui ne se
      corrigent qu'en sautant sur Next 15/16 (breaking change majeur,
      hors périmètre de cette passe — décision produit à part, pas un
      "mineur").

## Phase 3 — Mineurs (fiabilité / UX)

- [x] Reconnexion WebSocket automatique (backoff exponentiel) + indicateur
      connecté/déconnecté — `lib/useReconnectingSocket.ts` +
      `components/ConnectionBadge.tsx`, utilisés sur serveur/cuisine/client.
- [x] Bouton "Commander à nouveau" sur l'écran de suivi client.
- [x] Menu trié par ordre logique du repas (Entrées → Plats → Desserts →
      Boissons) — `CATEGORY_ORDER` dans `menu/router.py`.
- [x] `aria-label` sur les boutons +/- de quantité.
- [x] Page racine (`/`) et 404 (`not-found.tsx`) personnalisées + favicon
      minimal (`app/icon.tsx`).

## Phase 4 — Produit / Design

- [x] Suivi temps réel côté client (Envoyée → Confirmée → En cuisine → En
      préparation → Prête → Servie) — canal WebSocket dédié par commande
      (`/ws/order/{restaurant_id}/{order_id}`), état persisté en
      `sessionStorage` pour survivre à un rafraîchissement de page.
- [x] Dashboard resto minimal (`/dashboard?restaurant_id=1`) — CRUD complet
      du menu (créer/éditer/supprimer, bascule dispo), sans passer par
      Swagger. Endpoints `PATCH`/`DELETE /menu-items/{id}` ajoutés.
- [x] `description` et `image_url` affichés sur l'écran client + menu
      regroupé par catégorie avec titres de section.
- [x] Saisie d'une note par article côté client (texte libre par ligne de
      panier, transmis à la cuisine).
- [x] Première passe d'identité visuelle sur l'écran client (nom du
      restaurant affiché, bandeau de couleur).
- [x] Fallback si l'écran cuisine tombe — bouton "Imprimer (filet de
      secours)" sur l'écran cuisine, génère une vue imprimable des
      commandes en cours à partir de l'état déjà chargé en mémoire (pas
      une vraie intégration imprimante — suffisant comme filet de sécurité
      MVP, une vraie solution d'impression reste un chantier à part si le
      besoin est confirmé en pilote réel).

## Fait

Tout ce qui précède a été corrigé, testé (pytest + Playwright + `tsc` +
`next build`), et revérifié dans la même session que l'audit — voir le
second rapport (`report-v2`) pour le détail des captures avant/après.

## Notes pour la suite (hors périmètre de cette passe autonome)

- Montée de version majeure Next.js (15/16) : breaking change réel,
  décision produit à prendre à part, pas traitée ici.
- Auth staff (login serveur/cuisine/dashboard) : toujours pas d'authentification
  sur `/staff`, `/kitchen`, `/dashboard` — déjà su avant l'audit
  ("À faire avant un vrai pilote resto" dans `README.md`), non traité ici
  car ça dépasse la liste des remarques QA/PO/Design (c'est une décision
  produit — quel mécanisme d'auth, quel coût pour le pilote — pas un bug).
- Vraie intégration imprimante cuisine (au-delà du filet de secours
  navigateur ci-dessus).
