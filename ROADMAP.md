# Tawla — Roadmap

Fichier unique de pilotage du projet. Prendre la première tâche non cochée en
partant du haut, dans l'ordre des phases. Une tâche cochée `[x]` doit mentionner
la PR qui l'a livrée. Les tâches marquées 🧑 demandent une décision, un compte
réel ou une présence physique de Wassim — elles ne sont jamais faisables en
autonomie.

Refondue le 2026-08-15 après l'audit final ([`AUDIT_FINAL.md`](./AUDIT_FINAL.md)).
Les phases 12 à 18 sont closes ; ce qu'elles ont livré est résumé en fin de
fichier. Documents qui fondent celle-ci :

- [`AUDIT_FINAL.md`](./AUDIT_FINAL.md) — audit du 2026-08-15 : code exécuté,
  42 fonctionnalités notées, trois défauts à fermer, note recalculée à 5,6.
- [`REVUE_INVESTISSEURS.md`](./REVUE_INVESTISSEURS.md) — revue d'investissement
  du 2026-08-13, grille de notation et plafond de revenus.
- [`PREMIERES_VENTES.md`](./PREMIERES_VENTES.md) — les dix recommandations pour
  décrocher les deux premiers clients payants.
- [`ROADMAP_ARCHIVE.md`](./ROADMAP_ARCHIVE.md) — phases 0 à 11. Lecture seule.

## Objectif

**Deux restaurants qui paient, avant Ramadan 2027.**

Ce n'est plus « passer de 5,3 à 8/10 au prochain jury ». La note suit, elle ne
se pilote pas : deux lignes valant 40 % de la grille ne bougeront qu'avec des
chiffres relevés dans un vrai établissement, et l'audit a montré qu'en visant la
note directement on finit par se noter soi-même sur ses intentions.

L'objectif ci-dessus, lui, n'est pas interprétable : soit deux patrons ont
viré 120 DT, soit non.

## La règle qui structure toute cette roadmap

**Une seule phase de code, au début, et plus rien ensuite avant le premier
pilote.**

L'audit est net : le produit est noté 7,6/10 sur ses fonctionnalités livrées et
2,0/10 sur l'accès au marché. Il ne manque pas de fonctionnalité — il manque un
restaurateur. La Phase 19 ferme les trois défauts qui coûteraient un client, la
Phase 20 met en ligne, et **tout ce qui suit passe par la porte d'un
restaurant**.

Toute tâche de code proposée après la Phase 20 doit d'abord répondre à :
« quel restaurateur l'a demandée, et lequel refuse de payer sans elle ? ».
Sans réponse nommée, elle va en § « Sous condition ».

## Le calendrier, à rebours de Ramadan

Ramadan tombe en février-mars 2027. L'iftar est le service le plus tendu de
l'année, le mode ramadan et la pré-commande existent déjà, et c'est le seul
moment où la démonstration se fait toute seule. Rater cette fenêtre coûte un an.

| Quand | Phases | Ce qui doit être vrai à la fin |
|---|---|---|
| **15 – 22 août 2026** | 19, 20 | Le produit tourne en ligne, sauvegardé, sur un vrai domaine |
| **Fin août – septembre** | 21, 22 | 20 entretiens faits, prix tranché, roadmap coupée |
| **Octobre – novembre** | 23 | 3 pilotes installés, 4 semaines chacun, chiffres relevés |
| **Décembre – janvier 2027** | 24 | 2 pilotes passés au payant |
| **Février – mars 2027** | — | Ramadan : vendre avec des chiffres en main |

Six semaines pour les phases 19 à 22, dont une seule est du code. Le calendrier
n'a plus de marge : c'est ce qui justifie de refuser tout ajout fonctionnel.

## Où en est la note, et ce qui la déplace

Recalculée sur l'état constaté par l'audit, pas sur le travail fourni.

