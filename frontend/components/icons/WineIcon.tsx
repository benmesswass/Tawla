import type { IconProps } from "./types";

export default function WineIcon({ className = "w-4 h-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M7 3h10" />
      <path d="M7 3c0 4.5 1.8 7.5 5 7.5S17 7.5 17 3" />
      <path d="M12 10.5V18" />
      <path d="M8 21h8" />
    </svg>
  );
}
