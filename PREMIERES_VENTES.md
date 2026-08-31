# Premières ventes — audit fonctionnel, audit business, et 10 recommandations

Document de travail du 2026-08-14, écrit après la clôture des phases 12 à 16.
Complète [`REVUE_INVESTISSEURS.md`](./REVUE_INVESTISSEURS.md), qui fonde la
roadmap. Celui-ci ne parle que d'une chose : **obtenir les deux premiers clients
payants.**

Rappel du cadrage (Wassim, 2026-08-13) : entreprise rentable et non diluée, prix
unique élevé avec service inclus, pas d'expansion régionale.

---

## 1. Audit fonctionnel — du point de vue du patron, pas du développeur

Le produit tient techniquement : 251 tests, surface publique fermée, conformité
2004-63, sonde de production honnête. Ce n'est pas le sujet ici. La question est
la seule qui compte en rendez-vous : **est-ce qu'il manque quelque chose qu'un
restaurateur remarquera dans sa première semaine ?**

### Ce qui est prêt et se montre

| Ce qu'il voit | Pourquoi ça compte pour lui |
|---|---|
| Le client scanne et commande | Aucune app à installer, aucun compte à créer |
| Le serveur **confirme** avant la cuisine | Il garde la main. C'est la réponse à « ça va remplacer mes serveurs ? » : non, ça les accélère |
| Écran cuisine temps réel | Fin des tickets illisibles et des allers-retours |
| Rupture de stock en un clic | Le plat disparaît instantanément des téléphones |
| Appel serveur depuis la table | La table n'a plus à agiter le bras |
| Trois chiffres de preuve | Commandes perdues, délai commande → cuisine, panier moyen |
| Rapport par serveur | Base d'une prime de rendement, pas d'une surveillance |
| Suggestions « avec ce plat » | Vente incitative, et son effet est **mesuré** |
| Mode ramadan + pré-commande iftar | Personne d'autre sur ce marché ne l'a |
| Carte de fidélité par téléphone | Le client revient, et c'est lui qui saisit son numéro |
| Repli papier | Bouton d'impression si le réseau tombe |
| Installation en une commande | Carte depuis CSV, chevalets QR, fiche d'identifiants |

### Les deux trous qui se verront

**A. Le patron ne voit nulle part son chiffre du jour.**

Le tableau de bord affiche les commandes en cours, les temps par étape, la
performance par serveur, les plats les plus vendus, la répartition horaire.
Il n'affiche **pas** « voilà ce que tu as encaissé aujourd'hui ». La donnée
existe (`orders_count` × `avg_basket_amount` sur la page de preuve), elle n'est
simplement jamais montrée comme un total.

C'est le seul chiffre qu'un restaurateur regarde chaque soir sans qu'on lui
demande. Tant qu'il n'y est pas, le tableau de bord est une curiosité qu'on
ouvre quand on y pense. Avec lui, c'est une habitude quotidienne — et une
habitude quotidienne est ce qui empêche une résiliation au troisième mois.

**Coût : faible. Impact sur la rétention : le plus élevé de tout ce qui reste.**
À faire avant le premier pilote, pas après.

**B. L'addition est par commande, jamais par table.**

Une table qui commande des boissons puis des plats — le cas le plus banal d'un
service — crée deux commandes indépendantes, donc deux additions et deux cartes
sur l'écran serveur. Le partage d'addition fonctionne, mais à l'intérieur d'une
seule commande.

Ce n'est pas un bug : c'est un choix de modèle qui n'a jamais été confronté à un
service réel. Il tiendra dans un café où l'on commande une fois. Il grincera
dans un restaurant où l'on commande en deux temps.

**À ne pas construire maintenant.** C'est exactement le genre de sujet que les
20 entretiens doivent trancher : si les restaurateurs le mentionnent
spontanément, c'est la première chose à faire après. S'ils ne le mentionnent
pas, le construire serait deviner.

