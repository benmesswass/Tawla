# Revue d'investissement — Tawla (13 août 2026)

Revue menée en position de jury d'investisseurs sur `main` au commit `6074e3a` :
code lu, suite de tests exécutée (121 tests verts, 61 s), surface publique de
l'API attaquée par exécution réelle, marché tunisien recoupé sur sources
publiques.

**Note d'investissement : 3,9/10** — pass aujourd'hui, revoir à 90 jours.
**Note d'artisanat technique : 7,5/10.** L'écart entre les deux _est_ le
diagnostic : le produit est bien construit, il n'a simplement rencontré
personne.

Version mise en page (grille de notation, registre de risques, calcul du
plafond de revenus) : voir l'Artifact envoyé à Wassim le 2026-08-13.

---

## 0. Addendum — après réponses du fondateur (même jour)

Quatre réponses ont été apportées après la rédaction de ce qui suit. La
première invalide en partie ma grille : **l'objectif est une entreprise
rentable et non diluée**, pas une levée de fonds. J'ai donc noté un dossier de
capital-risque qui n'a jamais prétendu en être un.

Sur la bonne grille — viabilité d'une activité rentable tenue par une à deux
personnes — **la note passe de 3,9 à 5,3**, et atteindrait ~6,5 dès la
priorité 0 close et les vingt entretiens faits. Les ~120 k DT de revenu
récurrent atteignable, disqualifiants pour un fonds, constituent _un bon
revenu_ pour deux personnes avec quelques centaines de dinars de coûts
mensuels. Les chiffres de la section 5 restent justes ; c'est leur conclusion
qui change de signe.

Ce qui ne change pas : les deux points bloquants (3.1 et section 4), et
l'absence de tout contact restaurateur. **Le facteur limitant n'est plus la
technique ni le marché, c'est l'accès au marché** — la seule dimension que le
code ne peut pas résoudre.

### Les concurrents sont une bonne nouvelle

Digital Menu, Scanny et Menu-QR étaient une découverte. Pour une levée,
c'était le constat le plus dur. Pour une activité rentable, il s'inverse :
**trois acteurs qui vendent cette catégorie prouvent que le marché tunisien
paie pour ça.** Plus besoin d'évangéliser une idée — le travail le plus
coûteux et le plus incertain qui existe. La question devient « quelle niche je
sers mieux qu'eux ».

### La conséquence qui inverse la recommandation de prix (point 8)

La recommandation « un seul prix aligné sur le marché » était juste pour une
trajectoire de levée. Pour une activité rentable en solo, c'est **l'inverse**
qu'il faut faire.

Digital Menu est ancré à 19–49 DT parce qu'il joue le volume en libre-service.
Un fondateur seul ne peut pas gagner une guerre de volume : chaque client
ajouté coûte du support, de la formation, du déplacement. La seule arithmétique
gagnante est inverse — **moins de clients, mieux payés, mieux servis** :

| Stratégie | Prix/mois | Clients | Revenu/an | Charge réelle |
|---|---:|---:|---:|---|
| Volume, aligné concurrence | 35 DT | 290 | ≈ 122 k DT | 290 restos à supporter et dépanner en pleine soirée. Impossible seul. |
| **Valeur, service inclus** | **120 DT** | **45** | **≈ 65 k DT** | 45 clients, chaque patron connu par son prénom. Tenable seul. |
| **Valeur, à deux** | **120 DT** | **90** | **≈ 130 k DT** | Même revenu que la ligne 1, trois fois moins de clients à porter. |

Ce qui justifie 120 DT face à un concurrent à 39 DT n'est pas une
fonctionnalité de plus — c'est ce qu'un éditeur en libre-service ne fera
jamais : **venir sur place.** Paramétrer la carte complète, imprimer et livrer
les QR sur supports propres, former le personnel pendant un service réel, être
joignable un vendredi soir.

