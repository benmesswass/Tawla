# Étude de marché — concurrence et positionnement (28 août 2026)

Écrite le **2026-08-28**, sur `main` au commit `30bd2d9`. Complète
[`REVUE_INVESTISSEURS.md`](./REVUE_INVESTISSEURS.md) (13 août, première analyse
concurrentielle), [`AUDIT_FINAL.md`](./AUDIT_FINAL.md) (15 août, première
revérification) et [`MARCHE_FRANCE.md`](./MARCHE_FRANCE.md) (24 août, cadrage
France) — **sans réécrire aucun des trois**, qui restent des instantanés datés,
sur le modèle déjà posé par [`PREMIERES_VENTES.md`](./PREMIERES_VENTES.md).
Là où ce document corrige un raccourci d'un document antérieur, il le dit
explicitement et cite la ligne concernée, sans modifier le fichier source.

**Objet** : troisième revérification tunisienne (13 → 15 → 28 août, stable sur
les trois), triangulation du marché adressable, tranchage de deux incohérences
internes, revérification France, matrice comparative, énoncé de positionnement,
analyse de défendabilité des prix.

---

## 0. Méthode et limite à connaître avant de lire le reste

Recherche menée par deux agents en arrière-plan (skill `research`), l'un sur la
Tunisie, l'autre sur la France, chacun avec instruction explicite de vérifier
en direct plutôt que de se fier à une mémoire d'entraînement.

**Limite technique rencontrée par les deux agents, à prendre au sérieux** :
l'accès direct aux pages (`WebFetch`) a échoué à **100 %** dans cet
environnement d'exécution — y compris sur des domaines de contrôle neutres
sans aucun rapport avec la Tunisie ou la restauration (`en.wikipedia.org`,
`www.google.com`). C'est donc un blocage réseau généralisé de l'environnement
(proxy de sortie), pas un blocage ciblé sur les sites concurrents. Conséquence
directe : **aucune affirmation de ce document ne vient d'une lecture intégrale
d'une page primaire.** Tout vient de `WebSearch` — des extraits déjà résumés
par un modèle tiers — recoupés manuellement entre plusieurs sources
indépendantes chaque fois que c'était possible.

Deux niveaux de fiabilité en résultent, distingués tout du long :

- **Fiable** : les chiffres répétés à l'identique sur de nombreuses requêtes
  indépendantes et plusieurs médias différents (les 4 prix Digital Menu, les
  chiffres de levée Sunday, les 392-397 restaurants touristiques classés ONTT).
- **⚠️ Non confirmé** : tout ce qui ne repose que sur une source unique, une
  formulation suspecte de recoupement entre deux sites, ou un site de contenu
  à fiabilité incertaine. Marqué explicitement à chaque occurrence plutôt que
  présenté comme un fait établi.

---

## 1. Tunisie — la concurrence, revérifiée une troisième fois

Digital Menu, Scanny et Menu-QR restaient stables entre le 13 et le 15 août.
Ils le restent aussi le 28 août — mais cette fois avec le détail **par
palier**, jamais documenté avant, qui permet de trancher l'incohérence du
§2.2.

### 1.1 Digital Menu (digitalmenu.tn) — quatre paliers, quatre profils différents

| | **Light** — 19 DT | **Serveur** — 29 DT | **Commande à table** — 39 DT | **Boost / Premium** — 49 DT |
|---|---|---|---|---|
| Nature | Menu digital affiché | Prise de commande **staff** | Autonomie client **+** staff | Marketing/fidélisation au-dessus des trois |
| Menu QR multilingue (fr/en/ar), produits illimités, édition temps réel | ✅ | ✅ | ✅ | ✅ |
| QR par table auto-généré, PDF à imprimer soi-même (cartes pré-imprimées en option payante) | ✅ | ✅ | ✅ | ✅ |
| Commande prise par le **serveur**, transmise en cuisine | ⚠️ non confirmé inclus | ✅ (fonctionnalité qui définit ce palier) | ✅ (hérité) | ✅ (hérité) |
| Commande **autonome** par le client, sans serveur | ❌ | ⚠️ non confirmé | ✅ (fonctionnalité qui définit ce palier) | ✅ (hérité) |
| Écran/TV cuisine temps réel | ⚠️ non confirmé — une source dit « selon l'offre souscrite » sans préciser le seuil | probable | probable | ✅ |
| Fidélité | ❌ | ⚠️ non confirmé | ⚠️ non confirmé | ✅ |
| Menu IA (recommandations/upsell automatique) | ❌ | ❌ | ❌ | ✅ |
| Marketing (avis Google, happy hour, retargeting, VIP) | ❌ | ❌ | ❌ | ✅ |

Multi-zone / postes de production / stats personnel — cités dans
`REVUE_INVESTISSEURS.md` comme un gap Tawla — apparaissent cette fois sur une
page à part (« Gestion Multi-Entreprise »), **jamais rattachés explicitement à
l'un des 4 paliers** dans les sources retrouvées. Possible produit/option
séparée plutôt qu'un gap généralisé sur toute la gamme — à vérifier avant de
le citer à nouveau tel quel.

Sources (URLs vues, non lues directement — cf. §0) :
`digitalmenu.tn/prix-tarif-menu-digital-qr-code`,
`digitalmenu.tn/fonctionnalites-menu-digital-qr-code`,
`digitalmenu.tn/fonctionnalites/{gestion-multi-entreprise-restaurant,menu-ia-intelligent,happy-hour}`,
`digitalmenu.tn/faq`. Consultées le 2026-08-28.

