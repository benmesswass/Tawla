import type { IconProps } from "./types";

export default function FlameIcon({ className = "w-4 h-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3c-3 4-5 7.5-5 10.5a5 5 0 0 0 10 0c0-1.5-.6-2.7-1.3-3.7.1 1.4-.5 2.2-1.2 2.2-1 0-1-1-.7-2.2C14.4 8 13 5.5 12 3Z" />
    </svg>
  );
}
