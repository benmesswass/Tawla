# Tawla — Roadmap

Fichier unique de pilotage du projet. Une tâche cochée `[x]` doit mentionner la PR qui l'a livrée.

## Vision produit

Un client s'assoit à table, scanne le QR code, commande depuis un menu digital et valide son panier. La commande part vers un écran partagé consulté par tous les serveurs du service (les commandes de toutes les tables s'y empilent). Un serveur la prend en charge, se déplace à la table pour confirmer avec les clients, puis valide sur l'app — ce qui envoie la commande en cuisine. Le manager suit en temps réel l'activité globale : temps passé à chaque étape, charge de travail par serveur (base pour les primes de rendement). Le paiement se fait depuis l'app : carte avec pourboire optionnel, ou demande d'addition pour payer cash à table.

North star : un service fluide en salle (zéro commande perdue ou oubliée) et une visibilité complète pour le manager sur la performance de l'équipe.

---

## Phase 0 — Fondations

- [ ] Choix de la stack technique (proposition : Next.js + TypeScript + Prisma/PostgreSQL + Tailwind)
- [ ] CI de base (lint, typecheck, tests)
- [ ] Modèle de données initial : `Restaurant`, `Table`, `Categorie`, `Plat`, `Commande`, `LigneCommande`, `Utilisateur` (rôles serveur / cuisine / manager)
- [ ] Auth staff (serveurs, cuisine, manager) — le client, lui, n'a pas de compte : sa session est liée au QR code de la table
- [ ] Génération des QR codes par table (lien vers le menu, encodant l'identifiant de table)

## Phase 1 — MVP commande client

- [ ] Menu digital consultable depuis le QR (catégories, plats, prix, photo, description)
- [ ] Panier côté client + validation de la commande
- [ ] Envoi de la commande vers le pool partagé des serveurs
- [ ] État de la commande visible côté client (en attente / confirmée / en préparation / prête / servie)

## Phase 2 — Flux serveur & cuisine

- [ ] Écran serveurs : pool de toutes les commandes en attente (toutes tables), prise en charge (« claim ») par un serveur
- [ ] Confirmation à table : le serveur valide la commande sur l'app après l'avoir vérifiée avec les clients
- [ ] Transmission automatique à la cuisine dès la confirmation
- [ ] Écran cuisine : file d'attente des commandes confirmées, statuts (reçue / en préparation / prête)
- [ ] Statut final « sortie vers le client » (servie), déclenché par le serveur

## Phase 3 — Dashboard manager

- [ ] Vue temps réel de toutes les commandes en cours, par statut
- [ ] Temps moyen passé à chaque étape (attente de confirmation, confirmée → envoyée en cuisine, cuisine → sortie)
- [ ] Nombre de commandes prises en charge par serveur et par jour (base de calcul pour les primes de rendement)
- [ ] Statistiques plats les plus vendus, répartition par heure (identification des pics de charge)

## Phase 4 — Paiement

- [ ] Paiement carte depuis l'app, avec pourboire optionnel
- [ ] Demande de paiement cash depuis l'app (génère l'addition, prévient le serveur concerné)
- [ ] Partage de l'addition (split bill) : par personne, par plat, ou équitable

## Phase 5 — Spécificités culture tunisienne

- [ ] Mode Ramadan : menu ftour dédié, pré-commande calée sur l'heure exacte de la rupture du jeûne (variable chaque jour), anticipation du pic de charge en cuisine
- [ ] Commande groupée à table : panier commun pour les plats partagés (salades, mechouia...), couplé au split bill de la Phase 4
- [ ] Interface bilingue français / arabe (derja tunisienne), RTL natif ; option anglais/italien pour les zones touristiques
- [ ] Niveau de piment affiché par plat + mentions allergènes et halal
- [ ] Bouton « appeler le serveur », indépendant du passage de commande
- [ ] Gestion de la rupture de stock en temps réel (un plat en rupture est désactivé instantanément côté client)
- [ ] Mode café simplifié : commande de boissons seules, sans structure entrée/plat/dessert
- [ ] PWA offline-first : file d'attente locale si la connexion mobile est instable, envoi différé automatique
- [ ] Carte de fidélité digitale (ex. Nème café/plat offert, réduction anniversaire)

## Phase 6 — Croissance / opérationnel

- [ ] Multi-restaurants (un compte manager peut gérer plusieurs établissements, ou un établissement par compte selon le modèle retenu)
- [ ] Notifications SMS/push au client quand sa commande est prête
- [ ] Gestion des zones de salle (intérieur / terrasse / plage) pour les établissements concernés (ex. Hammamet, Sousse)
- [ ] Export des statistiques (manager)

## Phase 7 — Idées à trancher plus tard (🧑 arbitrage produit de Wassim)

- [ ] Modèle de paiement : frais de service uniquement vs vrai paiement intégral en ligne (implication juridique/comptable à valider)
- [ ] Programme de fidélité : par établissement vs mutualisé entre plusieurs restaurants partenaires
- [ ] Gestion des grands groupes / événements (mariages, réservations de salle)
- [ ] Nom de marque définitif et identité visuelle (le nom de repo « Tawla » est provisoire)