### 1.2 Scanny (scanny.tn)

**Aucun prix trouvé**, malgré plusieurs angles de recherche — à la différence
de Digital Menu, dont les 4 prix sont répétés identiquement partout. Accès
direct techniquement impossible (`scanny.tn` ne résout même pas en DNS depuis
cet environnement).

| | Palier de base | **Scanny Pro** |
|---|---|---|
| Menu QR (sans app), édition menu/prix/photos/horaires/promos | ✅ | ✅ |
| Réservation, commande sur place/emporter/livraison, appel serveur | ✅ (portée exacte non confirmée) | ✅ |
| « Caisse connectée » | ❌ | ✅ |

« Caisse connectée » désigne un **module de caisse propriétaire Scanny**
(commandes, paiements hors-ligne, reçus, remises, stats avancées) — aucune
source ne mentionne une intégration avec un logiciel de caisse tunisien tiers
(La Caisse, Megasoft, INNOVA SOFT, ASM). Point non tranché et potentiellement
important : la Tunisie impose depuis le **1er novembre 2025** (généralisation
au **1er juillet 2026**) une **homologation NACEF** obligatoire pour tout
logiciel de caisse utilisé en restauration (ticket + QR fiscal, chiffrement,
transmission au fisc). Aucune source ne confirme ni n'infirme que le module
Scanny Pro est homologué — à vérifier avant de s'appuyer dessus dans un
argumentaire commercial. Voir aussi §8 : cette même question se pose pour
Tawla.

### 1.3 Menu-QR (menu-qr.tn)

**Aucun prix trouvé.** Semble être une offre à palier unique (aucune
segmentation trouvée, cohérent avec son positionnement « entrée de gamme »
dans les documents internes).

| | Menu-QR |
|---|---|
| QR unique par table, PDF auto-généré ou cartes pré-imprimées en option | ✅ |
| Import du menu (modèle, PDF existant, ou saisie à blanc), photos, allergènes | ✅ |
| **Commande réelle** depuis le téléphone du client (pas juste consultation) | ✅ |
| Paiement | Cash/carte **à table** — pas de paiement en ligne |
| Vue cuisine sur tablette | ✅ |
| Rôles séparés (serveur, caissier, cuisine, manager) | ✅ |
| Fidélité / IA / marketing / multi-établissement | Aucune mention trouvée |

### 1.4 Nouveaux entrants identifiés — absents des documents internes

- **MAGH-QR** (`maghqr.net`) — QR + commande + paiement mobile revendiqués,
  aucun prix trouvé. Fait notable : c'est l'un des deux **seuls** acteurs
  tunisiens retenus dans un panorama nord-africain indépendant d'avril 2026
  (voir plus bas), aux côtés de Digital Menu — Scanny et Menu-QR n'y figurent
  pas.
- **Menu Clipper** (`menu.clpr.tn`) — menu QR temps réel, **aucune mention de
  commande réelle trouvée**. Sur la base de ce qui a été trouvé, c'est
  potentiellement le seul vrai « juste un menu digital, pas de commande » du
  marché tunisien identifié dans cette recherche — l'inverse exact de ce que
  `PREMIERES_VENTES.md` reprochait à tort à Digital Menu (§2.2).
- **Feady's** (`feadys.com`) — plateforme francophone multi-pays (Maroc,
  France, Tunisie, Algérie, Belgique, Suisse, Canada…), 12 000+ établissements
  revendiqués **au global**, pas en Tunisie spécifiquement. 0 % commission,
  site généré par IA. Catégorie un peu différente (vente en ligne + site web),
  avec un sous-domaine `scan.feadys.com` qui suggère une vraie brique
  commande à table. À surveiller plutôt qu'à classer comme concurrent direct.

**Panorama régional** (`magstartup.com`, avril 2026, ⚠️ source à fiabilité
incertaine — format listicle générique, jamais lue directement, noms non
recoupés indépendamment) : classe Digital Menu et MAGH-QR comme les deux seuls
acteurs tunisiens, face à NResto/Winakol (Algérie) et TacMenu/MyQR.ma/Menuquick
(Maroc). **Aucune preuve trouvée** qu'un acteur algérien ou marocain opère
activement en Tunisie, ni qu'un acteur MENA plus large (**Foodics**, le plus
gros acteur POS/QR de la région, 30 000+ points de vente revendiqués) y soit
présent — recherches ciblées sans résultat.

**Systèmes de caisse tunisiens** (La Caisse, Megasoft ERP, INNOVA SOFT, ASM
POS) : tous engagés dans la mise en conformité NACEF, **aucune preuve trouvée**
qu'un seul ait ajouté un module de commande client par QR (à distinguer du QR
**fiscal** imprimé sur le ticket, obligatoire, sans lien avec la commande
client). Zone à re-surveiller : la généralisation NACEF de juillet 2026 vient
de forcer une nouvelle version chez tous ces éditeurs — moment plausible pour
qu'un module QR apparaisse.

### 1.5 Le vrai concurrent n°1 : ne rien changer

**Aucune étude chiffrée trouvée** sur le taux d'équipement logiciel des
cafés/restaurants tunisiens, malgré plusieurs angles de recherche (secteur
CHR, Chambre nationale des cafetiers, digitalisation de la restauration
tunisienne). Ce qui suit est une **déduction logique, pas un chiffre sourcé** :