| Dimension | Poids | Actuelle | Cible | Ce qui la déplace | Phase |
|---|---:|---:|---:|---|---|
| Accès au marché & vente | 20 % | 2,0 | 7,5 | 20 entretiens menés, 3 pilotes installés, 2 clients payants | 21, 23, 24 |
| Besoin marché prouvé | 20 % | 5,5 | 8,5 | Les trois métriques relevées **avant** et **après** chez un pilote réel | 23 |
| Viabilité économique | 20 % | 5,0 | 8,0 | Un prix tranché, puis réellement payé par deux établissements | 22, 24 |
| Prêt à vendre (installable, sûr) | 15 % | 7,5 | 9,0 | Les trois défauts fermés, la production en ligne avec sauvegardes restaurées | 19, 20 |
| Exécution technique | 15 % | 8,5 | 9,0 | T1, T2, T3 corrigés **avec les tests qui les prouvent** | 19 |
| Différenciation sur une niche | 10 % | 6,5 | 7,5 | Un chiffre venu d'un vrai pilote, cité avec le nom de l'établissement | 23 |
| **Note pondérée** | **100 %** | **5,6** | **8,2** | | |

Recalculer cette colonne à la clôture de chaque phase — **sur ce qui est
constaté, jamais sur ce qui est préparé.** C'est la dérive que l'audit a
relevée : « besoin marché prouvé » avait été monté à 7,0 sans qu'aucun chiffre
n'ait été relevé nulle part.

---

## Phase 19 — Fermer les trois défauts qui coûteraient un client

**Une journée. La dernière phase de code avant la porte d'un restaurant.**

Ces trois défauts ont en commun de ne se manifester qu'en conditions réelles :
aucun n'est visible dans les 280 tests actuels, et chacun frappe un moment où le
client regarde. Rien d'autre dans le dépôt n'a besoin d'être touché.

Convention de la Phase 12.2, reconduite ici : **écrire d'abord le test qui
échoue**, puis le correctif. Un correctif sans test qui le prouve ne compte pas
comme livré.

**19.1 — T1 : fermer `POST /loyalty/lookup`** (dernière route publique qui
accepte un `restaurant_id` incrémental et qui **écrit** en base)

- [ ] `LoyaltyLookup` prend le `qr_token` de la table au lieu de `restaurant_id` — le restaurant en est déduit, exactement comme `OrderCreate` depuis la Phase 12.2
- [ ] La route ne crée plus la fiche : `404 LOYALTY_MEMBER_NOT_FOUND` si elle n'existe pas. `create_order` la crée déjà au bon moment, et une route publique qui écrit des numéros de téléphone de tiers n'a aucune finalité au sens de la loi 2004-63
- [ ] Côté client : afficher « première visite » sur ce 404 au lieu de lire `order_count: 0` — le comportement visible ne change pas pour le client attablé
- [ ] Test `test_lookup_fidelite_refuse_sans_qr_token` : sans le token de la table, la réponse est identique pour un numéro client et un numéro inconnu
- [ ] Test `test_lookup_fidelite_ne_cree_jamais_de_fiche` : aucune ligne `LoyaltyMember` créée par cette route, quel que soit le numéro
- [ ] Relire `frontend/lib/i18n/privacy.ts` (fr **et** ar) : le texte promet que le numéro n'est jamais partagé — il doit redevenir vrai, et le rester

**Résidu assumé** : avec le `qr_token` en main, un client attablé peut vérifier
si un numéro est connu de **ce** restaurant. C'est le même niveau d'accès que
passer commande, et le prix à payer pour une carte de fidélité sans compte. À
noter tel quel dans la PR.

**19.2 — T2 : rendre la création de commande idempotente** (aujourd'hui, une
réponse perdue en plein service produit deux commandes et deux préparations)

