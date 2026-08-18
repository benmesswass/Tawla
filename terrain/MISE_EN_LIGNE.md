# Mettre Tawla en ligne — Phase 20

Mode d'emploi de la seule phase technique que Claude Code ne peut pas faire :
elle demande des comptes, une carte bancaire et un domaine.

**Compter une demi-journée.** À faire d'une traite, pas en trois soirs : une
mise en ligne à moitié faite est un service qui répond mais qui perd les
commandes.

**Prérequis : la Phase 19 doit être fusionnée.** Le point 19.3 (limiteur de
débit derrière le proxy) n'a de sens qu'ici, et sans lui le premier soir de
service donnera des `429` à toute l'équipe.

---

## Étape 0 — Le seul critère qui départage les hébergeurs

Avant de comparer les prix, poser **une** question à chaque candidat :

> La base Postgres est-elle **managée**, avec une sauvegarde automatique
> quotidienne incluse dans le palier que je paie, et une procédure de
> restauration documentée ?

Si la réponse est non, l'hébergeur est éliminé — quel que soit son prix. Un
pilote qui perd son service du soir ne revient pas.

Ce que j'ai vérifié le 15/08/2026, à revérifier au moment de payer parce que ces
offres bougent :

| | Postgres | Conséquence |
|---|---|---|
| **Render** | Managé, sauvegardes automatiques annoncées sur les paliers payants | Candidat principal |
| **Railway** | Conteneur **non managé** — la sauvegarde est à votre charge | À écarter, sauf à ajouter soi-même un `pg_dump` planifié |

Les sources tierces se contredisent sur la profondeur exacte de restauration
selon les paliers Render. **Lire la page de tarifs le jour de l'inscription**, et
ne payer que si la ligne « sauvegardes » est explicite sur le palier choisi.

Trois autres exigences, toutes satisfaites par Render comme par Railway :

- **WebSocket natif** (le temps réel serveur/cuisine en dépend entièrement) ;
- **une seule instance** — ne jamais activer l'auto-scaling : le gestionnaire de
  connexions et le limiteur de débit vivent en mémoire du processus ;
- **un chemin de sonde de santé configurable** — ce sera `/health`.

Ordre de grandeur du budget mensuel : une instance web d'entrée de gamme plus une
base managée, soit environ 15 à 25 $ par mois, plus le domaine. Le frontend tient
sur l'offre gratuite de Vercel. **Ne pas prendre l'offre gratuite pour le
backend** : elle met le service en veille, et un service en veille perd ses
connexions WebSocket — donc les commandes du soir.

---

## Étape 1 — Le domaine