- Aucun des trois concurrents logiciels vérifiés ne publie de nombre de
  clients/établissements équipés — recherché spécifiquement pour chacun, sans
  résultat.
- Le marché adressable tourne autour de 40 000 à 48 000 établissements (§3).
  Même en supposant très généreusement que Digital Menu + Scanny + Menu-QR +
  MAGH-QR + Menu Clipper cumulent plusieurs milliers de clients (hypothèse
  haute, sans aucun chiffre concret pour l'appuyer), ça resterait une fraction
  à un chiffre du marché total.
- Corroboration indirecte : seuls ~392-397 établissements sont officiellement
  « restaurants touristiques classés » (§3) sur des dizaines de milliers —
  la formalisation (classement, logiciel, process) reste l'exception, pas la
  norme, dans ce secteur en Tunisie.

**Le carnet papier, l'appel du serveur, la commande orale ou par groupe
WhatsApp du resto restent donc, par déduction, le mode dominant** — pas un
concurrent qu'on trouve en ligne, mais celui que Tawla affronte réellement
dans l'écrasante majorité des services.

---

## 2. Les deux incohérences, tranchées

### 2.1 « Tawla est 3 à 6 fois plus cher que le marché » — vrai pour un palier, pas trois

Le narratif de `PREMIERES_VENTES.md` (« à 120 DT, Tawla est 2,5 à 6 fois plus
cher ») a été écrit le 14 août sur le prix unique d'alors. Depuis le
**2026-08-26** (PR #91), Tawla facture trois paliers : **Essentiel 49 DT /
Pro 89 DT / Business 149 DT** (`core/markets.py::TUNISIA.tier_prices`). Voici
ce que ça donne face à la fourchette Digital Menu (19-49 DT), palier par
palier :

| Palier Tawla | Prix | vs Digital Menu 19 DT | vs Digital Menu 49 DT (Boost) | Le narratif « pas comparable » tient ? |
|---|---:|---:|---:|---|
| **Essentiel** | 49 DT | × 2,6 | **× 1,0 (parité)** | **Non** — au même prix que le palier le plus riche de Digital Menu |
| **Pro** | 89 DT | × 4,7 | × 1,8 | Partiellement — premium réel, mais modeste face au palier Boost |
| **Business** | 149 DT | × 7,8 | × 3,0 | **Oui** — c'est la version qui correspond à l'ancien narratif |

**Verdict, noir sur blanc** : le narratif « on ne vend pas un logiciel, donc le
prix ne se compare pas » **reste honnête pour Business, à moitié honnête pour
Pro, et ne tient plus du tout pour Essentiel** — qui coûte très exactement ce
que coûte le palier le plus complet (fidélité + IA + marketing) de Digital
Menu. Ce n'est pas anodin : `Essentiel` est explicitement scopé pour « un
petit café, une seule salle » (`frontend/lib/offer.ts`), un segment que
`terrain/GUIDE_ENTRETIEN.md` exclut déjà de la cible commerciale (« Pas les
petits cafés : ticket trop faible pour le prix visé »). Tant que la vente se
fait sur le terrain à des restaurants de 6 tables et plus, c'est donc Pro ou
Business qui devrait être cité — jamais Essentiel.

**Une nuance qui sauve en partie Essentiel** : les quatre points d'inclusion
affichés sur la page tarifaire (`offer.ts::INCLUDED` — carte saisie pour vous,
QR imprimés et livrés, équipe formée sur place, joignable pendant le service)
s'appliquent **à tous les paliers, Essentiel compris**. Le nouveau relevé
Tunisie confirme qu'**aucun des trois concurrents (Digital Menu, Scanny,
Menu-QR) n'offre d'accompagnement humain sur site, à aucun palier** — donc
même à 49 DT, Tawla vend autre chose que ce que vend Digital Menu Boost à 49
DT : moins de fonctionnalités logicielles (pas de fidélité, pas d'IA, pas de
marketing), mais un service que personne d'autre ne livre. C'est un axe de
valeur différent, pas un rabais déguisé — mais c'est un argument à
**démontrer**, pas à empiler sur un argument de prix qui, pour ce palier
précis, n'existe pas.

**Constat qui déborde du périmètre de cette incohérence, mais trouvé en la
tranchant** : `terrain/GUIDE_ENTRETIEN.md` (le script des 20 entretiens à
venir, Phase 21) pose encore la question de prix à **« 120 dinars par mois »**
— un montant qui ne correspond plus à aucun palier réel depuis le 26 août.
Ce fichier ne doit pas être modifié depuis une session (règle du projet), donc
non corrigé ici — mais c'est une correction à faire **avant** la première
sortie terrain, pas après : demander la volonté de payer sur un prix qui
n'existe plus rendrait la Phase 21 inutilisable. Voir §9.

### 2.2 « Ils vendent un lien vers un menu PDF » — faux littéralement, à reformuler

**Verdict : faux, pour les trois concurrents et à tous les paliers vérifiés,
y compris le moins cher.** Détail :

1. **Digital Menu Light (19 DT)** — pas un PDF statique : menu structuré,
   multilingue, produits illimités, modifiable en temps réel. La vraie nuance
   (⚠️ pas certaine à 100 %) est que la prise de commande n'apparaîtrait
   qu'à partir du palier Serveur (29 DT) — Light pourrait être consultation
   seule. C'est une nuance bien plus précise et défendable que « PDF ».
2. **Digital Menu Serveur/Commande à table/Boost (29-49 DT)** — commande
   réelle transmise en cuisine dès 29 DT, autonomie client dès 39 DT,
   fidélité + IA + marketing à 49 DT. Aucune lecture possible comme « juste un
   PDF ».
3. **Menu-QR** (positionné entrée de gamme en interne) — vraie commande
   client, vue cuisine tablette, rôles staff séparés. Pas un PDF non plus.
4. **Scanny** — module de caisse complet sur le palier Pro. Pas un PDF.

**Ce qui est vrai, et qui explique d'où vient le raccourci** : les trois sont
du **self-service SaaS pur**. Le restaurateur saisit sa carte dans un
back-office, le système génère le QR/PDF, et c'est à lui de l'imprimer (ou de
payer un supplément pour des cartes pré-imprimées). **Aucune source, pour
aucun des trois, ne mentionne un accompagnement humain sur site** — personne
qui vient créer les comptes, poser les QR, remettre les identifiants en main
propre. C'est très exactement ce que fait `setup_restaurant.py` côté Tawla.

**Correction recommandée** (dans ce document, pas dans `PREMIERES_VENTES.md`,
qui reste un instantané gelé du 14 août) : remplacer « ils vendent un lien
vers un menu PDF » par **« ce sont des outils en libre-service : le
restaurateur saisit sa carte et imprime ses QR lui-même, sans accompagnement
humain sur site »**. C'est la partie vérifiée et défendable de l'affirmation
d'origine — la différenciation réelle est dans le **service**, pas dans la
**richesse fonctionnelle**, où Digital Menu à 49 DT propose déjà autant, sinon
plus, de fonctionnalités logicielles que Tawla Essentiel au même prix (§2.1).

---

## 3. Le marché adressable, triangulé

| Source | Chiffre | Portée | Statut |
|---|---|---|---|
| Tuniscope (déjà cité en interne) | ~40 000 cafés | Cafés uniquement | Non-INS, déclaration syndicale pendant la pénurie de café 2022 |
| Espace Manager (2022) | 20 000 cafés « organisés » + 15-20 000 « anarchiques » ≈ 35-40 000 | Cafés uniquement | ⚠️ Même ordre de grandeur que Tuniscope, mais probablement la même source syndicale relayée par deux médias pendant la même crise — pas deux mesures indépendantes |
| **INS — Répertoire National des Entreprises**, via ilboursa.com | **43 832 entreprises** « hébergement et restauration », 2019 | Hôtels + cafés + restaurants (légère sur-couverture) | ✅ Meilleure source officielle trouvée — non lue directement (PDF INS bloqué), vue via un article relais |
| Idem, édition RNE plus récente | ~48 065 | Idem | ⚠️ Année d'édition non confirmée (2022 ou 2024 probable) |
| ONTT, *Tourisme en chiffres 2023* | **392** restaurants touristiques classés | Sous-catégorie très étroite, officielle | ✅ Précis mais ne capture ni cafés ni restaurants non classés |
| businessnews.com.tn (2026), Fédération tunisienne des restaurants touristiques | **397** établissements classés, ~20 000 emplois | Idem | Cohérent avec ONTT 2023 |

**Verdict** : l'estimation de ~40 000 cafés **tient en ordre de grandeur** —
corroborée par la seule vraie donnée officielle trouvée (INS/RNE, 43 832,
2019, même ordre de grandeur malgré un périmètre légèrement plus large).
Aucune source n'isole proprement « cafés + restaurants » avec un chiffre
récent et officiel : je retiens une fourchette **40 000 à 48 000**
établissements pour le marché large, avec **~40 000 comme estimation la plus
défendable pour « cafés seuls »** — cohérent avec ce que `REVUE_INVESTISSEURS.md`
et `AUDIT_FINAL.md` utilisaient déjà, donc **aucun changement du chiffre
central**, mais une fourchette honnête au lieu d'un point unique.

En appliquant le même filtre d'adressabilité hérité (× 6 %, non re-vérifié
dans cette étude — Wi-Fi fiable, clientèle smartphone, volume, grandes villes)
à cette fourchette : **≈ 2 400 à 2 900 établissements adressables**, contre
« ≈ 2 400 » cité jusqu'ici. Différence marginale, dans le bruit de la méthode.