- [ ] `Order.client_order_id` (`String(64)`, unique, indexé, nullable) + migration Alembic + `model_registry.py`
- [ ] `OrderCreate.client_order_id` : identifiant généré par le navigateur **au moment où le panier est composé**, et conservé tel quel dans la charge utile mise en file hors ligne — un identifiant régénéré au rejeu ne servirait à rien
- [ ] `create_order` renvoie la commande existante au lieu d'en créer une seconde, avec son `public_token` d'origine : le téléphone du client doit retomber sur **sa** commande, pas sur une commande qu'il ne pourra plus suivre
- [ ] Aucun second broadcast WebSocket sur un rejeu — sinon la commande réapparaît sur l'écran serveur alors qu'elle est déjà prise en charge
- [ ] Test `test_deux_envois_du_meme_panier_ne_font_quune_commande` : deux `POST /orders` identiques → une commande, un événement, le même `public_token`
- [ ] Test : deux paniers différents avec deux identifiants différents restent deux commandes (le filet ne doit pas avaler une vraie deuxième tournée)

**19.3 — T3 : le limiteur de débit derrière le proxy de l'hébergeur**
(aujourd'hui `request.client.host` : en production, tout le parc partage un seul
compteur de 20 requêtes par minute)

- [ ] Clé du limiteur sur l'IP réelle du client, pas sur le pair TCP — en ne faisant confiance à `X-Forwarded-For` que depuis le proxy déclaré, jamais depuis n'importe qui
- [ ] `FORWARDED_ALLOW_IPS` documenté dans `backend/.env.example` avec la raison, et renseigné au déploiement (Phase 20)
- [ ] Test : deux requêtes portant des `X-Forwarded-For` différents ne partagent pas le compteur ; un en-tête envoyé par un client non fiable est ignoré
- [ ] Vérifier sur staging derrière le vrai proxy avant la bascule 🧑 — c'est le seul des trois défauts qui ne se constate qu'en production

**19.4 — Les trois défauts mineurs, dans la même passe** (aucun ne mérite une
PR à lui seul)

- [ ] `POST /orders` passe sous `rate_limit`, comme `POST /waiter-calls` : même niveau d'accès, même nuisance possible, sauf que celle-ci mobilise la cuisine
- [ ] `table_label` échappé dans les deux fenêtres d'impression (`app/staff/page.tsx`, `app/kitchen/page.tsx`) — les notes du client et le nom du serveur le sont déjà, dans la même fonction
- [ ] `<html lang>` suit la langue choisie par le client : le parcours bascule en arabe, l'attribut reste `fr`, et un lecteur d'écran prononce l'arabe avec les règles du français

**19.5 — Borner les commandes actives dans le temps** (défaut rendu visible par
le plan de salle : des tables restaient rouges le lendemain, avec « +1 h »)

- [ ] Les écrans de service ne montrent que les commandes du service en cours — filtrage dans `list_active_orders` et `list_pending_calls`, pas dans le composant : deux écrans qui filtrent différemment finiraient par se contredire
- [ ] **Ne pas** changer le statut de ces commandes : elles restent « perdues » pour `stats/service.py::_lost_orders`, et c'est ce chiffre qui porte l'argument de vente. On cesse de les afficher, on ne les efface pas
- [ ] Seuil à proposer et à confronter au premier pilote (comme `ABANDONED_PENDING_AFTER`), documenté au même endroit

---

## Phase 20 — Mettre en ligne, pour de vrai

**Bloquant avant la première commande d'un vrai client.** Un pilote qui perd son
service du soir ne revient pas, et il le racontera aux autres patrons du
quartier — c'est le seul incident dont le coût dépasse celui du produit.

Tout ici demande un compte ou une carte bancaire de Wassim.

