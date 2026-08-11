import type { IconProps } from "./types";

export default function GiftIcon({ className = "w-4 h-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="8" width="18" height="4" rx="1" />
      <path d="M12 8v13" />
      <path d="M19 12v7a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-7" />
      <circle cx="9" cy="5.5" r="2.5" />
      <circle cx="15" cy="5.5" r="2.5" />
    </svg>
  );
}
