import { Lalezar, Hanken_Grotesk, Cairo } from "next/font/google";

// Police d'affichage (titres, logo) — un seul poids, disponible.
export const lalezar = Lalezar({ subsets: ["latin"], weight: "400" });

// Police texte (UI, formulaires) — poids variable.
export const hankenGrotesk = Hanken_Grotesk({ subsets: ["latin"], weight: ["400", "500", "600", "700"] });

// Police texte en arabe (écran client RTL). Lalezar reste la police d'affichage
// (nom du restaurant, total) même en arabe — Cairo ne couvre que le texte courant.
export const cairo = Cairo({ subsets: ["arabic", "latin"], weight: ["400", "600", "700"] });