### Ce qui manque volontairement, et l'assumer en rendez-vous

- **Pas d'intégration caisse.** C'est la vraie douleur du patron, et c'est un
  autre produit. Réponse honnête : « pas aujourd'hui, et je ne vous le promets
  pas ».
- **Paiement carte simulé.** Le cash domine encore largement le commerce
  tunisien. Ne pas en faire un argument.
- **Pas de formules / menus du jour.** À construire seulement si les entretiens
  le font remonter.

---

## 2. Audit business — où est la difficulté réelle

### L'arithmétique du prix, dans le sens du client

C'est le calcul central, et il est vérifiable devant lui :

- **120 DT/mois ≈ 4 DT par jour.**
- Une commande perdue, panier moyen autour de 25 DT.
- **Une commande perdue par semaine paie l'abonnement.**
- **Une par jour le paie six fois.**

Ce calcul est solide parce qu'il ne demande pas de le croire : le produit
**mesure** les commandes perdues. On promet un chiffre, puis on le montre.

Le panier moyen de 25 DT est une hypothèse à remplacer par le vrai chiffre du
premier établissement dès qu'il existe. Ne jamais le citer comme un fait.

### Le vrai obstacle n'est pas le prix

Le marché tunisien affiche 19 à 49 DT (cf. la revue). À 120 DT, Tawla est 2,5 à
6 fois plus cher. Un restaurateur qui compare deux lignes de tarif dira non, et
il aura raison — parce qu'il compare deux logiciels.

Il ne faut donc jamais vendre un logiciel. Les concurrents à 29 DT vendent un
lien vers un menu PDF : le restaurateur saisit sa carte lui-même, imprime ses QR
lui-même, se débrouille lui-même. Tawla vend **quelqu'un qui vient**, installe,
forme l'équipe, imprime les chevalets, et reste joignable pendant le service.

Le prix ne se compare que si les deux choses vendues sont les mêmes. Le travail
du rendez-vous est de rendre la comparaison impossible.

### Les trois risques classés par ce qu'ils coûtent

1. **Le serveur sabote l'outil.** Premier risque, et de loin. Il utilise son
   téléphone personnel, sa batterie, son forfait, et un rapport nominatif mesure
   son temps de prise en charge. Si on ne le convainc pas lui, l'outil est
   contourné en trois services et le patron résilie sans jamais dire pourquoi.
2. **Un incident en pleine soirée.** Réseau qui tombe, écran qui gèle. Le repli
   papier existe, il faut qu'il soit **répété à l'équipe avant** d'en avoir
   besoin — pas découvert le soir même.
3. **Le patron ne rouvre jamais le tableau de bord.** Cf. trou fonctionnel A.
   Un outil qu'on n'ouvre pas est un abonnement qu'on annule.

### La fenêtre de tir

**Ramadan, février-mars 2027.** L'iftar est le service le plus tendu de l'année :
toutes les tables commandent à la même minute, et c'est là que les commandes se
perdent le plus. Le produit a déjà le mode ramadan, l'heure d'iftar et la
pré-commande — un avantage qu'aucun concurrent local n'a construit.

Cela donne un calendrier, à remonter à l'envers :

| Quand | Quoi |
|---|---|
| **Août – septembre 2026** | Mise en ligne (sauvegardes comprises), 20 entretiens |
| **Octobre – novembre 2026** | Trois pilotes gratuits, quatre semaines chacun, chiffres relevés |
| **Décembre 2026 – janvier 2027** | Deux pilotes passent payants. Vente avec des chiffres réels en main |
| **Février – mars 2027** | Ramadan : la démonstration se fait toute seule |

Rater cette fenêtre coûte un an.

---

## 3. Dix recommandations pour les premières ventes

Classées par ordre d'exécution, pas par importance.

### 1. Ne vends pas l'application. Vends la commande perdue.

