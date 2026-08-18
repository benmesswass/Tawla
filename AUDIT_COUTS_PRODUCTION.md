# Audit des coûts de production — Tawla

Réalisé le **2026-08-18** sur `main` au commit `0644bd1`. Périmètre strictement
**technique** : infrastructure, services tiers, domaine, conformité technique.
Hors périmètre : comptabilité, assurance, temps de Wassim, marketing.

Chaque prix externe porte sa source et sa date de consultation. Ce qui n'a pas
pu être vérifié est écrit comme tel — jamais recopié d'un doc interne sans
retour à la source, jamais deviné. Voir §2 pour une limite importante de cette
session qui touche **toutes** les sources externes de cet audit.

---

## 1. Décision

**Coût plancher mensuel récurrent obligatoire (Phase 20, hébergement + frontend) :**

| Scénario | Montant | Condition |
|---|---|---|
| **Prudent — retenu** | **≈ 100 TND/mois** (34 $/mois) | Si le palier Vercel Pro est requis (lecture la plus probable des CGU Vercel pour un produit commercial — §4.1) |
| Optimiste | ≈ 41 TND/mois (14 $/mois) | Si le palier gratuit Vercel Hobby reste toléré pendant la phase pilote (lecture non tranchée) |

Je retiens le scénario prudent en tête : la restriction d'usage commercial de
Vercel est écrite noir sur blanc dans ses propres conditions (§4.1), pas une
hypothèse basse improbable. C'est un vrai risque de facturation surprise ou
de suspension de service, pas un détail.

**Coût de mise en place ponctuel obligatoire — incomplet, une inconnue réelle :**

Le prix de `tawla.tn` — la seule vraie inconnue chiffrable de cette phase —
**n'a pas pu être vérifié** depuis cette session (accès aux registrars
tunisiens bloqué, §2). Ce qui est chiffré : `tawla.com` (filet) ≈ **43
TND** (14,78 $, tarif de renouvellement Namecheap, non vérifié en direct) ;
déclaration INPDP **probablement gratuite** mais non confirmée avec
certitude (§4.2). Aucune autre ligne ponctuelle obligatoire n'a été trouvée
dans le dépôt — pas de migration de données, pas de prestataire, pas de
matériel.

**Postes conditionnels, avec leur déclencheur exact — à ne pas payer maintenant :**

| Poste | Coût si déclenché | Déclencheur |
|---|---|---|
| Konnect réel (paiement carte) | 1,3 % (cartes TN/e-dinar) à 2,9 % (cartes intl.) par transaction, 2 TND/virement, 0 abonnement | Un pilote qui réclame le paiement carte |
| Sentry payant | 0 (probablement — palier gratuit suffisant), 26 $/mois si dépassé | Un DSN créé **et** volume > 5 000 événements/mois |

Détail, sources et le reste des catégories (déjà engagé à confirmer,
trajectoire de stockage, gratuit confirmé) en §4.

---

## 2. Méthodologie — et une limite qui touche tout cet audit

Consultation le **18 août 2026**. Sources internes : lecture directe du code
du dépôt (`fichier:ligne` cités), `ROADMAP.md`, `terrain/MISE_EN_LIGNE.md`,
`backend/requirements.txt`, `backend/requirements-dev.txt`,
`frontend/package.json`, `backend/.env.example`, `backend/Dockerfile`,
`docker-compose.yml`. Visibilité du dépôt confirmée **publique** via l'API
GitHub (`mcp__github__search_repositories`, réponse `"private": false,
"visibility": "public"`, consultée le 18/08/2026).

