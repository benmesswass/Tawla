import type { IconProps } from "./types";

export default function CakeIcon({ className = "w-4 h-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 21v-6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v6" />
      <path d="M4 21h16" />
      <path d="M4 17c1 1 2 1 3 0s2-1 3 0 2 1 3 0 2-1 3 0 2 1 3 0" />
      <path d="M12 13V8" />
      <path d="M12 8c-1.2 0-1.8-1-1.2-2S12 4 12 3c0 1 .6 2 1.2 3S13.2 8 12 8Z" />
    </svg>
  );
}