N'ouvre jamais un rendez-vous en montrant un écran. Ouvre-le par une question,
et tais-toi :

> « Combien de fois par service un client repart, ou renonce à recommander,
> parce que personne n'est venu à temps ? »

Il donnera un chiffre — ou il dira « ça arrive ». Les deux te suffisent. Alors,
et seulement alors, sors l'arithmétique : 4 DT par jour, une commande perdue par
semaine qui paie l'abonnement, une par jour qui le paie six fois.

C'est lui qui aura posé le problème. Tu ne fais que chiffrer sa propre phrase.

### 2. Choisis ton premier pilote pour son poids, pas pour sa facilité

Le restaurateur le plus accueillant n'est pas le plus utile. Les patrons se
connaissent, se parlent, et se recommandent entre eux plus efficacement que
n'importe quelle démarche commerciale.

Cherche l'établissement dont les autres parlent : celui qui est là depuis
quinze ans, dont le patron est respecté, et qui n'a pas la réputation de courir
après les nouveautés. Un « oui » de celui-là vaut vingt rendez-vous froids.

Accepte qu'il soit plus long à convaincre. C'est le seul endroit où la lenteur
est rentable.

### 3. Arrive avec SA carte déjà chargée

Ne fais jamais une démo sur un menu de démonstration. Avant le rendez-vous,
récupère sa carte — photo, PDF, ou la carte posée à l'entrée — et charge-la avec
`setup_restaurant.py` et l'import CSV.

Puis fais scanner le QR par son propre téléphone, et laisse-le voir **ses**
plats, **ses** prix, **ses** catégories.

La différence entre « voilà comment ça marcherait » et « voilà votre carte, elle
tourne » ne se rattrape par aucun argument. C'est l'usage le plus rentable du kit
d'installation, et personne à 29 DT ne le fera à ta place.

### 4. Vends d'abord un audit gratuit, pas un essai

Ne propose pas « essayez un mois ». Propose ceci :

> « Je viens quatre soirs. Je compte vos commandes perdues et votre panier
> moyen, à la main, sans rien installer. Je vous donne le chiffre. Si c'est zéro,
> je repars et vous ne me devez rien. »

Trois choses se produisent en même temps. Tu obtiens la **semaine de référence
avant activation**, sans laquelle la preuve d'après ne vaut rien. Tu passes
quatre soirées dans son établissement, donc tu connais son service mieux que
n'importe quel concurrent. Et tu as créé un engagement : il attend ton chiffre.

Un patron qui attend un chiffre de toi est déjà à moitié client.

### 5. Convaincs le serveur avant le patron

C'est la recommandation que tu regretteras d'avoir ignorée. Le patron signe, le
serveur décide si l'outil survit.

Ce qu'il faut lui dire, dans ces termes :

> « Tu ne prends plus les commandes. Tu les confirmes. Tu passes à table pour
> vérifier et encaisser, pas pour écrire. Tu tiens plus de tables en même temps,
> et le pourboire suit. »

Et traite de front, sans attendre qu'on te le demande, le sujet du téléphone
personnel — batterie, forfait, appareil privé utilisé pour travailler. Propose
au patron de fournir un téléphone de salle, ou de prendre le forfait en charge.
Le coût est dérisoire face à un outil contourné.

Enfin : le rapport par serveur est un **document de direction**. Il ne s'affiche
jamais en salle. Le jour où un serveur découvre qu'il est classé publiquement,
tu as perdu l'équipe.

### 6. Le prix ne bouge jamais. Le périmètre, oui.

La première remise tue le positionnement définitivement — et elle se saura, dans
un milieu où tout le monde se parle.

Quand il négocie, ne descends pas le prix : donne du temps.

> « Quatre semaines gratuites, service complet, installation comprise. En
> échange, j'ai le droit de citer votre nom et les chiffres mesurés chez vous. »