---

## 4. France — Sunday revérifié, niche stress-testée

### 4.1 Sunday, chiffres actualisés — confirmé stable, avec un vrai trou d'information

**Rien de plus récent trouvé que l'annonce du 13 novembre 2025**, malgré une
recherche ciblée sur le T1/T2/été 2026 et les médias nommés (Les Echos, La
Tribune, Maddyness, BFM Business, Frenchweb). Recoupé sur 8+ sources
indépendantes (Boursorama, FrenchWeb, Businesswire, Yahoo Finance, La Tribune
de l'Hôtellerie, Maddyness, Snacking.fr, L'Hôtellerie-Restauration) :

- **Série B : 21 M$ / 18 M€, annoncée le 13/11/2025**, menée par DST Global
  Partners.
- Échelle revendiquée (chiffres de l'annonce, republiés depuis sans mise à
  jour visible) : **3 000+ restaurants** (~1 500 France, ~1 000 US, le reste
  UK), **80 M+ convives**, **4 Md$+ de volume de paiement annuel**, croissance
  ×3 du CA en 12 mois, ~200 salariés.
- **Financement cumulé depuis la création ≈ 145 M$** : seed 24 M$ (avril
  2021), série A 100 M$ (septembre 2021, confirmée TechCrunch), série B 21 M$
  (novembre 2025). Aucune série C trouvée pour 2026.
