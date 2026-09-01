/**
 * Conditions générales de vente — CGV SaaS B2B (marché France).
 *
 * BROUILLON — texte fourni par Wassim en attente de validation par un
 * professionnel avant mise en ligne définitive. Les placeholders entre
 * crochets (durées, taux, seuils) sont intentionnels : ne pas inventer de
 * valeur.
 *
 * Régit l'abonnement du Client professionnel (le restaurant), à la
 * différence des CGU (`cgu.ts`) qui couvrent tout utilisateur. Renvoie vers
 * le DPA (`dpa.ts`, page `/dpa`) pour la sous-traitance RGPD.
 */

type Section = { title: string; paragraphs?: string[]; list?: string[] };
type CgvPage = { title: string; intro: string; sections: Section[] };

export const CGV: CgvPage = {
  title: "Conditions générales de vente (CGV)",
  intro:
    "Préambule : Régissent la relation contractuelle entre l'éditeur (« le Prestataire ») et tout restaurant professionnel souscrivant un abonnement au Service Tawla (« le Client »). S'appliquent à l'exclusion de toutes autres conditions, notamment celles du Client.",
  sections: [
    {
      title: "1. Objet",
      paragraphs: [
        "Fourniture au Client d'un accès à la plateforme logicielle Tawla en mode SaaS, incluant la gestion des commandes, de la carte, du personnel et, en option, l'intégration d'un dispositif d'encaissement des paiements de la clientèle du restaurant via Stripe Connect.",
      ],
    },
    {
      title: "2. Description du Service",
      paragraphs: [
        "[à affiner selon l'offre réelle — gestion de commandes, carte, personnel, tableau de bord, module de paiement optionnel].",
      ],
    },
    {
      title: "3. Prix et modalités de paiement",
      paragraphs: [
        "Le Service est facturé selon la formule d'abonnement souscrite, indiquée dans le bon de commande ou l'interface de souscription. Prix exprimés hors taxes, la TVA n'étant pas applicable tant que le Prestataire bénéficie de la franchise en base de TVA (art. 293 B CGI) — mention à retirer si le seuil est dépassé.",
        "Conformément à l'article L. 441-10 du Code de commerce, tout retard de paiement entraîne de plein droit, outre les pénalités de retard au taux [à fixer — minimum légal : taux BCE + 10 points], une indemnité forfaitaire pour frais de recouvrement de 40 €, sans préjudice d'une indemnisation complémentaire sur justificatif.",
      ],
    },
    {
      title: "4. Durée et résiliation",
      paragraphs: [
        "Abonnement souscrit pour une durée de [à définir], renouvelable par tacite reconduction sauf résiliation notifiée avec un préavis de [à définir]. Résiliation immédiate possible en cas de manquement grave d'une partie non corrigé dans un délai de [à définir] après mise en demeure.",
      ],
    },
    {
      title: "5. Obligations du Client",
      paragraphs: [
        "Le Client s'engage à utiliser le Service conformément aux CGU, à fournir les informations nécessaires à son paramétrage, et à respecter ses propres obligations légales vis-à-vis de sa clientèle (droit de la consommation, facturation).",
      ],
    },
    {
      title: "6. Paiement des clients du restaurant (module Stripe Connect)",
      paragraphs: [
        "Lorsque le Client active le module de paiement, il contracte directement avec Stripe en qualité de marchand (« merchant of record »). Le Prestataire n'est à aucun moment dépositaire des fonds versés par la clientèle du Client et n'intervient qu'en qualité de fournisseur de la solution logicielle d'intégration. Les frais applicables (Stripe Connect) sont ceux communiqués par Stripe et peuvent évoluer indépendamment du Prestataire.",
      ],
    },
    {
      title: "7. Garanties et responsabilité",
      paragraphs: [
        "Le Prestataire s'engage à fournir le Service avec diligence, sans garantir l'absence totale d'erreurs ou d'interruptions. Sa responsabilité, toutes causes confondues, est plafonnée au montant versé par le Client au titre des [douze / à définir] derniers mois. Sont exclus les dommages indirects, pertes d'exploitation, de clientèle ou de données imputables à un tiers (Stripe, hébergeur).",
      ],
    },
    {
      title: "8. Protection des données à caractère personnel",
      paragraphs: [
        "Le traitement de données à caractère personnel réalisé pour le compte du Client fait l'objet d'un Contrat de sous-traitance distinct (DPA), conforme à l'article 28 du RGPD — voir la page /dpa.",
      ],
    },
    {
      title: "9. Propriété intellectuelle",
      paragraphs: [
        "Le Service, ses logiciels, bases de données et documentation restent la propriété exclusive du Prestataire. Le Client bénéficie d'un droit d'usage non exclusif, non cessible, limité à la durée du contrat.",
      ],
    },
    {
      title: "10. Force majeure",
      paragraphs: [
        "Aucune partie ne peut être tenue responsable d'un manquement dû à un cas de force majeure au sens de l'article 1218 du Code civil.",
      ],
    },
    {
      title: "11. Droit applicable et litiges",
      paragraphs: [
        "Droit français. Recherche d'une solution amiable avant toute action judiciaire ; à défaut, tribunaux compétents du ressort du siège du Prestataire, sauf disposition d'ordre public contraire.",
      ],
    },
  ],
};
