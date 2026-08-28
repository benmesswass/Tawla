# Le parcours de Wassim — ce que personne ne peut faire à ta place

Point d'entrée unique pour les 31 tâches 🧑 de la roadmap. Les autres documents
de `terrain/` disent **comment** ; celui-ci dit **quoi, maintenant, et quand
c'est fini**.

Règle de lecture : prendre la première étape non cochée. Ne pas en préparer une
plus loin parce qu'elle paraît plus agréable — c'est toujours celle qui demande
de sortir qu'on repousse.

---

## Où j'en suis

- [ ] **Étape 1** — Mettre en ligne
- [ ] **Étape 2** — Vingt entretiens
- [ ] **Étape 3** — Trancher le prix
- [ ] **Étape 4** — Choisir et cadrer trois pilotes
- [ ] **Étape 5** — Les quatre soirs de relevé, par pilote
- [ ] **Étape 6** — Installer et former
- [ ] **Étape 7** — Quatre semaines de service réel
- [ ] **Étape 8** — Rendre les chiffres, faire passer au payant

Cocher une étape veut dire que **son critère de fin est vrai**, pas qu'on s'en
est occupé.

---

## Étape 1 — Mettre en ligne

**Une demi-journée · d'une traite · [`MISE_EN_LIGNE.md`](./MISE_EN_LIGNE.md)**

Domaine, hébergeur, clés, sauvegardes, monitoring, déclaration INPDP. Le document
donne l'ordre exact, les commandes à copier et les valeurs à renseigner.

Attendre que la Phase 19 soit fusionnée : le correctif du limiteur de débit n'a
de sens qu'ici, et sans lui le premier soir de service donnera des erreurs à
toute l'équipe.

**Fini quand** : une commande passée depuis un téléphone sur `tawla.tn` arrive
sur l'écran cuisine, une sauvegarde a été **restaurée pour de vrai**, une alerte
de monitoring est arrivée sur ton téléphone lors d'une coupure volontaire, le
parcours en 13 points est passé en entier, et la déclaration INPDP est déposée.

---

## Étape 2 — Vingt entretiens

**Trois semaines · deux sorties par semaine · [`GUIDE_ENTRETIEN.md`](./GUIDE_ENTRETIEN.md) → [`ENTRETIENS.md`](./ENTRETIENS.md)**

C'est la ligne qui pèse 20 % de la grille et qui est notée 2,0 depuis le début du
projet. Elle n'attend rien : elle peut commencer pendant que l'étape 1 se termine,
et même pendant que la Phase 19 est en revue.

Le guide couvre maintenant les deux moitiés du travail : comment obtenir les
rendez-vous (liste de quarante adresses, créneau 15 h – 17 h du mardi au jeudi,
les trente secondes à la porte, quoi faire des refus) et comment mener la
conversation.

**Fini quand** : vingt lignes remplies dans `ENTRETIENS.md`, verbatims compris,
et la synthèse écrite — les trois douleurs les plus citées, le prix médian
accepté, et **ce qui sort de la roadmap**.

**Décision qui t'appartient, à prendre à la fin** : la coupe. Trois candidats
sont déjà nommés par l'audit — partage d'addition, mode café, célébrations et
carte à partager. Si aucun des vingt ne les mentionne spontanément, les retirer
coûte moins cher que les maintenir dans chaque écran et chaque traduction. Écrire
la décision dans `ROADMAP.md`, même si c'est « on garde ».

---

## Étape 3 — Trancher le prix

**Déjà fait côté code, au 2026-08-28 — cette étape n'attend plus que toi.**

