# Le relevé « avant Tawla » — Phase 23.1

Quatre soirs dans l'établissement, un chronomètre, une feuille. C'est le seul
travail de toute la roadmap qui devient **impossible à rattraper** une fois
l'outil installé : le jour où le QR est sur les tables, l'« avant » n'existe plus.

C'est aussi le meilleur argument de vente qui existe — vous ne demandez pas au
patron de vous croire, vous lui apportez ses propres chiffres.

> « Je viens quatre soirs. Je chronomètre le temps qu'une table attend avant
> qu'on prenne sa commande, et je relève votre panier moyen, à la main, sans rien
> installer. Je vous donne les chiffres. S'il n'y a rien à gagner, je repars et
> vous ne me devez rien. »

Trois choses se produisent en même temps : vous obtenez la mesure de référence,
vous passez quatre soirées à comprendre son service mieux qu'aucun concurrent, et
il attend un chiffre de vous. Un patron qui attend un chiffre est déjà à moitié
client.

---

## La règle qui rend le chiffre utilisable

**Compter « avant » exactement comme le code comptera « après ».** Une mesure
d'avant faite à sa manière et une mesure d'après faite par la machine ne se
comparent pas — et une comparaison fausse détruit la seule chose que Tawla a à
vendre.

**Ce que le code mesure après installation**, et donc les deux seules choses
qui se comparent :

1. le **délai entre la commande du client et son arrivée en cuisine**
   (`avg_order_to_kitchen_seconds`) ;
2. le **panier moyen** (`avg_basket_amount`), avec et sans suggestion acceptée.

Les deux se mesurent seuls, sans qu'un serveur ait à enregistrer quoi que ce
soit. C'est précisément pour ça qu'ils sont comparables : ils ne dépendent
d'aucune discipline d'équipe, ni avant ni après.

> **Ce qu'on ne mesure plus, et qu'il ne faut plus promettre :** un comptage
> des « commandes perdues » a existé dans le produit jusqu'au 2026-09-09. Il ne
> comptait que les annulations qu'un serveur avait pris la peine
> d'enregistrer — donc zéro dans une équipe qui ne clique pas, et aveugle au
> client qui se lasse et s'en va. Retiré du produit et de l'argumentaire. Ne
> pas bâtir un « avant » sur un « après » qui n'existe plus.

Les équivalents observables à la main, et rien d'autre :

| Ce que le code mesurera | Ce que vous notez sur place |
|---|---|
| Délai commande → cuisine | Le temps entre le moment où le serveur prend la commande et celui où elle arrive en cuisine, chronomètre en main |
| Panier moyen | Total encaissé du service ÷ nombre de tables servies, lu sur la caisse en fin de soirée. Ne pas estimer |

**Notez aussi, à part, ce que le code ne mesurera jamais** — ça ne sert pas la
comparaison chiffrée, ça sert l'argumentaire et votre compréhension du service :
une table installée qui attend plus de dix minutes avant qu'on prenne sa
commande, un client qui s'installe puis repart sans commander, une commande
annulée ou renvoyée en cuisine. Ces lignes se racontent, elles ne se comparent
pas.

---

## Le protocole, soir par soir

**Quatre soirs, tous des services complets.** Choisir des soirs comparables entre
eux et comparables à ce qui suivra : si le pilote démarre un mardi, ne pas mesurer
quatre samedis.

Ce qu'il faut au poste :

- une montre ou le chronomètre du téléphone ;
- la feuille ci-dessous, imprimée, une par soir ;
- un endroit d'où l'on voit **toute la salle**, y compris la terrasse. Si la
  terrasse n'est pas visible depuis un seul point, mesurer la terrasse seule et
  l'écrire — mieux vaut un périmètre réduit et honnête qu'un total inventé.

Comment compter une table :

1. La table s'installe → **noter l'heure**.
2. Un serveur prend sa commande → **noter l'heure**. L'écart est le délai.
3. Si l'écart dépasse 10 minutes → cocher la colonne **> 10 min**.
4. Une commande annulée, refusée ou renvoyée en cuisine → cocher **annulée**.
5. Si elle repart avant de commander → colonne **repartie**.

Les colonnes 3 à 5 nourrissent votre compréhension du service et
l'argumentaire ; **aucune des trois ne se compare** à un chiffre d'après. Seuls
le délai et le panier moyen se comparent.

Ne compter que les tables **installées pour consommer** : quelqu'un qui prend un
café au comptoir n'entre pas dans la mesure, parce qu'il n'entrera pas non plus
dans la mesure d'après.

**Ne pas aider le service.** Vous mesurez un fonctionnement normal ; un soir où
vous avez donné un coup de main n'est pas mesurable. Le noter si ça arrive.

