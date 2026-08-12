import type { IconProps } from "./types";

export default function TrayIcon({ className = "w-4 h-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 13h4l2 3h6l2-3h4" />
      <path d="M5 13 6.5 5.5A2 2 0 0 1 8.46 4h7.08a2 2 0 0 1 1.96 1.5L19 13" />
      <path d="M4 13v5a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5" />
    </svg>
  );
}
