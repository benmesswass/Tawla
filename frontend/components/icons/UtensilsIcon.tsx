import type { IconProps } from "./types";

export default function UtensilsIcon({ className = "w-4 h-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M6 3v7a2 2 0 0 0 2 2h0a2 2 0 0 0 2-2V3" />
      <path d="M8 12v9" />
      <path d="M17 3c-1.5 0-2.5 1.8-2.5 4.5S15.5 12 17 12s2.5-1.8 2.5-4.5S18.5 3 17 3Z" />
      <path d="M17 12v9" />
    </svg>
  );
}
