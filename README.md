# Tawla

Application de commande depuis la table pour restaurants tunisiens.

Le client scanne le QR code posé sur sa table, compose son panier depuis le menu digital et valide. La commande apparaît immédiatement dans un écran partagé consulté par tous les serveurs (« pool » de commandes en attente, toutes tables confondues). Un serveur la prend en charge, se déplace à la table pour confirmer avec les clients, puis valide sur l'application — ce qui déclenche l'envoi vers la cuisine. Le manager dispose d'une vue d'ensemble en temps réel : temps passé à chaque étape (en attente de confirmation, confirmée mais pas encore en cuisine, en préparation, sortie vers le client) et nombre de commandes prises par serveur, utile notamment pour le suivi des primes de rendement. Le paiement se fait depuis l'application, par carte avec pourboire optionnel, ou en signalant une intention de payer cash pour que le serveur apporte l'addition.

Toutes les fonctionnalités prévues, phase par phase, sont détaillées dans [`ROADMAP.md`](./ROADMAP.md).

## Stack (à confirmer)

Aucune décision technique n'est encore actée. Proposition de départ pour rester cohérent avec les autres projets du même auteur : Next.js (App Router) + TypeScript + Prisma/PostgreSQL + Tailwind — à valider avant le début du développement (Phase 0 de la roadmap).
