/**
 * Mentions légales (marché France).
 *
 * BROUILLON — texte fourni par Wassim en attente de validation par un
 * professionnel (avocat / expert-comptable) avant mise en ligne définitive.
 * Les placeholders entre crochets (ex. `[SIRET à compléter]`) sont
 * intentionnels : ne pas inventer de valeur, ne pas les retirer.
 *
 * Séparé de `privacy.ts` (Tunisie) : ce texte est spécifique au marché
 * France (LCEN, droit français) et ne doit pas remplacer la politique de
 * confidentialité Tunisie existante sur `/confidentialite`.
 */

type Section = { title: string; paragraphs?: string[]; list?: string[] };
type MentionsLegalesPage = { title: string; intro: string; sections: Section[] };

export const MENTIONS_LEGALES: MentionsLegalesPage = {
  title: "Mentions légales",
  intro:
    "Base légale : article 1-1 de la loi n° 2004-575 pour la confiance dans l'économie numérique (LCEN), tel que modifié par la loi n° 2024-449 du 21 mai 2024 (loi SREN).",
  sections: [
    {
      title: "1. Éditeur du site",
      paragraphs: [
        "Le site tawla.com (« le Site ») est édité par :",
        "[Nom et prénom] — Wassim Ben Messaoud",
        "Entreprise individuelle (micro-entrepreneur), immatriculée sous le numéro SIRET [à compléter après immatriculation]",
        "Siège social : [adresse à compléter]",
        "Adresse e-mail : [contact@tawla.com]",
        "TVA intracommunautaire : non applicable — franchise en base de TVA (art. 293 B du Code général des impôts), sous réserve de dépassement du seuil en vigueur.",
      ],
    },
    {
      title: "2. Directeur de la publication",
      paragraphs: ["[Wassim Ben Messaoud], en qualité d'exploitant individuel."],
    },
    {
      title: "3. Hébergement",
      paragraphs: [
        "Le Site est hébergé par : [raison sociale et adresse exactes de l'hébergeur — à vérifier directement sur sa page légale avant publication, non reconstituées ici]. Base de données hébergée dans l'Union européenne (région à confirmer).",
      ],
    },
    {
      title: "4. Propriété intellectuelle",
      paragraphs: [
        "L'ensemble des éléments du Site (structure, textes, logiciels, bases de données, éléments graphiques, marques, logos) est protégé par le droit de la propriété intellectuelle et demeure la propriété exclusive de l'éditeur, sauf mention contraire. Toute reproduction, représentation ou exploitation, totale ou partielle, sans autorisation préalable écrite, est interdite.",
      ],
    },
    {
      title: "5. Données personnelles",
      paragraphs: [
        "Le traitement des données à caractère personnel collectées via le Site est décrit dans la Politique de confidentialité, accessible à [lien]. Pour toute question relative à vos données : [adresse e-mail dédiée].",
      ],
    },
    {
      title: "6. Droit applicable",
      paragraphs: [
        "Les présentes mentions légales sont soumises au droit français. À défaut de résolution amiable, tout litige relève de la compétence des tribunaux français compétents.",
      ],
    },
  ],
};