**Limite technique de cette session, constatée et non contournable :** l'accès
réseau direct (outil WebFetch, et `curl` via le proxy d'egress configuré)
vers les pages officielles de tarification est **bloqué par la politique
réseau de l'organisation** pour cette session — testé et confirmé sur
render.com, vercel.com, uptimerobot.com, sentry.io,
developers.cloudflare.com, ati.tn, bct.gov.tn, et même sur un domaine sans
aucun lien avec un service payant (`en.wikipedia.org`, testé pour distinguer
un blocage ciblé d'un blocage général — c'est bien un blocage général de
sortie réseau directe pour cette session, pas une liste noire de
concurrents). Le `curl` direct renvoie systématiquement `403` du proxy — la
consigne de l'environnement est explicite : ne jamais contourner un refus de
politique réseau, le signaler. C'est fait ici.

**Conséquence directe sur la fiabilité des chiffres de cet audit** : aucune
page de tarification officielle n'a pu être ouverte directement depuis cette
session. Chaque prix externe cité vient de l'outil de recherche web (résumés
de résultats, eux-mêmes datés d'août 2026, s'appuyant le plus souvent sur des
sites tiers qui suivent ces grilles tarifaires plutôt que sur la page
officielle elle-même). C'est une source plus faible qu'une lecture directe de
la page primaire, et c'est marqué à chaque ligne du tableau. **Chaque prix de
ce document est à recouper par Wassim au moment de l'inscription réelle** —
recommandation déjà présente dans `terrain/MISE_EN_LIGNE.md` avant cet audit
et qui reste vraie a fortiori ici. Ce qui n'a pu être trouvé par aucune
recherche est marqué **« non vérifié »**, sans chiffre inventé pour combler
le trou.

**Taux de change retenus** (Banque Centrale de Tunisie de préférence, comme
demandé) :
- **1 USD ≈ 2,94 TND** — BCT daté du 31/07/2026 : 2,9375 TND ; recoupé avec le
  taux de marché du jour de consultation (Investing.com, 18/08/2026) : 2,9346
  TND — écart de 0,1 %, négligeable. Le taux exact du jour sur bct.gov.tn n'a
  pas pu être ouvert directement (§ ci-dessus).
- **1 EUR ≈ 3,37 TND** — meilleur chiffre trouvé (3,374 TND), source et date
  précises non confirmées avec certitude. Non utilisé pour un montant
  significatif de cet audit (tous les services tarifés le sont en USD, sauf
  Konnect et le registrar `.tn`, déjà en TND).

Render, Vercel, Sentry, Cloudflare et GitHub facturent tous en USD. **Note
factuelle, pas un problème à résoudre ici** : la Tunisie applique un contrôle
des changes — un particulier a besoin d'un compte en devises ou en dinars
convertibles pour obtenir une carte utilisable à l'international, et la BCT
fixe un plafond annuel par particulier pour ce type d'achat (« allocation
technologique », de l'ordre de **1 000 DT/an**, distincte de l'allocation
touristique de 6 000 DT/an). La Loi de Finances 2026 permet depuis le 1ᵉʳ
janvier 2026 aux résidents d'ouvrir un compte en devises sans autorisation
préalable de la BCT, sous réserve de la publication des décrets
d'application (non vérifiée ici). **Point à noter** : le total prudent de
cet audit (§1, ≈ 34 $/mois) représente environ 408 $/an, soit au taux
retenu ≈ 1 200 TND/an — au-dessus du plafond « allocation technologique »
particulier cité par la source trouvée. Je ne sais pas si un abonnement SaaS
professionnel récurrent est décompté sur cette même allocation ou sur une
autre catégorie (compte professionnel, statut auto-entrepreneur/patente) —
question posée à Wassim en §6, pas tranchée ici.

---

## 3. Ce qui existe déjà dans le dépôt (base de tout le reste)

- `backend/requirements.txt` (14 lignes) : FastAPI, SQLAlchemy, psycopg2,
  Pydantic, Alembic, `qrcode`, `bcrypt`, `pyjwt`, **`pywebpush`**,
  `python-multipart`. Aucun SDK de paiement, SMS, stockage objet ou
  observabilité.
- `backend/requirements-dev.txt` : ajoute seulement `pytest` et `httpx` (tests).
- `backend/.env.example:20-30` : confirme que `py_vapid` est utilisé en ligne
  de commande pour générer les clés VAPID (`from py_vapid import Vapid02`) —
  c'est une dépendance de `pywebpush`, pas un paquet séparément installé
  (confirmé par recherche : `pywebpush` déclare `py-vapid` comme dépendance).