- Plans 2026 annoncés en novembre 2025 : nouvelles villes françaises et
  américaines, **premier déploiement Moyen-Orient à Dubaï**, menus dynamiques
  IA, 300+ bornes en libre-service, programme de fidélité, marque blanche.

**Point de vigilance, à noter explicitement** : Sunday avait annoncé vouloir
**doubler taille, clients et adoption d'ici l'été 2026**. Nous sommes le
28/08/2026 — **aucun bilan de cet objectif n'a été trouvé**, ni confirmation
ni contradiction. C'est un vrai trou d'information (le marché n'a pas
communiqué depuis 9 mois sur ce point précis), pas une preuve que l'objectif
a été manqué.

⚠️ Un article circulant mentionne « 100 M$ » et pourrait laisser croire à une
levée récente : vérifié, c'est la série A de **2021**, pas un tour 2026
(confirmé par TechCrunch daté).

### 4.2 La niche maghrébine bilingue — hypothèse fragilisée, ni confirmée ni réfutée

**Aucun produit basé en France ne combine QR + arabe + Ramadan/iftar +
positionnement maghrébin/halal explicite** — sur ce point précis étroit,
l'hypothèse résiste à la recherche de contre-exemples directs. Mais deux
choses affaiblissent l'idée d'un boulevard vide :

1. **La combinaison existe déjà juste à côté** — Golfe (TableQR, DG Menus) et
   Maroc (Mymenu.ma) — preuve que ce n'est pas inédit, seulement pas encore
   arrivé en France.
2. **Le public cible est déjà un segment reconnu et servi en France**, sur des
   briques adjacentes : **Mon Resto' Halal** (annuaire, 3 000+ restaurants
   halal référencés), **Hal'Rezo** (réservation + commande + fidélité, ~100
   établissements halal en Île-de-France — statut d'activité 2026 non
   confirmé, à vérifier à la main avant la Phase F1), et surtout **Temtem
   One** — super-app née en Algérie, qui livre **déjà** des repas de
   restaurants et traiteurs maghrébins à la diaspora en France depuis mai
   2021, avec une dynamique multi-services. C'est l'acteur le plus concret
   trouvé : il a déjà l'audience, la marque et la logique produit pour ajouter
   une brique « commande à table » avant Tawla, même si rien n'indique qu'il
   le projette aujourd'hui.

**Nuance importante pour le positionnement** : plusieurs outils de menu QR
généralistes (CarteMenu.app, Menu Touch, MenuCarta…) proposent déjà l'arabe
comme une langue de traduction parmi beaucoup d'autres. **« Avoir un menu en
arabe » n'est donc plus un différenciateur en soi** — n'importe quel
restaurant français peut l'obtenir avec un outil généraliste. Ce qui reste
différenciant, si ça l'est, c'est l'**identité bilingue assumée + le mode
Ramadan + le positionnement communautaire** — pas la simple présence de la
langue. Aucun des huit acteurs vérifiés nommément (Sunday, idmenu.fr,
L'Addition, Zelty, Lightspeed, Innovorder, Popina, Tiller/SumUp) n'a de trace
d'interface arabe ou de fonctionnalité Ramadan.

### 4.3 Taille de la niche — pas de source directe, seulement des proxys

Ni l'INSEE (la nomenclature NAF ne classe les restaurants que par format de
service, jamais par cuisine ou origine de clientèle — confirmé sur la
nomenclature nafr2 division 56), ni une fédération dédiée, ni une étude grand
public ne comptent directement « les restaurants maghrébins en France ».
Proxys trouvés, aucun ne répondant vraiment à la question :