Cible cohérente avec ce prix : **restaurants et brasseries de 6 tables et
plus** (Tunis, La Marsa, Sousse, Hammamet), pas les petits cafés. Ticket plus
élevé, plus de personnel, donc une commande perdue coûte réellement de
l'argent — et le tableau de bord « performance par serveur » y devient un
argument de direction. C'est le seul angle que les trois concurrents ne mettent
pas en avant.

### Matériel existant : bonne réponse, avec un piège

S'appuyer sur les téléphones du personnel et un écran déjà présent lève le
frein d'installation le plus courant. Deux réserves à tester dès le premier
pilote, invisibles dans le code :

- **Le téléphone personnel du serveur est un sujet social, pas technique** :
  batterie, forfait data, et l'idée de travailler sur son propre appareil —
  couplée à des statistiques nominatives servant à calculer des primes. Le
  personnel de salle est le premier saboteur potentiel de cet outil. À aborder
  de front avec le patron avant l'installation.
- **L'écran cuisine a été dessiné pour un grand écran** (mode sombre, cartes
  larges, badge « il y a X min »). S'il est affiché sur un téléphone posé sur
  une étagère, le vérifier en vrai à 360 px avant de promettre quoi que ce soit.

---

## 1. Grille de notation pondérée

| Dimension | Poids | Note | Ce qui fixe la note |
|---|---:|---:|---|
| Différenciation & défense | 20 % | 2,0 | Aucune fonctionnalité absente chez les concurrents tunisiens ; code reproductible en une semaine avec un assistant IA |
| Besoin marché réel | 15 % | 6,0 | La douleur « commande perdue » est vraie ; qu'elle vaille un abonnement reste à prouver |
| Marché & modèle économique | 15 % | 3,5 | Prix ancré à 19–49 DT/mois, plafond structurel sur la Tunisie seule |
| Traction & preuve | 15 % | 0,5 | Pas déployé, pas de pilote, pas d'entretien client tracé |
| Équipe & exécution | 15 % | 6,0 | Vélocité et discipline remarquables ; fondateur solo, pas de profil salle ni de vente |
| Qualité technique | 10 % | 7,5 | Architecture tenue, transitions verrouillées, isolation multi-tenant testée |
| Prêt pour la production | 5 % | 3,0 | Pas de sauvegardes, pas de supervision, `create_all()`, mono-instance, API publique ouverte |
| Conformité & risque légal | 5 % | 4,0 | Téléphones collectés sans déclaration INPDP, et actuellement exposés |
| **Total pondéré** | **100 %** | **3,9** | Défense et preuve, 35 % de poids cumulé, tirent tout vers le bas |

## 2. Ce qui est réellement solide

- **L'isolation multi-tenant tient.** Vérifiée par attaque : manager A → stats
  de B = `403`, manager A → confirmation d'une commande de B = `404`.
- **Le cœur métier est verrouillé au bon endroit** : `ALLOWED_TRANSITIONS`
  côté service, prix figé sur `OrderItem` au moment T.
- **121 tests en 61 s sur les vrais risques** (cycle de vie, étape non
  contournable, plat indisponible, isolation, unicité des tokens QR).
- **Le pool partagé + claim nominatif** est un vrai parti pris d'organisation
  de salle, et l'angle le plus vendable auprès d'un patron : savoir qui
  travaille, et sur quoi asseoir une prime.
- **Les renoncements sont tracés** dans `ROADMAP.md` (panier multi-appareils,
  imprimante, Next.js 15). Un fondateur qui sait écrire ses « non » vaut mieux
  qu'un fondateur qui a tout coché.

## 3. Les cinq peurs, par gravité

### 3.1 Le produit n'est pas installable par un client (bloquant)

Il n'existe **aucun endpoint pour créer un compte serveur ou cuisine**.
`/auth/register` crée le restaurant + son manager, rien d'autre ; les seuls
comptes serveur/cuisine viennent de `scripts/seed_demo.py`. Un restaurateur
onboardé en self-service ne peut donc donner accès ni à ses serveurs ni à son
écran cuisine — soit les deux tiers de la valeur du produit. **Aucun pilote
n'est possible en l'état.** C'est aussi le symptôme du risque 3.2 : ce trou
n'aurait pas survécu quinze minutes devant un vrai utilisateur.