- `backend/Dockerfile` : `alembic upgrade head && uvicorn …`, une seule
  commande de démarrage, cohérent avec la contrainte mono-instance déjà actée
  par la roadmap (gestionnaire WebSocket et limiteur de débit en mémoire,
  `ROADMAP.md` §20 et § Sous condition).
- `frontend/package.json` : Next.js 14.2.35, React 18, Tailwind — aucune
  dépendance de paiement, carte, ou analytics tierce.
- Recherche du dépôt entier (`.py`, `.ts`, `.tsx`, `.txt`, `.json`, `.yml`)
  pour des mentions de Stripe, Twilio, Firebase, AWS/S3, Cloudinary,
  SendGrid, Mailgun, Algolia, Auth0, Datadog, New Relic, PagerDuty, Segment,
  Mixpanel, Amplitude, Intercom, Zendesk : **aucune occurrence**. La liste de
  postes à chiffrer donnée en commande n'a rien manqué de visible dans le
  code.
- Métadonnées du dépôt GitHub (API, consultée le 18/08/2026) : champ
  `homepage` = `https://tawla-eight.vercel.app` — **un projet Vercel existe
  déjà**, probablement le déploiement automatique par défaut de
  l'intégration GitHub↔Vercel. Le palier (Hobby ou Pro) n'est pas visible
  depuis le dépôt → question posée en §6.

---

## 4. Tableaux chiffrés

### 4.1 — Obligatoire récurrent mensuel (pour sortir la Phase 20)

| Poste | Prix | ≈ TND/mois | Source | Palier gratuit suffisant ? |
|---|---|---|---|---|
| **Hébergement backend** — Render Web Service, palier **Starter** (512 Mo RAM, 0,5 CPU, **pas de mise en veille**) | 7 $/mois | 20,6 | Recherche web, résultats datés 2026, page officielle non consultable directement (§2) | Non — le palier gratuit met le service en veille après 15 min d'inactivité, ce qui coupe les WebSocket en plein service (déjà noté par `terrain/MISE_EN_LIGNE.md:49-50`) |
| **Postgres managé** — Render, palier **Basic-256mb** | 6 à 7 $/mois selon la source (deux chiffres trouvés, page officielle non consultable pour trancher) | 17,6 à 20,6 | Recherche web, résultats datés 2026 | Non — le palier Postgres gratuit de Render est supprimé après 30 jours sans préavis (trouvé via recherche), inutilisable en production |
| **Sous-total hébergeur (Render)** | **13 à 14 $/mois** | **38 à 41** | — | — |
| **Frontend** — Vercel | **0 (Hobby) si toléré, sinon 20 $/mois (Pro)** | 0 ou 58,8 | Vercel Fair Use Guidelines + Terms of Service, recherche web datée 2026 (page non consultable directement) | **Voir réserve ci-dessous — c'est la ligne la plus importante de ce tableau** |
| **Total** | **13-14 $ à 33-34 $/mois** | **38-41 à 97-100** | — | — |

**Réserve Vercel, détaillée** : les conditions de Vercel définissent l'usage
commercial comme « tout déploiement utilisé dans un but de gain financier de
toute personne impliquée dans sa production », avec pour exemple explicite
« toute méthode de demande ou de traitement de paiement des visiteurs du
site ». Le palier Hobby est réservé à un usage non-commercial ; **tout usage
commercial nécessite Pro ou Enterprise**. Tawla est un produit commercial par
construction (Phase 22 fixe un prix, Phase 24 vise des clients payants) —
même si le paiement des restaurateurs à Wassim se fait hors-ligne (virement,
chèque, `ROADMAP.md` Phase 22) et que le paiement carte du convive reste
simulé aujourd'hui, le déploiement lui-même existe **dans le but** d'un gain
financier, ce qui est le critère écrit par Vercel — pas seulement la présence
d'un flux de paiement en ligne. Les conditions elles-mêmes suggèrent de
contacter le support Vercel en cas de doute : c'est la voie la plus sûre pour
trancher avant la Phase 20, plutôt que de supposer. Techniquement, le volume
Hobby (≈ 100 Go de bande passante/mois, plusieurs centaines de minutes de
build) couvrirait largement quelques dizaines d'établissements — **la
question n'est pas le volume, elle est contractuelle**.

