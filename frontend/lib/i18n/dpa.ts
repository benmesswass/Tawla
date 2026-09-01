/**
 * Contrat de sous-traitance RGPD — DPA, article 28 du RGPD (marché France).
 *
 * BROUILLON — texte fourni par Wassim en attente de validation par un
 * professionnel avant mise en ligne définitive. Les placeholders entre
 * crochets sont intentionnels : ne pas inventer de valeur.
 *
 * Référencé depuis les CGV (`cgv.ts`, section 8) pour les Clients
 * professionnels (restaurants) au titre de leur qualité de Responsable de
 * traitement.
 */

type Section = { title: string; paragraphs?: string[]; list?: string[] };
type DpaPage = { title: string; intro: string; sections: Section[] };

export const DPA: DpaPage = {
  title: "Contrat de sous-traitance de données personnelles (DPA)",
  intro:
    "Entre le Client (restaurant utilisateur du Service), Responsable de traitement, et l'éditeur, Sous-traitant, en application de l'article 28 du Règlement (UE) 2016/679.",
  sections: [
    {
      title: "1. Objet et durée",
      paragraphs: [
        "Encadre le traitement de données à caractère personnel réalisé par le Sous-traitant pour le compte du Responsable de traitement, dans le cadre de l'exécution du Service, pour toute la durée du contrat SaaS principal.",
      ],
    },
    {
      title: "2. Nature, finalité et catégories de données",
      list: [
        "Nature : hébergement, stockage, traitement des commandes, gestion du personnel, et, le cas échéant, données liées aux paiements (hors détention des fonds).",
        "Finalité : exécution du Service commandé par le Client.",
        "Personnes concernées : personnel du Client, clientèle du Client (selon fonctionnalités activées).",
        "Données : identification, contact, commande ; données de paiement techniques limitées — le Sous-traitant ne stocke pas les données de carte bancaire, traitées directement par Stripe.",
      ],
    },
    {
      title: "3. Obligations du Sous-traitant",
      paragraphs: ["Conformément à l'article 28.3 du RGPD, le Sous-traitant s'engage à :"],
      list: [
        "traiter les données uniquement sur instruction documentée du Responsable de traitement ;",
        "garantir la confidentialité des personnes autorisées à traiter les données ;",
        "mettre en œuvre les mesures de sécurité prévues à l'article 32 du RGPD ;",
        "ne recourir à un sous-traitant ultérieur qu'avec autorisation préalable, écrite, générale ou spécifique, du Responsable de traitement (liste en Annexe 1) ;",
        "assister le Responsable de traitement dans le respect des droits des personnes concernées ;",
        "l'assister en cas de violation de données, notamment par notification sans délai indu après en avoir pris connaissance ;",
        "supprimer ou restituer, au choix du Responsable de traitement, l'ensemble des données à l'issue du contrat, sauf obligation légale de conservation ;",
        "mettre à disposition toute information nécessaire pour démontrer le respect du présent article et permettre la réalisation d'audits.",
      ],
    },
    {
      title: "4. Transferts hors Union européenne",
      paragraphs: [
        "Aucun transfert hors UE n'est prévu à ce jour. Toute évolution fera l'objet d'une information préalable du Responsable de traitement et, le cas échéant, de garanties appropriées (clauses contractuelles types de la Commission européenne).",
      ],
    },
    {
      title: "5. Responsabilité",
      paragraphs: [
        "Chaque partie répond des manquements qui lui sont propres au titre du RGPD. Le Sous-traitant informe sans délai le Responsable de traitement de toute instruction qu'il estimerait contraire au RGPD.",
      ],
    },
    {
      title: "Annexe 1 — Sous-traitants ultérieurs",
      list: [
        "Hébergement : [hébergeur retenu — région UE à confirmer]",
        "Traitement des paiements : Stripe Payments Europe Limited (ou entité Stripe applicable)",
      ],
    },
  ],
};
