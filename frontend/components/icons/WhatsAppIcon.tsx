import type { IconProps } from "./types";

export default function WhatsAppIcon({ className = "w-4 h-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3a8 8 0 0 0-7 12l-1 4 4-1a8 8 0 1 0 4-15Z" />
    </svg>
  );
}