**Stockage Postgres au-delà du forfait inclus** : 0,30 $/Go/mois (≈ 0,88
TND), facturé à la seconde près. Le forfait inclus par palier n'a pas pu être
confirmé avec précision (page officielle non consultable) ; impact chiffré en
§4.4 — négligeable à l'échelle actuelle.

### 4.2 — Ponctuel / annuel obligatoire

| Poste | Prix | ≈ TND | Source |
|---|---|---|---|
| Domaine `tawla.tn` (registrar tunisien, priorité selon `ROADMAP.md:167`) | **Non vérifié** — aucune page de registrar tunisien (ATI, Topnet, HexaByte, register.tn) n'a pu être consultée directement, et la recherche web n'a fait remonter aucun chiffre en dinars fiable | — | À confirmer par Wassim directement sur `topnet.tn`, `ati.tn` ou `register.tn` au moment de l'achat |
| Domaine `tawla.com` (filet, `ROADMAP.md:167`) | ≈ 14,78 $/an (tarif de **renouvellement** Namecheap — la première année est souvent moins chère en promotion) | ≈ 43/an | Recherche web datée 2026, page officielle non consultable directement |
| Déclaration INPDP (`inpdp.tn`) | **Probablement gratuite** — aucune redevance mentionnée dans les sources trouvées sur la loi 2004-63 ni sur les pages INPDP décrivant la procédure de déclaration ; mais aucune confirmation explicite « c'est gratuit » n'a été trouvée non plus | — | Non confirmé avec certitude — à vérifier par Wassim sur `inpdp.tn` |

**Ce que recouvre le « justificatif d'activité » pour `.tn`** : d'après la
recherche, les pièces demandées dépendent du statut du déposant — pour un
particulier, une copie de la CIN et le formulaire de demande signé ; pour une
entreprise, le registre de commerce et la CIN du gérant ; pour une
association, la déclaration au JORT et la CIN du président. Wassim, projet
personnel, relèverait a priori du cas « particulier » — à confirmer avec le
registrar choisi.

### 4.3 — Déjà engagé, à confirmer par Wassim (invisible depuis le dépôt)

| Poste | Ce qui est su | Ce qui manque |
|---|---|---|
| `tawla-backend.onrender.com` | En ligne depuis au moins le 18/08/2026 (mesure du limiteur de débit, `ROADMAP.md:180`, PR #57) | Palier actif (gratuit ou payant) et date de début réelle — invisible depuis le dépôt, et une requête ne le révèle pas : le palier gratuit de Render sert aussi des requêtes, juste avec mise en veille entre deux |
| `tawla-eight.vercel.app` | Projet Vercel existant, trouvé via le champ `homepage` des métadonnées GitHub du dépôt (§3) — vraisemblablement le déploiement automatique par défaut de l'intégration GitHub | Palier (Hobby/Pro) inconnu |
| Domaine | `ROADMAP.md:167` liste la réservation comme **non cochée** | À confirmer que rien n'a été réservé en dehors du suivi de la roadmap |

### 4.4 — Trajectoire à projeter : croissance Postgres par les photos de carte

Base du calcul, citée en code :

- Plafond serveur dur : **3 Mo/photo** (`backend/app/modules/menu/router.py:190`,
  `TAILLE_PHOTO_MAX = 3 * 1024 * 1024`), imposé si le redimensionnement côté
  navigateur échoue ou est contourné.
- Redimensionnement navigateur avant envoi : côté long ramené à **1200 px**,
  JPEG qualité **0,82** (`frontend/lib/photo.ts:8-9`) ; une image déjà sous
  1200 px **et** sous 600 Ko part sans retraitement
  (`frontend/lib/photo.ts:22`).
- Stockage : `MenuItem.image_data`, colonne `LargeBinary`
  (`backend/app/modules/menu/models.py:60`), une ligne par plat.

**Estimation réaliste par photo** : à 1200 px de côté et qualité JPEG 0,82,
une photo de plat pèse typiquement de l'ordre de **150 à 300 Ko** (estimation
d'ingénierie fondée sur les ratios de compression JPEG usuels à cette
résolution/qualité — non mesurée dans cette session, à ne pas confondre avec
une valeur relevée). Le commentaire du code lui-même
(`backend/app/modules/menu/models.py:56`) évalue une carte de 40 plats à
« quelques mégaoctets », cohérent avec cette fourchette (40 × 150-300 Ko ≈ 6
à 12 Mo).