1. Réserver `tawla.tn` (registrar tunisien, `.tn` demande souvent un justificatif
   d'activité), `tawla.com` en secours.
2. Décider tout de suite la répartition, elle conditionne toute la suite :
   - `tawla.tn` → le frontend (Vercel)
   - `api.tawla.tn` → le backend (Render)
3. Ne rien configurer d'autre pour l'instant : les DNS se posent à l'étape 4.

---

## Étape 2 — Générer les vraies clés

Sur votre machine, dans `backend/`, avec l'environnement de développement
installé :

```bash
# JWT_SECRET — signe les jetons de connexion du personnel
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Paire VAPID — notifications « votre commande est prête »
python -c "
from py_vapid import Vapid02
from py_vapid.utils import b64urlencode
from cryptography.hazmat.primitives import serialization
v = Vapid02(); v.generate_keys()
pub = v.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
priv = v.private_key.private_numbers().private_value
print('VAPID_PUBLIC_KEY=' + b64urlencode(pub))
print('VAPID_PRIVATE_KEY=' + b64urlencode(priv.to_bytes(32, 'big')))
"
```

Coller ces trois valeurs dans un gestionnaire de mots de passe, **pas dans un
fichier du dépôt**. Le `.env` local ne doit jamais contenir les clés de
production : c'est le chemin le plus court vers une clé publiée par erreur.

Filet de sécurité déjà en place : si `ENV=production` et que `JWT_SECRET` est
resté la valeur de développement, l'application **refuse de démarrer**
(`app/core/config.py`). C'est voulu — un backend qui ne démarre pas est moins
grave qu'un backend dont tout le monde peut forger les jetons.

---

## Étape 3 — Le backend

1. Créer le service web depuis le dépôt GitHub, **racine `backend/`**, type
   Docker. Le `Dockerfile` fait déjà le bon travail : il lance
   `alembic upgrade head && uvicorn …`, et le `&&` fait échouer le conteneur si
   une migration échoue plutôt que de démarrer sur un schéma incohérent.
2. Créer la base Postgres managée **dans la même région** que le service.
3. Renseigner les variables d'environnement :

| Variable | Valeur |
|---|---|
| `DATABASE_URL` | l'URL interne fournie par l'hébergeur |
| `ENV` | `production` |
| `JWT_SECRET` | la valeur générée à l'étape 2 |
| `FRONTEND_ORIGIN` | `https://tawla.tn` — **l'origine exacte**, sans barre finale |
| `VAPID_PUBLIC_KEY` · `VAPID_PRIVATE_KEY` | les valeurs générées à l'étape 2 |
| `VAPID_CONTACT_EMAIL` | `contact@tawla.tn` |

Pas de variable à renseigner pour le limiteur de débit derrière le proxy
(19.3) : Render est systématiquement fronté par Cloudflare, qui pose
`CF-Connecting-IP` à l'IP réelle du client et rejette en 403 toute tentative
de le forger — le code s'appuie directement sur cet en-tête, rien à
configurer.

4. **Sonde de santé** : chemin `/health`. Elle interroge la base et renvoie 503
   si elle est injoignable — c'est ce qui permet à l'hébergeur de redémarrer le
   service au lieu de le laisser répondre « ok » pendant qu'aucune commande ne
   passe.
5. **Instances : 1. Ne pas y toucher.**

Vérification avant de continuer :

```bash
curl -i https://api.tawla.tn/health
# attendu : 200 et {"status":"ok"}
```

Si vous obtenez `{"status":"degraded"}` avec un 503, le service tourne mais ne
voit pas la base : c'est `DATABASE_URL` qu'il faut corriger, pas le code.

---

## Étape 4 — Le frontend

1. Importer le dépôt sur Vercel, **racine `frontend/`**.
2. Variable d'environnement : `NEXT_PUBLIC_API_URL=https://api.tawla.tn`.
   Attention : elle est lue **à la construction**, pas à l'exécution — la
   changer impose de reconstruire.
3. Brancher le domaine `tawla.tn` sur le projet Vercel et `api.tawla.tn` sur le
   service backend.
4. Attendre la propagation DNS et les certificats (quelques minutes à quelques
   heures).

Vérification : ouvrir `https://tawla.tn`. La page d'accueil doit s'afficher avec
« tarif communiqué au premier rendez-vous » tant que la Phase 22 n'est pas faite.

---

## Étape 5 — La sauvegarde, et sa restauration

**C'est l'étape qu'on est tenté de sauter, et la seule qui prouve les autres.**

1. Activer la sauvegarde automatique quotidienne sur la base managée.
2. Créer un établissement de test avec quelques commandes :
   ```bash
   cd backend && python scripts/setup_restaurant.py \
     --config mon-pilote.json --frontend-url https://tawla.tn
   ```
3. Attendre la première sauvegarde automatique.
4. **Restaurer cette sauvegarde sur une base jetable** (pas sur la base de
   production), et vérifier que les commandes de test y sont.
5. Noter dans ce fichier, ci-dessous, la date de l'essai et la durée réelle de
   la restauration.

> **Essai de restauration** — date : ______ · durée : ______ min · résultat : ______

Une sauvegarde jamais restaurée n'est pas une sauvegarde : c'est une case cochée.
Le jour où vous en aurez besoin, ce sera un vendredi 21 h, et ce n'est pas le
moment de découvrir la procédure.

Supprimer l'établissement de test avant d'installer un vrai pilote.

---

## Étape 6 — Le monitoring

1. Créer un compte UptimeRobot (offre gratuite suffisante).
2. Moniteur HTTP sur `https://api.tawla.tn/health`, toutes les 5 minutes.
3. Alerte par e-mail **et par SMS ou notification téléphone** — une alerte que
   vous ne verrez qu'au réveil ne sert à rien pendant un service.
4. Second moniteur sur `https://tawla.tn`, même fréquence.
5. Brancher la collecte des erreurs : le log drain de l'hébergeur suffit, les
   logs sortent déjà en JSON structuré. Ne pas installer de SDK avant d'avoir
   une destination réelle.

Vérification : couper volontairement la base une minute (ou changer
`DATABASE_URL` pour une valeur fausse), et **constater que l'alerte arrive sur
votre téléphone**. Remettre la bonne valeur ensuite.

---

## Étape 7 — Rejouer le parcours complet

À faire sur le domaine réel, avec **deux téléphones et un ordinateur**, pas dans
un seul onglet. Compter vingt minutes.

| # | Ce que vous faites | Ce qui doit se produire |
|---|---|---|
| 1 | Créer un compte sur `tawla.tn/signup` | Vous arrivez sur le dashboard, connecté |
| 2 | Créer une table et un plat | Ils apparaissent dans les listes |
| 3 | Créer un compte serveur et un compte cuisine (onglet Équipe) | Le mot de passe temporaire s'affiche **une seule fois** — le noter |
| 4 | Ouvrir `/staff` sur le téléphone A avec le compte serveur | L'écran serveur s'affiche, pastille de connexion en vert |
| 5 | Ouvrir `/kitchen` sur l'ordinateur avec le compte cuisine | Écran cuisine, vide |
| 6 | Scanner le QR de la table avec le téléphone B, commander deux plats | La commande apparaît **immédiatement** sur le téléphone A, sans rafraîchir |
| 7 | Prendre en charge, puis confirmer depuis le téléphone A | La commande arrive **immédiatement** sur l'écran cuisine |
| 8 | « En préparation », puis « Prêt » depuis la cuisine | Le téléphone B (client) voit le statut changer tout seul |
| 9 | Demander à payer en espèces depuis le téléphone B | La demande apparaît sur le téléphone A |
| 10 | Encaisser depuis le téléphone A | Le téléphone B voit le paiement confirmé |
| 11 | Couper le Wi-Fi du téléphone B, valider une commande, rallumer | La commande part toute seule au retour du réseau, **et une seule fois** |
| 12 | Rafraîchir `/staff` en pleine commande | Rien ne disparaît : l'écran se recharge depuis le serveur |
| 13 | Ouvrir `/dashboard` | Recette du jour et commandes perdues en tête |

**Le point 11 est le test de la Phase 19.2.** S'il produit deux commandes, ne pas
mettre en service : c'est exactement le défaut qui fait préparer deux fois le
même plat.

Si un point échoue, noter lequel et arrêter. Un parcours qui casse à l'étape 7
en démonstration coûte le rendez-vous.

---

## Étape 8 — La déclaration INPDP

À faire **avant le premier client réel**, pas après. Le produit est conforme
depuis la Phase 16 (consentement affiché, politique publiée en fr et ar,
rétention de 24 mois, purge réelle) ; il manque le dépôt administratif.

1. Formulaires sur `inpdp.tn`, section déclarations.
2. Traitement à déclarer : **fidélisation de la clientèle d'un établissement de
   restauration**.
3. Données collectées : numéro de téléphone, et date de naissance facultative.
4. Finalité : compteur de visites et récompense, propres à un seul établissement.
5. Durée de conservation : **24 mois sans nouvelle commande**, puis suppression.
6. Destinataires : aucun. Le numéro n'est jamais transmis à un tiers.
7. Joindre la politique de confidentialité publiée sur
   `tawla.tn/confidentialite`.

Point à clarifier avec l'INPDP, et à écrire noir sur blanc dans le contrat
pilote : **le restaurateur est responsable du traitement, Tawla est
sous-traitant.** C'est ce que dit déjà `terrain/PRISE_EN_MAIN.md` au patron ; la
déclaration doit dire la même chose.

Noter ici la date de dépôt et le numéro de récépissé :

> **Déclaration INPDP** — déposée le : ______ · récépissé n° : ______

---

## Critère de sortie de la Phase 20

Cochez seulement quand les cinq sont vrais :

- [ ] Une commande passée depuis un téléphone sur `tawla.tn`, vue sur l'écran cuisine
- [ ] Une sauvegarde restaurée pour de vrai, avec sa durée notée ci-dessus
- [ ] Une alerte de monitoring reçue sur votre téléphone lors d'une coupure volontaire
- [ ] Le parcours en 13 points rejoué en entier, sans échec
- [ ] La déclaration INPDP déposée

Tant que ces cinq lignes ne sont pas cochées, **ne pas installer de pilote.**
