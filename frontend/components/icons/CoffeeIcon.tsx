import type { IconProps } from "./types";

export default function CoffeeIcon({ className = "w-4 h-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 9h13v6a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4V9Z" />
      <path d="M17 10h1.5a2.5 2.5 0 0 1 0 5H17" />
      <path d="M8 2c0 1-1 1-1 2s1 1 1 2" />
      <path d="M12 2c0 1-1 1-1 2s1 1 1 2" />
    </svg>
  );
}
