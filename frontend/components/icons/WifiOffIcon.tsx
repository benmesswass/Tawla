import type { IconProps } from "./types";

export default function WifiOffIcon({ className = "w-4 h-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 8a13 13 0 0 1 16 0" />
      <path d="M7 11.5a8 8 0 0 1 10 0" />
      <path d="M10 15a3.5 3.5 0 0 1 4 0" />
      <circle cx="12" cy="19" r="1" fill="currentColor" stroke="none" />
      <path d="M3 3l18 18" />
    </svg>
  );
}
