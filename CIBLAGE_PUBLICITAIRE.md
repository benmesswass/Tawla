# Ciblage publicitaire — Horizon 1 (rendez-vous qualifiés)

*Rédigé le 2026-08-28. Prêt à activer par Wassim — aucun compte publicitaire
n'a été créé, aucune dépense engagée. Champ d'application : uniquement
l'Horizon 1 (sept. 2026 – janv. 2027, pendant les Phases 21 et 23 de
`ROADMAP.md`). La vraie campagne publique de l'Horizon 2 (Ramadan, avec des
chiffres de pilotes réels) est un document séparé, pas encore écrit — voir
`CAMPAGNE_MARKETING.md`.*

## Un seul objectif, pas deux

**Produire des rendez-vous qualifiés en personne, jamais des inscriptions en
ligne.** Rien ici ne pointe vers `/signup`. Ce plan ne remplace jamais la
tournée à pied de `terrain/GUIDE_ENTRETIEN.md` (40 adresses, créneau
15h-17h mardi-jeudi) — il la précède de quelques jours, dans le même
quartier, pour qu'un patron ait déjà vu le nom une fois avant que Wassim
toque à sa porte (effet de simple exposition : on ouvre plus facilement à un
nom déjà croisé).

Budget volontairement petit. Si le coût par rendez-vous qualifié dépasse ce
qu'une sortie à pied produit pour le même temps, arrêter — ce n'est pas la
stratégie qui doit s'adapter au budget, c'est le budget qui doit prouver sa
place à côté de la stratégie qui marche déjà.

## Plateforme : Meta (Facebook + Instagram), pas LinkedIn, pas Google

- **LinkedIn écarté** : les gérants de restaurants indépendants n'y
  maintiennent quasiment jamais de profil professionnel à jour, et le
  ciblage par intitulé de poste LinkedIn suppose une donnée qu'ils ne
  renseignent pas. LinkedIn cible juste des décideurs d'entreprise qui
  utilisent LinkedIn — ce n'est pas ce public.
- **Google Search écarté pour l'instant** : suppose un volume de recherche
  (« logiciel commande restaurant Tunisie ») qui reste à prouver — les trois
  concurrents investissent peu en SEO/SEA visible. Tant qu'aucune preuve de
  volume n'existe, un budget de test y est un pari à l'aveugle, pas un
  ciblage. À reconsidérer si `CANAUX_ACQUISITION.md` ou une recherche
  ultérieure prouve un volume réel.
- **Meta retenu** : présence massive des petits commerçants tunisiens sur
  Facebook (page pro, groupes), ciblage géographique fin par lieu + rayon
  disponible nativement, et un **formulaire Lead natif** permet de qualifier
  sans construire ni héberger de page d'atterrissage — zéro dépendance au
  code du site, zéro pixel à poser.

## Mécanisme de qualification : formulaire Lead Meta, pas une landing page

Un **formulaire Lead** (Meta Ads Manager → objectif « Prospects ») posé
directement dans la publicité. Trois questions, dans cet ordre — les deux
premières disqualifient avant même que Wassim ne rappelle :

1. **« Combien de tables avez-vous ? »** — choix : *Moins de 6* / *6 à 15* / *Plus de 15*
2. **« Vos clients ont-ils du wifi ou du réseau à toutes les tables ? »** — *Oui* / *Non* / *Je ne sais pas*
3. **« Votre ville »** — *Tunis* / *La Marsa* / *Sousse* / *Hammamet* / *Autre*

Champs de contact Meta standard (nom, téléphone) pré-remplis par la
plateforme. Une réponse « Moins de 6 » ou « Non » au wifi ne s'élimine pas
automatiquement (Meta ne permet pas de branchement conditionnel natif), mais
donne à Wassim, avant de décrocher le téléphone, exactement l'information de
`ARGUMENTAIRE_RESTAURATEUR.md` §5 pour disqualifier tout de suite ou non.
Les leads se relèvent depuis Meta Ads Manager ou un export CSV — aucune
intégration technique requise.

## Ciblage

**Zone : lieu + rayon, jamais la Tunisie entière**, synchronisé avec la
ville où Wassim marche cette semaine-là (cf. Calendrier) :

| Ville | Centre du rayon (recherche « Lieu » Meta) | Rayon |
|---|---|---|
| Tunis | « Tunis Centre, Tunisie » (+ un second pin « Les Berges du Lac, Tunis » si le budget de la vague le permet) | 3 km |
| La Marsa | « La Marsa, Tunisie » | 3 km |
| Sousse | « Sousse Centre, Tunisie » | 4 km |
| Hammamet | « Hammamet, Tunisie » | 5 km (couvre Hammamet Sud/Yasmine) |

**Âge / genre :** 28-58 ans, tous genres — tranche réaliste d'un
gérant/propriétaire de restaurant indépendant, ni trop jeune (peu de gérants
propriétaires) ni trop âgé (peu actifs sur Meta).