**Pire cas** : chaque photo au plafond serveur de 3 Mo (redimensionnement
échoué pour toutes les photos) → 40 × 3 Mo = **120 Mo/établissement**.

| Échelle | Réaliste (150-300 Ko/photo) | Pire cas (3 Mo/photo) |
|---|---|---|
| 1 établissement (40 plats) | 6-12 Mo | 120 Mo |
| **45 établissements** (cible Phase 22, `ROADMAP.md:225`) | 270-540 Mo | **5,4 Go** |
| 450 établissements (10× la cible, hors périmètre produit actuel) | 2,7-5,4 Go | 54 Go |

**Coût marginal** au tarif de dépassement Render (0,30 $/Go/mois), en
supposant par prudence que **la totalité** de ce volume est facturée en
dépassement (le forfait inclus par palier n'a pas pu être confirmé — §4.1,
donc ce calcul **majore** le coût réel) :

- 45 établissements, réaliste : < 1 Go → surcoût quasi nul (< 0,30 $/mois)
- 45 établissements, pire cas : 5,4 Go × 0,30 $ ≈ **1,62 $/mois** (≈ 4,8 TND)
- 450 établissements, pire cas : 54 Go × 0,30 $ ≈ **16,20 $/mois** (≈ 47,6 TND)

**Conclusion chiffrée** : à l'échelle visée par la roadmap (45
établissements), et même à dix fois cette échelle, le stockage des photos en
`LargeBinary` ne force **aucune** mise à niveau de palier Postgres — le
surcoût reste de l'ordre de quelques dinars à quelques dizaines de dinars par
mois, même dans l'hypothèse la plus pessimiste. Ceci confirme
quantitativement ce que `models.py:56` affirmait qualitativement (« le
volume reste dérisoire »). Le texte de `ROADMAP.md` (19bis.4) qui qualifie ce
choix de tenable à revoir « à l'échelle d'une chaîne » reste juste : le point
de bascule n'est pas 45 ni 450 établissements.

