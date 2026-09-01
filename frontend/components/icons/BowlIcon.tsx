import type { IconProps } from "./types";

export default function BowlIcon({ className = "w-4 h-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 11h16" />
      <path d="M4 11a8 5 0 0 0 16 0" />
      <path d="M9 11c0-2 1-3 1-4" />
      <path d="M14 11c0-2-1-3-1-4" />
    </svg>
  );
}