---

## Feuille de relevé — à imprimer, une par soir

```
ÉTABLISSEMENT : ____________________   DATE : ____/____/______
SERVICE : midi / soir      MÉTÉO : ______      JOUR : L Ma Me J V S D
PARTICULARITÉ (match, veille de fête, travaux, absence d'un serveur) :
_______________________________________________________________________

  #  | Zone      | Installée | Commande prise | Écart | > 10 min | Annulée | Repartie
-----|-----------|-----------|----------------|-------|----------|---------|----------
  1  |           |    :      |      :         |       |          |         |
  2  |           |    :      |      :         |       |          |         |
  3  |           |    :      |      :         |       |          |         |
  4  |           |    :      |      :         |       |          |         |
  5  |           |    :      |      :         |       |          |         |
  6  |           |    :      |      :         |       |          |         |
  7  |           |    :      |      :         |       |          |         |
  8  |           |    :      |      :         |       |          |         |
  9  |           |    :      |      :         |       |          |         |
 10  |           |    :      |      :         |       |          |         |
 11  |           |    :      |      :         |       |          |         |
 12  |           |    :      |      :         |       |          |         |
 13  |           |    :      |      :         |       |          |         |
 14  |           |    :      |      :         |       |          |         |
 15  |           |    :      |      :         |       |          |         |
 16  |           |    :      |      :         |       |          |         |
 17  |           |    :      |      :         |       |          |         |
 18  |           |    :      |      :         |       |          |         |
 19  |           |    :      |      :         |       |          |         |
 20  |           |    :      |      :         |       |          |         |

TOTAUX DU SOIR
  Tables servies ............................ ______
  Délai moyen installée → commande .......... ______ min   (se compare)
  Tables > 10 min avant commande ............ ______       (contexte)
  Commandes annulées ou renvoyées ........... ______       (contexte)
  Clients repartis sans commander ........... ______       (contexte)

RELEVÉ DE CAISSE (fin de service)
  Total encaissé ............................ ______ DT
  Nombre de tables servies (caisse) ......... ______
  Panier moyen = total ÷ tables ............. ______ DT

CE QUE J'AI VU ET QUI NE SE COMPTE PAS
_______________________________________________________________________
_______________________________________________________________________

UNE PHRASE DU PATRON OU D'UN SERVEUR, MOT POUR MOT
« _____________________________________________________________________ »
```

---

## Après le quatrième soir

**Faire la moyenne des quatre**, pas le total. Reporter dans
`terrain/PILOTES.md`, bloc de l'établissement, section « Semaine de référence ».

Deux chiffres, et rien d'autre — ce sont les deux que le produit saura
remesurer seul après installation :

| | Valeur relevée |
|---|---|
| Délai moyen installée → commande | ______ min |
| Panier moyen | ______ DT |

Ces deux valeurs iront dans `Restaurant.baseline_*` (Phase 23.2) et
s'afficheront sur `/dashboard/preuve` en face des chiffres mesurés. **Ne jamais
les arrondir dans le sens qui arrange**, et ne jamais en inventer une qui
manquerait : une seule valeur inventée rend toute la démonstration mensongère, et
un restaurateur qui reconnaît un chiffre faux sur son propre service ne vous
recevra plus.

## Rendre le chiffre au patron

Le lendemain du quatrième soir, en cinq minutes, debout :

> « Sur vos quatre soirs : ___ minutes en moyenne entre le moment où une table
> s'installe et le moment où quelqu'un prend sa commande, et ___ DT de panier
> moyen. Sur ___ tables par service, ça fait environ ___ minutes d'attente
> cumulée chaque soir. »

Puis se taire. C'est lui qui doit dire le mot suivant.

**Si le chiffre est proche de zéro, le dire et partir.** Un établissement qui ne
perd rien n'a pas besoin de Tawla, et forcer la vente donnera un client qui
résilie au troisième mois en le racontant à tout le quartier. C'est la promesse
qui rend l'audit crédible chez les dix suivants.

## Si le patron refuse le relevé

Deux réponses possibles, et elles ne veulent pas dire la même chose :

- **« Pas besoin, je sais que j'en perds »** → il croit déjà au problème. Faire
  quand même les quatre soirs : sans « avant » chiffré, le passage au payant en
  Phase 24 se négociera sur une impression.
- **« Je ne veux pas de quelqu'un qui observe mon service »** → ce n'est pas un
  refus de la mesure, c'est un refus de vous. Remercier, passer au suivant, et
  le noter dans `ENTRETIENS.md` : un pilote qui ne veut pas être regardé ne
  laissera pas non plus publier ses chiffres.
