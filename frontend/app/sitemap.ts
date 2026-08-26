/**
 * France, MARCHE_FRANCE.md Phase F4 §5 ("sitemap.xml par marché").
 *
 * Limité aux pages commerciales statiques, communes à tout visiteur — les
 * pages `/menu/<qr_token>` d'un établissement ne sont volontairement PAS
 * listées ici : les lister demanderait d'interroger le backend depuis cette
 * fonction (le sitemap deviendrait dépendant d'un service externe, contraire
 * à l'esprit "léger, jamais indisponible en même temps qu'un backend" déjà
 * posé pour le hub), et la question de savoir si un client cherche
 * réellement un restaurant précis sur Google plutôt que par le QR physique
 * reste un choix produit, pas une évidence technique — à trancher par
 * Wassim si le besoin se présente.
 */
import type { MetadataRoute } from "next";
import { currentMarket } from "@/lib/market";
import { marketBaseUrl } from "@/lib/marketUrls";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = marketBaseUrl(currentMarket.code);
  return [
    { url: `${base}/`, priority: 1 },
    { url: `${base}/signup`, priority: 0.8 },
    { url: `${base}/confidentialite`, priority: 0.2 },
  ];
}