- [ ] Choisir et provisionner l'hébergement 🧑 — backend dockerisé sur Railway ou Render (WebSocket natif + Postgres managé), frontend sur Vercel. Contrainte à respecter : **une seule instance backend** (gestionnaire WebSocket et limiteur de débit en mémoire)
- [ ] Réserver le domaine 🧑 (`tawla.tn` en priorité, `.com` en secours)
- [ ] Générer les vraies clés en variables d'environnement 🧑 : `JWT_SECRET`, `FRONTEND_ORIGIN` sur l'origine exacte de prod, paire VAPID, `FORWARDED_ALLOW_IPS` (cf. 19.3)
- [ ] Activer les sauvegardes automatiques du Postgres managé 🧑
- [ ] **Restaurer une sauvegarde une fois, sur une base jetable** 🧑 — une sauvegarde jamais restaurée n'est pas une sauvegarde. C'est la seule ligne de cette phase qu'on sera tenté de sauter, et la seule qui prouve les autres
- [ ] Brancher le monitoring externe sur `/health` 🧑 (UptimeRobot gratuit) — la sonde interroge déjà la base et renvoie 503 si elle est injoignable
- [ ] Collecte des erreurs 🧑 — log drain de l'hébergeur, ou Sentry si un DSN existe. Les logs sortent déjà en JSON sur stdout : ne rien coder avant d'avoir la destination
- [ ] Rejouer le parcours complet sur staging — client, serveur, cuisine, manager — puis bascule finale 🧑
- [ ] Déclaration du traitement des numéros de fidélité auprès de l'INPDP 🧑 (`inpdp.tn`) — avant le premier client réel, pas après. Le produit est conforme depuis la Phase 16 ; il manque le dépôt

**Critère de sortie de phase** : une commande passée depuis un téléphone sur le
domaine réel, vue sur l'écran cuisine, avec une sauvegarde restaurée la veille.

---

## Phase 21 — Vingt entretiens de restaurateurs 🧑

**La ligne la plus lourde de la grille (20 %), notée 2,0, et la seule qui
conditionne toutes les suivantes.** Elle n'attend rien : elle peut démarrer le
jour où la Phase 19 est en revue, sans attendre la mise en ligne.

Le matériel existe depuis la Phase 13 (`terrain/GUIDE_ENTRETIEN.md`,
`terrain/ENTRETIENS.md`) et n'a jamais servi : le tableau de dépouillement porte
vingt lignes vides.

- [ ] Mener les 20 entretiens 🧑 — restaurants et brasseries de **6 tables et plus** (Tunis, La Marsa, Sousse, Hammamet), pas les petits cafés. Ne jamais montrer l'application avant la fin
- [ ] Remplir `terrain/ENTRETIENS.md` sur place ou juste après 🧑 — une ligne par établissement, et les verbatims mot pour mot, surtout les refus
- [ ] Poser la question de prix franchement, après avoir décrit le bénéfice et jamais la fonctionnalité 🧑
- [ ] Repérer les trois profils de pilote au passage 🧑 : café de quartier, restaurant de centre-ville, zone touristique. Chercher celui dont les autres patrons parlent, pas le plus accueillant
- [ ] Écrire la synthèse 🧑 : les trois douleurs les plus citées, le prix médian accepté, l'écart entre le prix spontané et la réaction à 120 DT

**21.1 — La coupe** (ce qui rend cette phase utile au produit, et pas seulement
au commercial)

La synthèse doit produire un **retrait**, pas un ajout. Une fonctionnalité
qu'aucun des vingt n'a mentionnée spontanément est candidate à la suppression —
pas au maintien « au cas où ».

- [ ] Trancher le sort des trois candidats déjà identifiés par l'audit 🧑 : partage d'addition (noté 6,0), mode café (6,5), célébration et carte à partager (4,0). Les retirer coûte moins cher que les maintenir dans chaque écran, chaque traduction et chaque test
- [ ] Écrire la coupe dans cette roadmap avec la raison, même si la décision est « on garde »
- [ ] Si l'addition par table remonte spontanément chez plusieurs patrons, c'est la **seule** fonctionnalité qui remonte en Phase 23 ; sinon elle reste en § « Sous condition »

---

## Phase 22 — Un seul prix 🧑

Décision qui n'attend aucune donnée nouvelle : elle est écrite dans deux
documents et attendue par une constante `null` dans le code.