**Alternative mise en regard, sans recommandation de migrer maintenant**
(`ROADMAP.md` tranche déjà : à revoir à l'échelle d'une chaîne, pas
aujourd'hui) : **Cloudflare R2**, stockage objet compatible S3 — 0,015
$/Go/mois (≈ 0,044 TND) en stockage standard, palier gratuit de 10 Go +
1 million d'opérations classe A + 10 millions d'opérations classe B, **sans
frais de sortie (egress)** — un avantage structurel de R2 sur S3 pour un
usage où les photos sont resservies en boucle au client. Moins cher au Go que
le surcoût Postgres, mais ajoute un service externe, une clé API et un point
de défaillance supplémentaire pour un problème qui, chiffré ci-dessus, n'en
est pas un à l'échelle actuelle — YAGNI, comme déjà tranché.

### 4.5 — Conditionnel (uniquement si le déclencheur nommé se produit)

| Poste | Prix | Déclencheur exact (`ROADMAP.md`) |
|---|---|---|
| **Konnect réel** (paiement carte) | 1,3 % par transaction — cartes tunisiennes et e-dinar ; 2,9 % — cartes internationales ; 2 TND par virement bancaire ; **pas d'abonnement, pas de frais de mise en place, inscription gratuite** | Un pilote qui réclame le paiement carte (§ Sous condition). **F-5 doit être fermé avant** (`ROADMAP.md:126`), pas une question de coût |
| **Sentry** (collecte d'erreurs) | Palier gratuit (Developer) : 5 000 événements/mois, 1 utilisateur, rétention 30 jours — **probablement suffisant** à l'échelle d'un pilote ou de 45 établissements (erreurs applicatives, pas des événements business à fort volume). Palier payant (Team) : 26 $/mois (≈ 76 TND) pour 50 000 événements, si jamais dépassé | Un DSN créé (`ROADMAP.md` Phase 20 : « log drain de l'hébergeur, ou Sentry si un DSN existe ») |

Source : Konnect — recherche web datée 2026 (docs.konnect.network,
konnect.network, page officielle non consultable directement, §2). Sentry —
recherche web datée 2026, idem.

### 4.6 — Gratuit, confirmé

| Poste | Constat |
|---|---|
| **VAPID / Web Push** (`py_vapid`, `pywebpush`) | Confirmé gratuit — `py-vapid` est une dépendance de signature de `pywebpush` (recherche web confirmée), pas un service tiers facturé. La livraison passe par le point de terminaison Web Push standard exposé par chaque navigateur (Mozilla, Google, Microsoft) — protocole ouvert, **pas** Firebase Cloud Messaging, aucun compte ni facturation associés. |
| **Certificats TLS** | Gratuits et automatiques chez Render (Let's Encrypt, domaines personnalisés inclus) et chez Vercel (Let's Encrypt, certificats wildcard automatiques). Confirmé par recherche datée 2026. |
| **GitHub Actions** | Dépôt `benmesswass/Tawla` confirmé **public** (`"visibility": "public"`, API GitHub, 18/08/2026) → minutes **illimitées et gratuites** sur les runners standard GitHub-hébergés, quel que soit le volume des 3 niveaux de la pyramide CI (`ci.yml` + `nightly.yml`). Le palier payant (2 000 min/mois gratuites en privé, puis 0,006 $/min) ne s'applique qu'aux dépôts privés — sans objet ici. |
| **Vercel — volume** (bande passante, minutes de build) | Le palier Hobby (≈ 100 Go de bande passante/mois, largement plusieurs centaines de minutes de build selon les sources) couvrirait techniquement quelques dizaines d'établissements sans difficulté. **Ceci ne lève pas la réserve contractuelle du §4.1** — c'est une confirmation de volume, pas d'éligibilité. |
| **UptimeRobot — alerte qui réveille la nuit** | L'application mobile UptimeRobot (iOS/Android) est gratuite et propose des notifications push — de quoi répondre à l'exigence de `terrain/MISE_EN_LIGNE.md` Étape 6 (« alerte qui réveille la nuit ») **sans achat**, à condition que le téléphone de Wassim ait l'app installée avec les notifications actives (réglage à faire, pas un coût). SMS et appel vocal sont des options **payantes séparées** (crédits achetés à l'unité pour le SMS ; l'appel vocal n'est proposé par UptimeRobot sur **aucun** palier, gratuit ou payant) — inutiles si la notification push mobile suffit. Moniteur HTTP toutes les 5 minutes inclus sur le palier gratuit (jusqu'à 50 moniteurs). |

---

## 5. Ce que je ne recommande pas maintenant

- **Render — palier workspace « Pro » (≈ 25 $/utilisateur/mois selon la
  source trouvée, non confirmée avec précision)**, qui étend la fenêtre de
  restauration continue (*point-in-time recovery*) de 3 à 7 jours. Deux
  mécanismes distincts existent chez Render, et c'est probablement la source
  de la contradiction déjà notée dans `terrain/MISE_EN_LIGNE.md:35-36`
  (« les sources tierces se contredisent sur la profondeur exacte de
  restauration ») : (1) une **sauvegarde logique quotidienne**, retenue 7
  jours, **incluse sur n'importe quel palier Postgres payant** — c'est elle
  qui satisfait littéralement l'exigence posée par `terrain/MISE_EN_LIGNE.md`
  Étape 0 (« sauvegarde automatique quotidienne incluse dans le palier
  payé ») ; (2) la **restauration continue (PITR)**, minute par minute, dont
  la profondeur dépend du palier du **compte** (workspace), pas de
  l'instance Postgres — 3 jours sur workspace gratuit, 7 jours seulement sur
  workspace payant. Le besoin exprimé est le (1), déjà couvert sans surcoût.
  Ne pas payer pour le (2) tant qu'aucun incident réel ne justifie une
  granularité de restauration à la minute plutôt qu'au jour.
- **Cloudflare R2** (ou tout stockage objet) pour les photos de carte —
  chiffré en §4.4 : le surcoût actuel de `LargeBinary` en Postgres est de
  l'ordre du dinar par mois à l'échelle de la roadmap. `ROADMAP.md` (19bis.4)
  tranche déjà : à revoir « à l'échelle d'une chaîne », pas aujourd'hui.
- **Render Postgres au-delà de Basic-256mb** (ex. Basic-1GB, ≈ 20 $/mois) —
  rien dans le dépôt ni dans la roadmap n'indique un besoin de RAM ou de
  connexions simultanées au-delà de l'entrée de gamme à l'échelle actuelle
  (mono-instance, quelques dizaines d'établissements visés).
- **Sentry payant (Team, 26 $/mois)** — le palier gratuit (5 000
  événements/mois) n'a aucune raison d'être dépassé à l'échelle d'un pilote ;
  à réévaluer seulement si le volume réel après mise en place le dépasse.
- **UptimeRobot payant** — le palier gratuit (50 moniteurs, vérification
  5 min, alerte e-mail + app mobile push) couvre déjà les deux moniteurs
  demandés par `terrain/MISE_EN_LIGNE.md` Étape 6.
- **Konnect réel** — aucun pilote ne l'a demandé à ce jour ; le paiement
  carte reste simulé. Coût chiffré en §4.5 pour le jour où le déclencheur se
  produit, pas une dépense à engager maintenant.

---

## 6. Questions pour Wassim

Rien de ce qui suit n'est vérifiable depuis le dépôt — ce sont des faits du
monde réel, pas des choix de code.

1. **`tawla-backend.onrender.com` tourne-t-il déjà sur un palier payant ?**
   Depuis quelle date ? Si oui, c'est une dépense déjà engagée à faire
   apparaître dans le budget réel, indépendamment de cet audit.
2. **Un domaine (`tawla.tn` et/ou `tawla.com`) est-il déjà réservé ?**
   `ROADMAP.md:167` le liste comme non fait, mais seul Wassim peut le
   confirmer avec certitude.
3. **Le projet Vercel `tawla-eight.vercel.app` (trouvé via les métadonnées
   GitHub, §3) est-il sur un compte Hobby gratuit ou déjà sur un plan
   payant ?**
4. **Vercel Hobby vs Pro (§4.1) : plutôt que de trancher sur une lecture des
   CGU, vaut-il mieux écrire directement au support Vercel** — comme leurs
   propres conditions le suggèrent en cas de doute — **avant la Phase 20 ?**
   C'est la seule ligne de ce budget qui peut faire x2,4 sur le plancher
   mensuel (§1).
5. **Méthode de paiement envisagée pour les factures en USD** (Render,
   Vercel, éventuellement Sentry) : carte internationale adossée à un compte
   en devises personnel, ou un compte/statut professionnel ? Pertinent parce
   que le plafond « allocation technologique » particulier trouvé par
   recherche (≈ 1 000 DT/an, §2) est plus bas que le total annualisé du
   scénario prudent de cet audit (≈ 1 200 TND/an) — à vérifier auprès de la
   banque de Wassim, pas quelque chose que ce dépôt peut trancher.
6. **`tawla.tn` — prix réel** : aucune page de registrar tunisien n'a pu être
   consultée depuis cette session (§2). La seule vraie inconnue chiffrable
   de la Phase 20 reste à obtenir directement — `topnet.tn`, `ati.tn` ou
   `register.tn`.