**Ciblage détaillé (à combiner, pas à empiler tous en même temps — tester
séparément) :**
- Comportement Meta **« Administrateurs de Page »** (proxy le plus fiable pour « dirige un commerce ayant une présence Facebook »), filtré si l'outil le permet sur des Pages de catégorie restaurant/café.
- Centres d'intérêt : « Restaurant management », « Hôtellerie-restauration », « Petite entreprise », « Restaurateur ».
- Intitulé de poste (si le champ est disponible sur le compte) : « gérant de restaurant », « propriétaire de restaurant », « restaurateur ».

**Placements :** Facebook + Instagram, Feed et Stories, **mobile uniquement**
— exclure Audience Network et Messenger placement automatique (bruit, pas ce
public).

**Exclusions :** aucun client existant à exclure aujourd'hui (zéro client).
Prévoir l'exclusion dès le premier pilote signé, pour ne jamais payer pour
réatteindre quelqu'un déjà engagé.

## Créas — qualifier, jamais séduire

Trois angles, testés en parallèle à petit budget égal, jamais un seul remis
en avant avant d'avoir un signal.

**Angle 1 — la question qui fait mal (perte)**

> Un vendredi soir plein, combien de commandes se perdent entre la salle et
> la cuisine chez vous ?
> On vient chez vous, on installe, on forme votre équipe — pas un logiciel à
> configurer seul.
> **CTA : Demander un rendez-vous**

**Angle 2 — la différenciation service**

> On ne vous envoie pas un lien à paramétrer seul. On vient avec votre
> carte, on installe, on forme votre équipe pendant un vrai service, et on
> reste joignable le vendredi soir.
> **CTA : Demander un rendez-vous**

**Angle 3 — la rareté (pilote)**

> Je cherche 3 restaurants à [Ville] pour tester gratuitement, 4 semaines,
> installation et formation comprises. Wifi correct en salle.
> **CTA : Demander un rendez-vous**

Visuel : pas de maquette léchée — une photo simple d'un chevalet QR posé sur
une vraie table, ou l'écran serveur en usage. La sincérité artisanale du
positionnement (`.agents/product-marketing.md` § Brand Voice) doit se voir
dans la créa, pas seulement se lire dans le texte.

## Budget et calendrier — calé sur la tournée à pied, pas sur Ramadan

Trois vagues de test, chacune dans la ville que Wassim démarche à pied
cette période-là (`terrain/GUIDE_ENTRETIEN.md` : deux sorties/semaine, trois
semaines pour vingt entretiens — dater les vagues une fois l'ordre réel des
villes connu sur le terrain).

| Vague | Ville | Durée | Budget/jour | Budget total vague |
|---|---|---|---:|---:|
| 1 | Tunis + La Marsa | 10 jours | 15 DT | 150 DT |
| 2 | Sousse | 8 jours | 15 DT | 120 DT |
| 3 | Hammamet + reciblage des leads non convertis des vagues 1-2 | 8 jours | 15 DT | 120 DT |
| **Total Horizon 1** | | ~26 jours de diffusion, étalés sur sept. 2026 – janv. 2027 | | **≈ 390 DT** |

Le reciblage de la vague 3 vise l'audience personnalisée « a ouvert le
formulaire sans le finir » — budget inclus dans les 120 DT, pas un ajout.

**Ne jamais lancer les trois villes en même temps** : le budget est pensé
pour rester lisible ville par ville et se couper immédiatement si le coût
par rendez-vous qualifié dérape (cf. métrique de succès ci-dessous) sans
avoir englouti tout le test d'un coup.

## Métrique de succès — un rendez-vous, pas un clic

La seule métrique qui compte : **coût par rendez-vous qualifié réellement
obtenu** (pas coût par lead, pas CTR, pas CPM — des métriques vanity pour cet
objectif). Un lead qui ne correspond pas au profil visé n'est pas qualifié,
même s'il coûte le même CPM que les autres.

**Seuil d'arrêt :** si le coût par rendez-vous qualifié dépasse ce qu'une
sortie à pied produit pour un temps équivalent (ordre de grandeur : une
sortie à pied produit 2-3 entretiens en une demi-journée, sans coût
monétaire direct — la comparaison honnête est donc le temps, pas seulement
les dinars), couper la vague en cours et ne pas reconduire, plutôt que
d'espérer que la suivante corrige le tir.

## Prérequis avant d'activer (🧑, à Wassim seul)

- Business Manager Meta + Page Facebook Tawla existante et publiée.
- Moyen de paiement posé sur le compte publicitaire.
- Revue finale des trois textes de créa et du visuel choisi.
- Vérifier que le formulaire Lead exporte bien vers un endroit consulté (e-mail de notification Meta activé, ou export manuel régulier — pas de CRM à construire pour ce volume).
- Poser les plafonds de budget quotidien indiqués ci-dessus avant publication, pas après.

## Ce que ce plan ne couvre pas

- **L'Horizon 2 (Ramadan)** : campagne publique à budget réel, appuyée sur
  des chiffres de pilotes mesurés — nécessite que `PILOT_RESULTS` ne soit
  plus vide. Document séparé, à écrire une fois les pilotes conclus (cf.
  `CAMPAGNE_MARKETING.md`).
- **Tout ciblage grand public** — hors sujet tant que la stratégie reste la
  vente en personne à une cible étroite.