- [ ] Fixer le prix unique 🧑 — proposition tenue depuis la revue : **120 DT/mois, service d'installation inclus**, cible 45 établissements. 45 × 120 DT ≈ 65 k DT/an tenable seul, contre 290 clients à 35 DT pour un revenu comparable et une charge de support intenable
- [ ] Renseigner `PRICE_MONTHLY_DT` dans `frontend/lib/offer.ts` — la page publique affiche alors le montant sans autre changement de code
- [ ] `Restaurant.pilot_ends_on` + bandeau « pilote gratuit jusqu'au JJ/MM » sur le dashboard + migration. Rend l'échéance explicite au lieu d'une conversation gênante à avoir. **Ne pas coder avant que le prix soit tranché** : un bandeau qui n'annonce aucune suite ne sert à rien
- [ ] Facturation : facture mensuelle **manuelle** pour les dix premiers clients (un virement ou un chèque). N'automatiser qu'au-delà — YAGNI strict
- [ ] Ne pas activer la facturation avant la fin de la phase pilote gratuite

**Le prix ne bouge jamais. Le périmètre, oui.** La première remise tue le
positionnement définitivement, et elle se saura — dans un milieu où tout le
monde se parle. Face à une négociation : donner du temps (quatre semaines
gratuites), jamais des dinars.

---

## Phase 23 — Les trois pilotes

C'est ici que la note « besoin marché prouvé » se gagne, et nulle part ailleurs.

**23.1 — Avant d'installer quoi que ce soit** 🧑

- [ ] Disqualifier à la porte 🧑 : pas de Wi-Fi utilisable ou de réseau à toutes les tables → ne pas installer, même s'il insiste. Moins de six tables → la douleur est trop faible pour 120 DT. Une terrasse est le signal positif le plus fort
- [ ] Accord écrit d'une page par pilote 🧑 : quatre semaines d'usage **effectif en service**, droit de citer le nom, droit de publier les chiffres mesurés, et en échange installation, formation, chevalets et support pendant le service. Un pilote qui refuse le droit de citation est un client gratuit, pas un pilote
- [ ] **Relever la semaine de référence à la main, avant activation** 🧑 : commandes perdues par service et panier moyen, comptés sur place pendant quatre soirs. Sans cet « avant », la preuve d'après ne vaut rien — et c'est le seul travail de cette roadmap qui devient impossible à rattraper une fois l'outil installé
- [ ] Arriver avec **sa** carte déjà chargée 🧑 (`setup_restaurant.py` + import CSV) et lui faire scanner son propre QR. « Voilà votre carte, elle tourne » ne se rattrape par aucun argument

**23.2 — L'audit d'avant devient un écran** (à coder **quand le premier relevé
existe**, pas avant : un écran qui n'a rien à afficher n'est pas une
préparation)

- [ ] `Restaurant.baseline_lost_orders_per_day`, `baseline_avg_basket`, `baseline_measured_on` + migration + `model_registry.py`
- [ ] Saisie depuis le dashboard manager, avec la date du relevé — rien d'affiché tant que ce n'est pas saisi
- [ ] `/dashboard/preuve` affiche « avant Tawla » en face de « mesuré » quand le relevé existe. C'est **la** capture d'écran qui vend le passage au payant
- [ ] Ne jamais inventer ni pré-remplir ces valeurs : un chiffre « avant » inventé rend toute la démonstration mensongère, et la mesure est la seule chose que Tawla a à vendre

**23.3 — Les quatre semaines** 🧑

- [ ] Former l'équipe sur place, dix minutes pendant un service creux (`terrain/FORMATION_10MIN.md`) 🧑
- [ ] **Convaincre les serveurs avant le patron** 🧑 — « tu ne prends plus les commandes, tu les confirmes ». Traiter de front le sujet du téléphone personnel (batterie, forfait), et proposer au patron de fournir un téléphone de salle. Le personnel de salle est le premier saboteur possible de cet outil
- [ ] Répéter le repli papier **avant** d'en avoir besoin, pas le soir où le réseau tombe 🧑
- [ ] Tenir `terrain/PILOTES.md` le soir même de chaque service observé 🧑 : incidents, verbatims, ce qui a été contourné ou jamais utilisé
- [ ] Relever les trois métriques chaque semaine sur `/dashboard/preuve` 🧑
- [ ] Confronter les seuils codés au réel 🧑 : `ABANDONED_PENDING_AFTER` (10 min) et le seuil de fin de service de 19.5 sont des propositions, pas des vérités
- [ ] Confronter le plan de salle aux entretiens 🧑 : les zones suffisaient-elles, ou le plan dessiné change-t-il vraiment la conversation ?