### 3.2 Zéro contact marché, features bâties sur un client imaginé

`git log` : 36 commits, 10→12 août 2026, un auteur. Onze phases, identité de
marque, mode Ramadan, niveau de piment, anecdotes culturelles, carte à
tamponner, partage social — tout avant qu'un restaurateur n'ouvre l'app. Le
risque n'est pas la qualité, c'est le mauvais cahier des charges très bien
exécuté. À l'inverse, la seule fonctionnalité qui justifie économiquement un
abonnement dans cette catégorie — **la vente incitative** (suggestions,
formules, boisson associée) — n'existe pas.

### 3.3 Segment déjà occupé, déjà moins cher, et le code n'est plus un moat

- **Digital Menu** : 19 DT (light) / 29 DT (serveur) / 39 DT (commande à
  table) / 49 DT (premium) par mois, avec écran cuisine, priorisation, zones,
  **postes de production** (que Tawla n'a pas), fidélité, stats personnel.
- **Scanny** : + caisse connectée. **Menu-QR** : entrée de gamme.

Comparé fonctionnalité par fonctionnalité, Tawla n'a rien de plus. Ils sont
tunisiens aussi : Ramadan et derja ne sont pas un avantage durable. Et comme
ce produit a été écrit en trois jours avec un assistant IA, n'importe quel
concurrent peut répliquer le périmètre en une semaine. **En 2026 cette couche
logicielle n'est pas un actif défendable — seule la distribution l'est.**

### 3.4 Le ROI vendu est le plus difficile à vendre

Le client commande, puis le serveur se déplace quand même confirmer : le
trajet est conservé, donc l'économie de main-d'œuvre ≈ 0. Reste « zéro
commande perdue » et « visibilité manager » — réels mais invérifiables avant
installation. Pendant ce temps, ce qui obsède le patron (stock, coulage,
caisse) n'est pas adressé : **aucune intégration caisse**, donc double saisie
quotidienne. C'est la friction qui fait désinstaller au bout de trois semaines.

### 3.5 Tarification décidée avant le premier client

Trois paliers arbitrés et à moitié codés, aucun montant fixé, aucun client
payant. Optimisation prématurée. En revanche, **abandonner la commission au
profit de l'abonnement est la bonne décision** : le paiement à la livraison
reste ~68 % des commandes e-commerce tunisiennes en 2025 (82 % en 2022) — sur
des tickets de 15–40 DT réglés en espèces, une commission n'aurait jamais
produit de revenu.

## 4. Sept constats vérifiés par exécution (pas par lecture)

Scénario joué sur le harnais de test du projet, deux restaurants concurrents,
aucun token :

```
1. GET /api/v1/orders/1 (anonyme)            -> 200, téléphone client +216…, montant, table
   IDs séquentiels : énumération 1..N, tous restos confondus
2. POST /api/v1/orders/1/pay/card (anonyme)  -> 200, payment_status = paid (sans un dinar)
3. POST /api/v1/orders, table_id deviné      -> 201, commande de 1250 TND au pool serveurs
   (le qr_token protège la lecture du menu, pas l'écriture d'une commande)
4. POST /api/v1/loyalty/lookup (anonyme)     -> 200, visites + date de naissance
5. WS /ws/staff/{id} sans token              -> acceptée, flux temps réel des commandes
6. Manager A -> stats/commande de B          -> 403 / 404  (correct — contrôle)
7. POST /api/v1/restaurants (anonyme)        -> 201 (endpoint legacy)
```

Pourquoi ça compte au-delà de la technique :

- **Le constat 3 est le pire opérationnellement** : un plaisantin injecte des
  commandes dans le service en cours → nourriture réellement préparée,
  personnel mobilisé, en plein rush. Le premier resto à qui ça arrive résilie
  le jour même. Le `qr_token` existe et est bien conçu, il n'est simplement
  pas exigé à la création de commande.
- **Le constat 1 est le plus risqué juridiquement** : un numéro de téléphone
  est une donnée personnelle au sens de la loi organique 2004-63, dont
  l'article 7 impose une **déclaration préalable à l'INPDP**. Ici les numéros
  sont traités sans déclaration et lisibles par un anonyme sur une URL à ID
  incrémental.
- **Le constat 2 est un trou d'intégrité dès maintenant** : un client marque
  sa commande « payée » sans rien régler, et le serveur voit « payé ». Le jour
  où Konnect est branché, la même route devient une fraude au paiement.

Bon point : tout ce qui est derrière un JWT est correctement cloisonné
(constat 6). Le problème est concentré sur la surface publique du parcours
client.

## 5. Le plafond de revenus (hypothèses explicites)

| Étape | Valeur | Hypothèse |
|---|---:|---|
| Cafés en Tunisie | ≈ 40 000 | Estimation de presse 2025, hors restaurants, non officielle |
| Filtre d'adressabilité | × 6 % | Wi-Fi fiable, clientèle smartphone, volume, grandes villes / zones touristiques |
| Établissements adressables | ≈ 2 400 | Le vrai marché, pas le TAM de présentation |
| Revenu annuel par client | ≈ 420 DT | 35 DT/mois — prix ancré par la concurrence, pas par choix |
| Marché total si on prend tout | ≈ 1,0 M DT/an | Scénario impossible : trois concurrents installés |
| Part réaliste à 3 ans | × 12 % | ≈ 290 établissements — déjà une très belle exécution commerciale |
| **Revenu récurrent atteignable** | **≈ 120 k DT/an** | ~36 k€, contre 5–10 M€ attendus au bout d'une thèse de fonds |

Conclusion : **ce n'est pas un dossier de capital-risque sur la Tunisie
seule** — mais c'est une entreprise saine et rentable à deux personnes, qu'il
ne faut surtout pas diluer. Les deux jeux demandent des décisions opposées ;
il faut choisir consciemment. Le contexte renforce ce point : premier semestre
2026 quasi vide en opérations de capital en Tunisie, et les tickets locaux
(216 Capital 100–250 k$, Anava/Flat6Labs ~330 k DT en moyenne) iront aux
dossiers qui montrent une preuve.

## 6. Recommandations

### Priorité 0 — cette semaine, avant tout contact client

1. **Création des comptes serveur/cuisine par le manager** (endpoint + écran).
   Sans ça, il n'y a littéralement rien à vendre. Une demi-journée.
2. **Lier le parcours client à un jeton** : `order_token` opaque renvoyé à la
   création, exigé sur `GET /orders/{id}`, `pay/card`, `pay/cash`,
   `push-subscription` ; exiger le `qr_token` de la table à la création ;
   retirer `loyalty_phone` de `OrderOut`.
3. **Authentifier `/ws/staff` et `/ws/kitchen`** (JWT), supprimer
   `POST /api/v1/restaurants` devenu inutile depuis `/auth/register`.
4. **Sauvegardes Postgres, Alembic actif, supervision `/health`** — déjà
   identifiés dans la roadmap. Aucune donnée réelle avant.
5. **Déclaration INPDP** du traitement des numéros de fidélité.

### Priorité 1 — 30 jours, fabriquer la preuve

6. **Trois pilotes réels** (café de quartier, resto centre-ville, zone
   touristique), gratuits, engagement écrit de 4 semaines + droit de citer.
7. **Trois métriques avant/après, et rien d'autre** : commandes perdues par
   service, délai commande → cuisine, panier moyen.
8. **Un seul prix** pour les dix premiers clients.
9. **Construire la vente incitative** — le seul levier qui transforme
   l'argumentaire en chiffre vérifiable, donc le seul qui autorise > 49 DT.
10. **Vingt entretiens de restaurateurs**, écrits, sans montrer l'app avant la
    fin : « qu'est-ce qui te fait perdre de l'argent chaque semaine ? »

### Priorité 2 — après les pilotes, choisir le jeu

11. **Descendre dans la caisse** (stock, coulage) — ARPU et rétention
    supérieurs, chantier lourd, concurrence installée.
12. **Monter en régional** (Algérie, Maroc, Libye) — seul chemin compatible
    avec une levée.
13. **Assumer l'entreprise rentable à deux** — le plus probable et le plus
    rationnel ici ; alors on ne lève pas, on vend.
14. **Trouver un associé « salle »** — aujourd'hui le maillon le plus faible
    du dossier, plus que la technique.

## 7. Ce qui ferait passer la note à 7 (revue à 90 jours)

- Trois pilotes actifs depuis 4 semaines, dont **deux qui acceptent de payer**.
- Le triplet de métriques avant/après sur au moins un établissement.
- Priorité 0 close, avec **tests dédiés** sur les correctifs de sécurité.
- Une réponse nette à « pourquoi toi et pas Digital Menu à 39 DT », formulée
  dans les mots d'un restaurateur pilote.
- Un choix assumé parmi les trois chemins. Le mauvais choix explicite vaut
  mieux que l'indécision : il est corrigeable.

## 8. Questions ouvertes (non déductibles du dépôt)

1. Combien de restaurateurs rencontrés réellement, et qu'ont-ils dit du prix ?
2. Objectif : lever des fonds, ou entreprise rentable contrôlée ? (décisions
   opposées sur prix, périmètre, vitesse)
3. Qui paie le matériel — tablette serveur, écran cuisine, Wi-Fi de salle ?
4. Digital Menu / Scanny / Menu-QR étaient-ils connus avant cette revue ?
5. Que se passe-t-il quand le Wi-Fi tombe en plein service ? (repli papier
   documenté pour le pilote ?)
6. Combien de temps de trésorerie sans revenu ?
7. Le serveur qui perd la main sur la prise de commande — lui en as-tu parlé ?
   Les stats par serveur sont vendeuses pour le patron et potentiellement
   explosives en salle.

## Sources

- Concurrence : [Digital Menu tarifs](https://digitalmenu.tn/prix-tarif-menu-digital-qr-code)
  et [fonctionnalités](https://digitalmenu.tn/fonctionnalites-menu-digital-qr-code),
  [Scanny](https://scanny.tn/), [Menu-QR](https://www.menu-qr.tn/),
  [panorama Afrique du Nord 2026](https://www.magstartup.com/menu-qr-restaurant-afrique-du-nord-top-10-solutions-2026/)
- Parc de cafés : [Tuniscope](https://www.tuniscope.com/article/357077/actualites/societe/tn-124608121)
  (estimation de presse, non INS)
- Paiements : [Challenges TN](https://www.challenges.tn/economie/paiements-numeriques-en-tunisie-les-chiffres-dun-trimestre-record/),
  [Managers](https://managers.tn/2025/02/25/paiements-en-tunisie-en-moyenne-le-cash-a-gagne-du-terrain/),
  [web6](https://web6.tn/blog/ecommerce-paiement-livraison-tunisie/)
- Données personnelles : [loi 2004-63](https://www.ins.tn/sites/default/files/2020-04/Loi%2063-2004%20Fr.pdf),
  [INPDP](https://www.inpdp.tn/Formulaires.html)
- Financement : [Startup Act](https://startup.gov.tn/en/startup_act/discover),
  [Anava Seed Fund](https://flat6labs.com/fr/funds/anava-seed-fund/),
  [216 Capital](https://superscout.co/investor/216-capital-ventures),
  [LaunchBase Africa — S1 2026](https://launchbaseafrica.com/2026/07/29/near-zero-equity-deals-in-h1-what-happened-to-tunisias-startup-ecosystem/)

Deux sources n'ont pas pu être ouvertes directement depuis l'environnement de
revue (Mag Startup, LaunchBase Africa) : citées d'après résumés de recherche,
à relire avant reprise dans un document adressé à des tiers.
