# Prochaines étapes — ce qui t'attend

Extrait pratique de `ROADMAP.md` (qui reste la seule source de vérité du projet) : uniquement les points qui ont besoin de toi — décision produit, compte réel, ou accès à ton PC. Rien d'autre n'a bougé ; tout le reste du travail autonome (Phases 9, 10, 11) est mergé sur `main`.

## 1. Décisions produit à trancher

- **Prix des 3 paliers d'abonnement** (Essentiel / Pro / Business) — aucun montant fixé à ce stade.
- **Contenu exact de chaque palier** — j'ai proposé un découpage dans `ROADMAP.md` Phase 11 (Essentiel = socle Phases 0-4, Pro = + fidélité/export CSV/zones/Ramadan-café, Business = + multi-établissements) à partir des frontières déjà réelles du code. À valider ou ajuster.
- **Nom de domaine** — `tawla.tn` proposé en priorité (positionnement tunisien), `.com` en secours.
- **Hébergeur backend** — Railway ou Render proposés (déploient le `Dockerfile` existant, gèrent le WebSocket nativement, Postgres managé avec sauvegardes). Un choix + un budget à valider.

## 2. Actions qui nécessitent tes mains (comptes réels, argent, DNS)

Rien de tout ça n'a été touché — ce sont des comptes/dépenses réels, hors de portée d'un chantier autonome.

- Réserver le nom de domaine choisi.
- Créer un compte chez l'hébergeur backend choisi (Railway/Render) + un compte Vercel pour le frontend.
- Provisionner le déploiement de staging, générer les vraies clés (`JWT_SECRET`, VAPID) et les poser en variables d'environnement.
- Activer les sauvegardes automatiques du Postgres managé.
- Brancher un monitoring externe (ex. UptimeRobot, gratuit) sur l'endpoint `/health` déjà existant.

## 3. Ce que je reprendrai dès que tu m'auras débloqué un point ci-dessus

Pas besoin de redemander explicitement — dès que l'un des points ci-dessus est tranché, je reprends directement là-dessus :

- Hébergeur + domaine choisis → je déploie sur staging, rejoue le parcours complet (client/serveur/cuisine/manager) sur l'environnement réel, puis bascule en prod une fois validé par toi.
- Prix des paliers fixés → je code la page tarifs publique, le flux de mise à niveau, et la logique de gating des fonctionnalités Pro/Business (le champ `Restaurant.subscription_tier` existe déjà, prêt à l'emploi).
- Grands groupes / événements (mariages, réservations de salle) — reste ouvert pour une session de cadrage dédiée, je ne relance pas le sujet tant que tu ne le demandes pas (cf. `ROADMAP.md` Phase 7).

---

_Ce fichier est un instantané pratique pour cette reprise, pas un deuxième document de pilotage. Une fois ces points tranchés, les cases correspondantes se cochent directement dans `ROADMAP.md` — pas la peine de maintenir celui-ci en parallèle._