**23.4 — Ce qui sort des pilotes**

- [ ] Remplir `PILOT_RESULTS` dans `frontend/lib/offer.ts` avec des chiffres réellement relevés chez un établissement qui a donné son accord écrit pour être cité
- [ ] Écrire la réponse à « pourquoi toi et pas Digital Menu à 39 DT » **dans les mots d'un patron pilote**, pas dans les nôtres

---

## Phase 24 — Les deux clients payants

Le passage de « produit » à « entreprise ». C'est la seule phase dont la
réussite ne dépend d'aucune ligne de code.

- [ ] Deux des trois pilotes passent à l'abonnement payant 🧑
- [ ] Première facture émise et encaissée 🧑
- [ ] Mesurer les deux chiffres qui décident de la suite 🧑 : durée réelle d'une installation, et minutes de support par client et par semaine. Le modèle à 45 clients suppose une heure et quelques minutes ; si l'installation prend une demi-journée, la cible est 20 clients, pas 45 — et il vaut mieux l'apprendre au deuxième client qu'au vingtième
- [ ] Instrumenter la rétention : compter les ouvertures du tableau de bord par établissement et par semaine. Le produit sait dire ce qu'un restaurant encaisse, pas si son patron l'a regardé — or c'est ce signal qui précède une résiliation de deux mois. Une colonne suffit, à ne coder qu'ici : avant deux clients payants, il n'y a rien à retenir

---

## Sous condition — ne pas ouvrir sans le déclencheur nommé

Chaque ligne est une chose qu'il serait tentant de construire. Le déclencheur
est la condition **exacte** qui la ferait entrer dans la roadmap.