| Proxy | Ordre de grandeur | Limite |
|---|---|---|
| Marché halal global (tous canaux) | 5,5-10 Md€ (~7 Md€ dans plusieurs analyses 2026) | Inclut distribution/agroalimentaire, pas seulement restauration |
| Restauration rapide halal | ≈ 1,7 Md€ | ⚠️ Source unique, non recoupée |
| Points de vente kebab | 9 000-11 000 | Cuisine turque à l'origine, pas maghrébine |
| Restaurants halal référencés (Mon Resto' Halal) | 3 000+ | Auto-déclaré, toutes cuisines halal confondues |

**Fourchette honnête** : de quelques milliers à un peu plus de 10 000
établissements selon la définition retenue — mais **aucun chiffre de cette
liste ne vient d'un décompte fait pour répondre à cette question précise**.
Si ce nombre doit fonder un business case, la recommandation est de le
construire soi-même (extraction SIRENE/API Entreprise par mots-clés de
dénomination, ou comptage manuel Google Maps par catégorie et par ville)
plutôt que d'emprunter un chiffre agrégé hors périmètre.

---

## 5. Matrice comparative

### 5.1 Tunisie

| | DM Light 19DT | DM Serveur 29DT | DM Commande à table 39DT | DM Boost 49DT | Scanny (prix ND) | Scanny Pro (prix ND) | Menu-QR (prix ND) | **Tawla Essentiel 49DT** | **Tawla Pro 89DT** | **Tawla Business 149DT** |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Menu QR multilingue | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ND | ✅ fr/ar | ✅ | ✅ |
| Commande serveur → cuisine | ⚠️ND | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Commande autonome client | ❌ | ⚠️ND | ✅ | ✅ | ND | ND | ✅ | ✅ | ✅ | ✅ |
| Écran cuisine temps réel | ⚠️ND | probable | probable | ✅ | ND | ND | ✅ tablette | ✅ | ✅ | ✅ |
| Paiement carte | ND | ND | ND | ND | ND | ✅ (caisse propre) | ❌ | ❌ | ✅ | ✅ |
| Fidélité | ❌ | ⚠️ND | ⚠️ND | ✅ | ND | ND | ❌ | ❌ | ✅ | ✅ |
| Vente incitative **mesurée** | ❌ | ❌ | ❌ | ❌ (marketing IA, non mesuré) | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Plan de salle visuel | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Mode Ramadan / iftar | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Page de preuve chiffrée (avant/après) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Rapport par serveur / base de prime | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Installation humaine sur site | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Homologation fiscale NACEF (caisse) | s.o. | s.o. | s.o. | s.o. | ND | ⚠️ND | s.o. | à vérifier §8 | à vérifier §8 | à vérifier §8 |
| **Prix/mois** | 19 DT | 29 DT | 39 DT | 49 DT | ND | ND | ND | **49 DT** | **89 DT** | **149 DT** |

*(ND = non trouvé malgré recherche ciblée ; ⚠️ND = trouvé mais non confirmé
avec certitude ; s.o. = sans objet, la fonctionnalité n'existe pas donc la
question ne se pose pas.)*

Lecture : sur les fonctionnalités logicielles seules, Tawla Essentiel est
strictement moins riche que Digital Menu Boost au même prix (§2.1). L'écart se
crée à partir de Pro, et la ligne la plus défendable — le rapport par serveur
— n'existe **nulle part ailleurs dans ce tableau**, et seulement à partir de
Business côté Tawla.

### 5.2 France (version plus légère — aucun prix Tawla annoncé publiquement)

| | Sunday | idmenu.fr | Systèmes de caisse installés (L'Addition, Zelty, Lightspeed, Innovorder, Popina, Tiller/SumUp) | Tawla France (hypothèse F3, non validée) |
|---|---|---|---|---|
| Catégorie | Paiement/checkout QR à table | Menu digital QR | Caisse certifiée NF525, déjà amortie | Commande à table QR + cuisine + serveur |
| Prix | ⚠️ND — modèle probablement volume/transaction, pas un abonnement SaaS classique trouvé | 25-35 €/mois | Variable, déjà payé | 49/89/149 € (jamais annoncé, cf. `markets.py` — « pas avant validation F1 ») |
| Interface arabe | ❌ non trouvée | ⚠️ND | ❌ non trouvée | ✅ déjà codée |
| Mode Ramadan / iftar | ❌ non trouvé | ⚠️ND | ❌ non trouvé | ✅ déjà codé |
| Déploiement terrain | ✅ commerciaux + équipes de déploiement | ⚠️ND | ✅ marché mature | À re-dériver — le modèle « fondateur seul » tunisien ne transpose pas tel quel (`MARCHE_FRANCE.md` §1) |
| Blocage NF525 | Concerné s'il enregistre des règlements | Concerné si commande = règlement | Déjà conformes | À trancher en Phase F2 (déjà identifié) |

---

## 6. Positionnement

### 6.1 Énoncé canonique — Tunisie (cible prioritaire : restaurants et brasseries de 6 tables et plus)

> Pour les restaurants et brasseries tunisiens de 6 tables et plus (Tunis, La
> Marsa, Sousse, Hammamet), qui perdent des commandes — et de l'argent — à
> chaque coup de feu sans jamais pouvoir le prouver, **Tawla est le service de
> commande par QR code livré avec un accompagnement humain sur place** —
> carte saisie pour vous, QR imprimés et livrés, équipe formée sur place,
> joignable pendant le service — **qui élimine les commandes oubliées et
> transforme chaque service en chiffres** (commandes perdues, délai
> commande → cuisine, panier moyen, performance par serveur). Contrairement à
> **Digital Menu, Scanny et Menu-QR** — trois outils en libre-service où le
> restaurateur saisit sa carte, imprime ses QR et se débrouille seul —
> **Tawla ne vend pas un logiciel, elle vend quelqu'un qui vient**, forme
> l'équipe pendant un service réel, et reste joignable un vendredi soir.

Cet énoncé ne tient, prix à l'appui, que pour les paliers **Pro** et
**Business** (§2.1) — jamais Essentiel, dont le seul argument défendable est
le service inclus, pas l'écart de prix.

### 6.2 Variante courte — niche France (secondaire, hypothèse non validée sur le terrain)

> Pour les restaurants et salons de thé en France à clientèle maghrébine, qui
> ne trouvent dans aucune solution installée une expérience pensée pour leur
> carte et leur calendrier, Tawla est la commande à table par QR déjà
> bilingue français/arabe, avec mode Ramadan et pré-commande iftar —
> contrairement à **Sunday**, qui arrive en force commerciale mais sans
> spécificité communautaire.

À qualifier systématiquement, tant que la Phase F1 (entretiens France) n'a
pas eu lieu : l'hypothèse n'est pas réfutée par un concurrent direct (§4.2),
mais deux acteurs adjacents — **Temtem One** (livraison, déjà en France
depuis 2021) et **Hal'Rezo** (réservation/commande/fidélité, statut 2026
incertain) — montrent que le public est déjà identifié par d'autres, sans
qu'aucun n'ait construit la commande à table elle-même. Ce n'est donc ni un
boulevard vide ni un segment déjà perdu — une hypothèse à tester, pas un fait.

---

## 7. Les trois paliers restent-ils défendables ? (skill `pricing`)

Cadre appliqué : le prix doit se situer entre la **meilleure alternative**
(plancher) et la **valeur perçue** (plafond) — jamais fondé sur le coût de
revient. Ici, la meilleure alternative vérifiée est Digital Menu (le seul
concurrent avec des prix publics confirmés).

**Essentiel (49 DT) — défendable uniquement sur le service, pas sur le prix.**
Positionné à parité stricte avec le palier le plus riche de Digital Menu
(§2.1). Sur une comparaison fonctionnalité-pour-fonctionnalité, un visiteur
qui compare les deux pages tarifaires sans valeur accordée à l'installation
humaine voit un Tawla moins complet **au même prix**. Risque concret : ce
palier est celui affiché en premier sur la page tarifaire publique
(`frontend/lib/offer.ts`), visible par n'importe quel visiteur non accompagné
— y compris les petits cafés que la cible commerciale exclut déjà sur le
terrain. Le risque est donc plus **un problème de cohérence de la page
publique** qu'un problème de vente active (si Essentiel n'est en pratique
jamais cité en entretien face à un prospect 6 tables et plus).

