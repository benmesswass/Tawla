import { Lalezar, Hanken_Grotesk } from "next/font/google";

// Police d'affichage (titres, logo) — un seul poids, disponible.
export const lalezar = Lalezar({ subsets: ["latin"], weight: "400" });

// Police texte (UI, formulaires) — poids variable.
export const hankenGrotesk = Hanken_Grotesk({ subsets: ["latin"], weight: ["400", "500", "600", "700"] });