| Chantier | Déclencheur |
|---|---|
| **Addition au niveau de la table** (une table qui commande en deux temps produit deux additions) | Trois patrons sur vingt le mentionnent **spontanément** en Phase 21 |
| **Formules / menus du jour** | Idem — trois mentions spontanées |
| **Tests frontend** (aucun aujourd'hui, sur 7 861 lignes) | Un bug de panier constaté chez un pilote, ou un deuxième développeur qui touche `menu/[qrToken]/page.tsx`. L'idempotence de 19.2 est testée côté serveur : c'est ce qui couvre l'argent |
| **Découper les deux fichiers de plus de 1 000 lignes** | Le même déclencheur que ci-dessus. Un refactor qui ne corrige aucun bug ne rapproche d'aucun client |
| **Intégration Konnect réelle** (le paiement carte reste simulé) | Un pilote qui le réclame. Le cash domine encore largement le commerce tunisien |
| **Intégration caisse / stock** | Dix prospects qui la citent comme motif de refus. C'est un autre produit, et la vraie douleur du patron |
| **Plusieurs instances backend** (WebSocket et limiteur en mémoire) | Une coupure de service constatée en pleine soirée, ou le 30ᵉ client |
| **Multi-établissements sous un même compte** | Un client qui possède deux établissements et le demande |
| **Mode sombre côté client** | Un retour de pilote sur la lisibilité en terrasse le soir |

## Hors périmètre, définitivement

- **Expansion régionale** (Algérie, Maroc, Libye) — seul chemin compatible avec une levée, donc hors sujet depuis le cadrage « entreprise rentable et non diluée ». Trois conquêtes commerciales distinctes pour un fondateur seul
- **Trois paliers d'abonnement** — remplacés par un prix unique. `Restaurant.subscription_tier` reste en base sans coût, et **aucun gating n'est codé** : bloquer une fonctionnalité déjà utilisée par un pilote casserait son service sans aucun bénéfice
- **Grands groupes, événements, réservations de salle** — Wassim a choisi de ne pas cadrer ; ne pas relancer
- **SMS au client, imprimante cuisine matérielle, montée de version Next.js** — arbitrages déjà tranchés (cf. archive)

---

## Ce qui est déjà livré (phases 12 à 18, closes)

Résumé destiné à ce fichier ; le détail par tâche vit dans l'historique git et
dans les PR citées.

| Phase | Ce qu'elle a livré | PR |
|---|---|---|
| **12.1** | Comptes serveur et cuisine créés par le manager, `Staff.is_active` vérifié à chaque requête, onglet Équipe | #36 |
| **12.2** | Surface publique fermée : `Order.public_token`, `qr_token` exigé à la création, `loyalty_phone` sorti de la vue client, WebSockets authentifiés, `POST /restaurants` supprimé — 20 tests nommés d'après chaque constat | #36, #44 |
| **12.3** | Alembic seule voie du schéma, test de conformité modèles/migrations, sonde `/health` qui interroge la base | #36, #41, #43 |
| **13.2** | Kit d'installation : `setup_restaurant.py`, import CSV, chevalets QR, fiches de prise en main et de formation | #37 |
| **13.3** | Les trois métriques de preuve, `/dashboard/preuve`, export CSV, définition codée de « commande perdue » | #37 |
| **14.1** | Vente incitative « avec ce plat » et son effet **mesuré** (`OrderItem.from_suggestion`) | #38 |
| **14.2** | Page publique « service inclus », rapport hebdomadaire par serveur, jamais de statistiques nominatives en salle | #39 |
| **15** | Tenue en service réel : écran cuisine à 360 px, repli papier, session expirée gérée, test de charge, deux défauts trouvés en rejouant un service | #39, #45 |
| **16** | Conformité 2004-63 : consentement au-dessus du champ, politique fr/ar, rétention et purge réelle | #40 |
| **17** | Recette du jour et commandes perdues en tête du dashboard, encart « ma soirée » sur l'écran serveur | #46 |
| **18** | Plan de salle : édition par glisser-déposer avec enregistrement automatique, vue serveur en direct, action depuis la table, couverts dessinés | #47, #48, #49, #50 |

Ce qui reste ouvert de ces phases a été repris ci-dessus : la mise en ligne
(→ Phase 20), les entretiens et les pilotes (→ 21, 23), le prix (→ 22), l'écran
de relevé « avant » (→ 23.2), le bandeau de fin de pilote (→ 22), et les
commandes actives non bornées dans le temps (→ 19.5).

---

## Comment travailler cette roadmap (pour Claude Code)

1. **Une tâche = une branche = une PR.** Jamais de push direct sur `main`. CI verte avant merge.
2. **Ordre strict**, sauf la Phase 21 (les entretiens) qui tourne en parallèle et n'attend aucun code.
3. **Phase 19 : écrire le test qui échoue d'abord**, puis le correctif. Un correctif de sécurité ou d'intégrité sans test qui le prouve ne compte pas comme livré.
4. **Cocher `[x]` avec le numéro de PR**, et si le scope a été réduit, écrire pourquoi sur la ligne.
5. **À la clôture d'une phase, recalculer la grille** — sur ce qui est constaté, jamais sur ce qui est préparé. Si une phase n'a déplacé aucune note, le dire dans la PR : c'est le signal que la tâche n'aurait pas dû être faite.
6. **Après la Phase 20, toute proposition de code doit nommer le restaurateur qui l'a demandée.** Sans nom, elle va en § « Sous condition ». C'est la règle que l'audit du 2026-08-15 rend nécessaire : trois phases irréprochables ont été livrées après que ce fichier eut écrit qu'écrire du code ferait baisser la note.
7. **Conventions inchangées** : voir `CLAUDE.md` (multi-tenant partout, transitions d'état contrôlées, prix figé sur `OrderItem`, tout nouveau modèle dans `model_registry.py`, toute migration dans la même PR, logs via `log_event`).
8. **Face à une ambiguïté produit** : livrer le scope le plus étroit qui règle le problème réel, et signaler l'ambiguïté dans la PR — plutôt que d'inventer une réponse.