Tu ne perds rien : ces trois pilotes doivent de toute façon être gratuits. Tu
gagnes la seule chose qui manque — des références. Et le prix affiché reste
intact pour les quarante-deux suivants.

### 7. Remonte ton calendrier depuis Ramadan

Fixe février 2027 comme date de démonstration évidente, et déduis le reste :
entretiens en août-septembre, pilotes en octobre-novembre, passage payant en
décembre-janvier.

À partir de janvier, l'argument change de nature. Ce n'est plus « ça vous ferait
gagner » mais :

> « Dans trois semaines, toutes vos tables commanderont à la même minute.
> Combien de commandes vous perdez ce soir-là ? »

Le mode ramadan et la pré-commande iftar existent déjà. C'est l'argument
saisonnier le plus fort que tu auras, et il ne se présente qu'une fois par an.

### 8. Disqualifie durement à la porte

Un mauvais premier client coûte plus cher qu'il ne rapporte : il devient la
référence négative dont tout le quartier parlera.

Deux questions avant toute démonstration :

1. **Vos clients ont-ils un wifi utilisable, ou du réseau à toutes les tables ?**
   Si non, n'installe pas. Même s'il insiste. Le produit fonctionnera mal, et
   c'est ta faute qu'on retiendra, pas celle de son réseau.
2. **Combien de tables ?** En dessous de six, la douleur est trop faible pour
   justifier 120 DT, et tu vas passer ton temps en support pour rien.

Un troisième signal, positif : **une terrasse**. Terrasse = tables loin du
comptoir = serveur qui marche le plus = commandes perdues au maximum. Et le QR
est naturellement accepté dehors. C'est la douleur la plus forte pour le « oui »
le plus facile.

### 9. Fais signer une page pour chaque pilote

Sans accord écrit, tu finiras avec trois pilotes contents et zéro référence
utilisable — et toute la note « accès au marché » dépend de ces références.

Une page, quatre lignes :

- quatre semaines d'usage **effectif en service** (pas d'installation dormante) ;
- le droit de citer le nom de l'établissement ;
- le droit de publier les chiffres mesurés chez lui ;
- ce que tu fournis en échange : installation, formation, chevalets, support
  pendant le service.

S'il refuse le droit de citation, il n'est pas un pilote : c'est un client
gratuit. Remercie et passe au suivant.

### 10. Montre-lui son chiffre du jour

C'est à la fois une recommandation commerciale et la seule chose à construire
avant le premier pilote (cf. trou fonctionnel A).

Le tableau de bord ne montre nulle part ce qu'il a encaissé aujourd'hui. C'est
pourtant le seul chiffre qu'un restaurateur cherche tous les soirs de sa vie.

Mets-le en haut, en gros, avant tout le reste. Un patron qui ouvre Tawla chaque
soir pour voir son chiffre ne résilie pas au troisième mois — et il découvre le
délai commande → cuisine et les commandes perdues **en passant**, ce qui est
exactement la bonne façon de les lui faire adopter.

---

## Ce qu'il ne faut surtout pas faire

- **Publier un prix avant de l'avoir tranché.** La page d'accueil dit « tarif
  communiqué au premier rendez-vous » : c'est volontaire, et c'est mieux qu'un
  montant que personne n'a arrêté.
- **Inventer un chiffre de pilote ou un témoignage.** `PILOT_RESULTS` est vide
  exprès. Un faux chiffre détruit la seule chose que Tawla a à vendre : la
  mesure.
- **Construire une fonctionnalité pour décrocher une vente.** Si un prospect
  exige l'intégration caisse, ce n'est pas ton client aujourd'hui. Note-le,
  compte-le, et si dix le demandent, alors la question se posera.
- **Élargir la cible quand ça résiste.** Les petits cafés diront oui plus
  facilement et paieront moins, plus mal, et pour plus de support. C'est la pente
  qui transforme une entreprise rentable en travail mal payé.