**Pro (89 DT) — défendable.** ×1,8 à ×4,7 vs la fourchette Digital Menu, avec
une réelle avance fonctionnelle vérifiée à ce prix (vente incitative
**mesurée**, page de preuve chiffrée, mode Ramadan) — deux différenciateurs
qu'aucun concurrent tunisien vérifié ne possède, à aucun palier.

**Business (149 DT) — le plus défendable, et le plus cohérent avec le
narratif de vente existant.** ×3 à ×7,8 vs Digital Menu, et surtout : le
**rapport par serveur / base de prime** — LE différenciateur le plus souvent
cité comme argument de direction dans `REVUE_INVESTISSEURS.md` et
`PREMIERES_VENTES.md` pour la cible 6 tables et plus — n'existe **qu'à ce
palier** côté Tawla, et **chez aucun concurrent tunisien vérifié, à aucun
palier**. C'est la version la plus propre de l'ancien narratif « pas
comparable » : ici, il l'est réellement.

**Ce que je recommande d'écrire pour Wassim, sans rien changer dans le code :**

1. **Ne jamais citer un prix Tawla unique** en entretien ou en argumentaire —
   toujours nommer le palier. Pour la cible 6 tables et plus, ancrer la
   comparaison sur **Business**, où l'écart de prix et l'écart fonctionnel
   pointent dans le même sens.
2. **Essentiel mérite un arbitrage** : soit assumer qu'il ne sera jamais
   vendu à la cible actuelle et vivre avec l'incohérence de la page publique
   (elle ne s'adresse pas à un visiteur qui compare des tableaux, mais à un
   prospect qu'on accompagne), soit revoir sa mise en avant sur la page
   tarifaire (ex. ne plus l'afficher en premier, ou reformuler sa proposition
   de valeur autour du service plutôt que du prix). Ce n'est **pas** une
   recommandation de changer son prix — c'est une question de message, laissée
   à Wassim.
3. **Aucune recherche de volonté de payer n'a encore eu lieu** sur ces trois
   montants (49/89/149 DT décidés le 26 août, Phase 21 — les 20 entretiens —
   pas encore lancée au 28 août). `REVUE_INVESTISSEURS.md` §3.5 qualifiait déjà
   l'ancien prix unique d'« optimisation prématurée, aucun client payant » ;
   le même constat s'applique aux trois paliers actuels tant que les
   entretiens n'ont pas eu lieu. Ce n'est pas une raison de retarder la Phase
   21 — c'est exactement ce à quoi elle sert (question de prix posée
   franchement, `terrain/GUIDE_ENTRETIEN.md` Q4) — mais la question doit être
   reposée avec les **bons montants** (§2.1, §9).
4. **France non évaluable sur le prix aujourd'hui.** Le modèle tarifaire de
   Sunday (le concurrent principal) n'a pas pu être établi — probablement pas
   un abonnement SaaS classique, plutôt un modèle volume/transaction, ce qui
   rend toute comparaison directe avec un abonnement fixe hasardeuse.
   idmenu.fr (25-35 €/mois) serait, lui, moins cher que même Essentiel
   (49 €/mois hypothèse) — cohérent avec la note déjà présente dans
   `core/markets.py` : ces montants sont une hypothèse de départ, **pas à
   annoncer publiquement avant validation en Phase F1**. Rien à corriger ici,
   la garde-fou existant est déjà le bon.

---

## 8. Un risque trouvé en marge de cette étude, hors périmètre à trancher ici

En vérifiant le module « caisse connectée » de Scanny (§1.2), cette recherche
a découvert que la Tunisie impose depuis le **1er novembre 2025**
(généralisation au **1er juillet 2026**) une **homologation NACEF**
obligatoire pour tout logiciel de caisse utilisé par les cafés/restaurants —
un mécanisme qui rappelle directement le NF525 français déjà identifié comme
bloquant potentiel dans `MARCHE_FRANCE.md` §3.1. Tawla enregistre déjà des
règlements (espèces, carte via Konnect) sur son marché tunisien. **Cette
étude n'a pas vérifié si Tawla entre dans le champ de la NACEF** — c'est hors
du périmètre concurrentiel qui lui était fixé, et la question est d'ordre
réglementaire, pas commercial. Signalé ici pour que Wassim décide s'il faut
ouvrir une vérification dédiée, sur le modèle de ce que `MARCHE_FRANCE.md`
§3.1 a fait pour le NF525.

