import type { IconProps } from "./types";

export default function StampIcon({ className = "w-4 h-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M8 14v-2a4 4 0 1 1 8 0v2" />
      <path d="M5 14h14l1.2 5.2a1 1 0 0 1-1 1.8H4.8a1 1 0 0 1-1-1.8L5 14Z" />
      <path d="M9 18h6" />
    </svg>
  );
}
