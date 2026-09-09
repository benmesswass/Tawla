import type { IconProps } from "./types";

/**
 * L'arc tourne, le cercle de fond reste : sans lui, un arc seul sur un aplat
 * coloré se lit comme un défaut d'affichage plutôt que comme une attente.
 *
 * L'animation est portée par `animate-spin` de Tailwind, neutralisée par la
 * règle `prefers-reduced-motion` de `globals.css` — l'icône reste alors
 * visible et immobile, ce qui dit encore « ça travaille ».
 */
export default function SpinnerIcon({ className = "w-4 h-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={`${className} animate-spin`} fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth={2.5} opacity={0.28} />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        strokeWidth={2.5}
        strokeLinecap="round"
      />
    </svg>
  );
}