Le prix unique à 120 DT décrit ici jusqu'au 18 août n'a jamais été codé.
Depuis (Phase 22, PR #63, amendé PR #91) : **trois paliers publics 49/89/149
DT** (Essentiel/Pro/Business), gating réel par fonctionnalité, page
tarifaire publique et inscription en self-service — tout vit dans le code
aujourd'hui, plus dans une constante `null`. Le rappel de paiement (« le
bandeau de fin de pilote » qu'on attendait plus bas) est lui aussi déjà
codé : une modale à chaque connexion tant que l'établissement n'a jamais
payé. Aucune session de code n'attend plus rien ici.

Pour cette cible (6 tables et plus) : **le nombre à dire est Pro, 89
DT/mois** — voir `ARGUMENTAIRE_RESTAURATEUR.md` pour l'arithmétique complète
et pourquoi ne jamais proposer Essentiel en premier ici.

Les vingt entretiens ne servent toujours pas à découvrir le prix — ils
servent à savoir **comment le présenter**. Si le prix médian accepté sort
très en dessous de 89, ça ne veut pas dire « baisser » : ça veut dire que la
valeur n'a pas été comprise, ou que la cible est mauvaise.

**Fini quand** : tu as dit à voix haute la phrase que tu diras au prochain
patron sans hésiter dessus. Le montant, lui, est déjà écrit — cette case ne
se coche que sur la seconde moitié, qui reste à toi.

---

## Étape 4 — Choisir et cadrer trois pilotes

**Deux semaines · trois profils : quartier, centre-ville, zone touristique**

Choisir pour le **poids social**, pas pour la facilité. Le plus accueillant n'est
pas le plus utile : cherche celui dont les autres patrons parlent, installé depuis
quinze ans, qui n'a pas la réputation de courir après les nouveautés. Un « oui »
de celui-là vaut vingt rendez-vous froids, et il sera plus long à convaincre —
c'est le seul endroit où la lenteur est rentable.

Disqualifier durement à la porte, sans exception :

- **pas de Wi-Fi utilisable ou pas de réseau à toutes les tables** → ne pas
  installer, même s'il insiste. Le produit fonctionnera mal, et c'est ta faute
  qu'on retiendra, pas celle de son réseau ;
- **moins de six tables** → douleur trop faible pour 120 DT, et du support pour
  rien.

**Accord écrit d'une page par pilote**, quatre lignes :

1. quatre semaines d'usage **effectif en service** — pas une installation dormante ;
2. le droit de citer le nom de l'établissement ;
3. le droit de publier les chiffres mesurés chez lui ;
4. ce que tu fournis : installation, formation, chevalets, support pendant le service.

S'il refuse le droit de citation, ce n'est pas un pilote : c'est un client
gratuit. Remercier et passer au suivant — toute la note « accès au marché »
dépend de ces références.

**Fini quand** : trois accords signés, trois profils différents.

---

## Étape 5 — Les quatre soirs de relevé

**Quatre soirs par pilote · [`RELEVE_AVANT.md`](./RELEVE_AVANT.md)**

**L'étape la plus importante de tout le parcours, et la seule qu'on ne peut pas
rattraper.** Le jour où le QR est sur les tables, l'« avant » n'existe plus.

Le document donne la feuille à imprimer, le protocole de comptage, et surtout la
règle qui rend le chiffre utilisable : compter « avant » exactement comme le code
comptera « après » — commande annulée, ou table qui attend plus de dix minutes.

Ne pas aider le service pendant la mesure. Ne pas arrondir dans le sens qui
arrange. Et si le chiffre est proche de zéro, **le dire et partir** : c'est cette
promesse tenue qui rend l'audit crédible chez les dix suivants.

**Fini quand** : trois chiffres par pilote, reportés dans `PILOTES.md`.

---

## Étape 6 — Installer et former

**Une demi-journée par pilote · [`FORMATION_10MIN.md`](./FORMATION_10MIN.md) + [`PRISE_EN_MAIN.md`](./PRISE_EN_MAIN.md)**

Arriver avec **sa** carte déjà chargée. Récupérer son menu avant le rendez-vous —
photo, PDF, ou la carte posée à l'entrée — et l'importer via
`setup_restaurant.py`. Puis lui faire scanner son propre QR avec son propre
téléphone. La différence entre « voilà comment ça marcherait » et « voilà votre
carte, elle tourne » ne se rattrape par aucun argument.

Deux conversations à avoir **avant** de brancher quoi que ce soit, avec le patron
seul (le déroulé exact est dans `FORMATION_10MIN.md`) :

- **le téléphone personnel du serveur** — batterie, forfait, appareil privé
  utilisé pour travailler. Proposer un téléphone de salle ou la prise en charge
  du forfait : le coût est dérisoire face à un outil contourné ;
- **les statistiques nominatives** — présentées comme une base de prime, ça
  passe ; découvertes par hasard, c'est de la surveillance et l'équipe sabote.
  C'est **lui** qui doit l'annoncer, pas toi.

Puis convaincre les serveurs avant le patron, dans ces mots : « tu ne prends plus
les commandes, tu les confirmes ». Le patron signe, le serveur décide si l'outil
survit.

**Fini quand** : le carnet papier est resté sur le comptoir, le repli a été
répété à l'équipe, et une vraie commande client est passée devant toi.

---

## Étape 7 — Quatre semaines de service réel

**Par pilote · [`PILOTES.md`](./PILOTES.md), tenu le soir même**

Ce qui se perd si on ne l'écrit pas le soir même : les phrases exactes du patron,
ce qui a bloqué en salle, ce que l'équipe a contourné. Une semaine plus tard il ne
reste qu'une impression, et une impression ne se montre à personne.

Deux choses à confronter au réel, et à me remonter :

- le seuil de **dix minutes** avant qu'une table en attente soit signalée au
  serveur (`ATTENTE_ALERTE_MINUTES`, `frontend/app/staff/page.tsx`) — c'est une
  proposition, pas une vérité. Elle ne compte plus dans « commandes perdues »
  depuis le 2026-08-28 (seule une annulation compte), mais reste le seuil
  d'alerte à l'écran serveur ;
- le **plan de salle** : les zones suffisaient-elles, ou le plan dessiné change-t-il
  vraiment la conversation ?

Être joignable pendant les services. C'est littéralement ce qui est vendu.

**Fini quand** : quatre semaines d'usage effectif, incidents consignés, trois
métriques relevées chaque semaine sur `/dashboard/preuve`.

---

## Étape 8 — Rendre les chiffres, faire passer au payant

**Une conversation par pilote, debout, cinq minutes**

Montrer `/dashboard/preuve` : « avant Tawla » en face de « mesuré ». C'est la
capture d'écran qui vend, et elle n'existe que si l'étape 5 a été faite.

Puis se taire.

**Le prix ne bouge jamais. Le périmètre, oui.** Quand il négocie, ne descends pas
le prix — donne du temps : « quatre semaines gratuites de plus, service complet,
en échange du droit de citer votre nom et vos chiffres ». La première remise tue
le positionnement définitivement, et elle se saura : dans ce milieu, tout le monde
se parle.

**Deux chiffres à noter pour toi**, et ils décident de la suite du projet :

- la **durée réelle** d'une installation ;
- les **minutes de support** par client et par semaine.

Le modèle à 45 clients suppose une heure et quelques minutes. Si l'installation
prend une demi-journée, la cible est 20 clients, pas 45 — et il vaut mieux
l'apprendre au deuxième client qu'au vingtième.

**Fini quand** : deux des trois pilotes paient, et la première facture est
encaissée.

---

## Les quatre pièges de ce parcours

1. **Coder entre deux sorties.** C'est le piège principal, et il est documenté :
   trois phases techniquement irréprochables ont été livrées après que la roadmap
   eut écrit qu'écrire du code ferait baisser la note. Après la mise en ligne,
   toute idée de fonctionnalité doit nommer le restaurateur qui l'a demandée.
2. **Sauter le relevé « avant ».** Il paraît toujours possible de le faire plus
   tard. Il ne l'est jamais.
3. **Installer chez un établissement au mauvais réseau** parce qu'il a dit oui.
   Le premier mauvais client coûte plus cher qu'il ne rapporte : il devient la
   référence négative dont le quartier parle.
4. **Élargir la cible quand ça résiste.** Les petits cafés diront oui plus
   facilement et paieront moins, plus mal, et pour plus de support. C'est la pente
   qui transforme une entreprise rentable en travail mal payé.

## Ce que je peux faire pendant ce temps

- La Phase 19 (les trois défauts), en une passe.
- La Phase 23.2 (l'écran de saisie du relevé), **le jour où le premier relevé
  existe** — pas avant.
- Les Phases 22 et 24 côté code : le prix affiché, le bandeau de fin de pilote,
  le compteur de rétention.
- Répondre à une question précise sur un écran ou un chiffre pendant que tu es
  chez un pilote.

Tout le reste de cette page est à toi. C'est le sujet du projet.