---

## 9. Ce qui reste à Wassim

- **Valider cette synthèse** avant qu'elle infuse un vrai rendez-vous ou les
  20 entretiens de la Phase 21.
- **Trancher le prix cité en entretien** : cette étude recommande Pro (89 DT)
  ou Business (149 DT) selon le profil du restaurant, jamais Essentiel ni
  l'ancien « 120 dinars ». `terrain/GUIDE_ENTRETIEN.md` Q4 cite encore 120 DT
  — à corriger à la main avant la première sortie terrain (non fait ici, ce
  fichier ne se modifie pas depuis une session).
- **Arbitrer Essentiel** sur la page tarifaire publique (§7, point 2) — rien
  n'a été changé dans le code.
- **Décider si la niche France mérite d'être creusée plus tôt que prévu** :
  cette étude recommande de **ne pas accélérer** — l'hypothèse est fragilisée,
  pas invalidée, et `MARCHE_FRANCE.md` §1 (scénario B) reste le bon plan.
  Ajouter en revanche **Temtem One** à la veille concurrentielle F1, et
  vérifier à la main le statut 2026 de Hal'Rezo avant d'écrire quoi que ce
  soit de définitif sur cette niche.
- **Décider si la question NACEF (§8) mérite une vérification dédiée** avant
  la mise en avant commerciale du paiement carte Tawla en Tunisie.

---

## Sources

Toutes consultées le **2026-08-28**, exclusivement via `WebSearch` (`WebFetch`
bloqué pour tous les domaines testés sans exception, y compris des domaines de
contrôle neutres — voir §0). Le symbole ⚠️ marque une affirmation non
confirmée par recoupement indépendant ou provenant d'une source de fiabilité
incertaine.

**Tunisie — concurrents** : digitalmenu.tn (`/prix-tarif-menu-digital-qr-code`,
`/fonctionnalites-menu-digital-qr-code`, `/faq`, `/fonctionnalites/gestion-multi-entreprise-restaurant`,
`/fonctionnalites/menu-ia-intelligent`, `/fonctionnalites/happy-hour`) ·
scanny.tn (inaccessible, DNS) · menu-qr.tn · maghqr.net · menu.clpr.tn ·
feadys.com / scan.feadys.com · ⚠️ magstartup.com (« Menu QR Restaurant Afrique
du Nord : Top 10 Solutions 2026 ») · asmpos.com, innovasoft-web.com,
megasofterp.com, caisses.tn (éditeurs de caisse tunisiens).

**NACEF** : homologation.nacef.tn · webmanagercenter.com
(2025-11-04, « Tunisie : caisses enregistreuses fiscales, l'État branche les
cafés et restaurants au contrôle automatique ») · managers.tn (2026-06-30,
« Tunisie : caisses enregistreuses obligatoires dès demain pour ces
structures »).

**Marché tunisien** : tuniscope.com/article/357077 (déjà cité en interne) ·
espacemanager.com (pénurie café/sucre 2022) · ilboursa.com (relais INS/RNE,
43 832 entreprises) · ins.tn (RNE 2020 et 2024, PDF non ouverts) ·
managers.tn/2025/06/04 (statistiques entreprises Tunisie) ·
ontt.tn (Tourisme en chiffres 2023) · businessnews.com.tn/2026/07/01
(restaurants touristiques classés) · lapresse.tn/2024/10/26 (Chambre nationale
des cafetiers).

**Sunday — financement** : boursorama.com (13/11/2025, déjà cité en interne)
· lhotellerie-restauration.fr · frenchweb.fr · maddyness.com (12/11/2025) ·
latribunedelhotellerie.com · snacking.fr · neorestauration.com ·
fintech.global · finance.yahoo.com · businesswire.com (13/11/2025) ·
sundayapp.com/an-inside-look-at-our-series-b · techcrunch.com (14/04/2021 seed,
22/09/2021 série A) · usine-digitale.fr · tendancehotellerie.fr ·
pitchbook.com · tracxn.com.

**France — arabe/Ramadan/halal** : idmenu.fr (déjà cité en interne, prix) ·
cartemenu.app · doxmenu.com · menu-touch.fr · menucarta.app · mymenu.ma ·
tableqr.co (Ramadan Golfe) · dgmenus.com (Golfe) · shopcaisse.com ·
restofast.com · revofrance.fr · ⚠️ magstartup.com (même réserve que ci-dessus).

**Acteurs halal/maghrébins France** : mon-resto-halal.com + App Store ·
Hal'Rezo (Google Play ; maddyness.com 23/01/2018 ; ajib.fr) · temtem
(Google Play ; uptodown.com) · argml.com · App Store « Koul Halal » ·
startup-muslim.com (⚠️ chiffre 1,7 Md€ non recoupé).

**Taille marché halal France** : agroligne.com · lessentieldeleco.fr ·
toute-la-franchise.com · planetoscope.com (halal et kebab) ·
lexpress-franchise.com · club-sandwich.net · insee.fr (fiche secteur 561 et
nomenclature nafr2 division 56) · xerfi.com (pâtes/couscous, non exploitable).

**Avertissement** : rien de ce qui précède n'est un avis juridique. Le point
NACEF (§8) doit être confirmé par une vérification dédiée avant toute décision
qui en dépend.
