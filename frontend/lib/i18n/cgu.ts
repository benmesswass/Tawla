/**
 * Conditions générales d'utilisation — CGU (marché France).
 *
 * BROUILLON — texte fourni par Wassim en attente de validation par un
 * professionnel avant mise en ligne définitive. Les placeholders entre
 * crochets sont intentionnels : ne pas inventer de valeur.
 *
 * Distinct des CGV (`cgv.ts`) : les CGU régissent l'usage de la plateforme
 * par tout utilisateur (personnel du restaurant client, ou public consultant
 * une carte en ligne) ; les CGV régissent l'abonnement du Client
 * professionnel.
 */

type Section = { title: string; paragraphs?: string[]; list?: string[] };
type CguPage = { title: string; intro: string; sections: Section[] };

export const CGU: CguPage = {
  title: "Conditions générales d'utilisation (CGU)",
  intro:
    "Préambule : Régissent l'accès et l'utilisation de la plateforme Tawla par tout utilisateur — personnel d'un restaurant client, ou toute personne accédant à une interface publique du Service (ex. consultation d'une carte en ligne). Complètent les Conditions Générales de Vente applicables au Client professionnel abonné.",
  sections: [
    {
      title: "1. Objet",
      paragraphs: [
        "Le Service permet aux restaurants de gérer leurs commandes, leur carte, leur personnel et, le cas échéant, l'encaissement des paiements de leur clientèle via un prestataire de paiement tiers (Stripe).",
      ],
    },
    {
      title: "2. Accès au Service",
      paragraphs: [
        "L'accès à certaines fonctionnalités nécessite la création d'un compte. L'Utilisateur s'engage à fournir des informations exactes et à préserver la confidentialité de ses identifiants.",
      ],
    },
    {
      title: "3. Utilisation conforme",
      paragraphs: [
        "L'Utilisateur s'engage à utiliser le Service conformément à sa destination et à la réglementation applicable, notamment en matière de protection des données personnelles et, lorsqu'il s'adresse à des consommateurs finaux, de droit de la consommation.",
      ],
    },
    {
      title: "4. Disponibilité du Service",
      paragraphs: [
        "L'éditeur met en œuvre les moyens raisonnables pour assurer la disponibilité du Service, sans garantie de continuité absolue. Des interruptions pour maintenance peuvent survenir, avec information préalable dans la mesure du possible.",
      ],
    },
    {
      title: "5. Propriété intellectuelle",
      paragraphs: [
        "Le Service, son code source, ses interfaces et sa documentation demeurent la propriété exclusive de l'éditeur. Aucune licence autre que le droit d'usage prévu au contrat n'est concédée à l'Utilisateur.",
      ],
    },
    {
      title: "6. Responsabilité",
      paragraphs: [
        "L'éditeur ne saurait être tenu responsable des dommages indirects résultant de l'utilisation du Service. La responsabilité du prestataire de paiement (Stripe) pour l'exécution des transactions relève exclusivement de ses propres conditions contractuelles.",
      ],
    },
    {
      title: "7. Données personnelles",
      paragraphs: [
        "Voir la Politique de confidentialité et, pour les Clients professionnels, le Contrat de sous-traitance RGPD annexé aux CGV.",
      ],
    },
    {
      title: "8. Modification des CGU",
      paragraphs: [
        "L'éditeur peut modifier les présentes CGU à tout moment ; les Utilisateurs sont informés de toute modification substantielle.",
      ],
    },
    {
      title: "9. Droit applicable et juridiction",
      paragraphs: [
        "Droit français. Tribunaux français compétents, sous réserve des règles impératives applicables aux consommateurs le cas échéant.",
      ],
    },
  ],
};
