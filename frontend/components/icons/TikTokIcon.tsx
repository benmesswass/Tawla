import type { IconProps } from "./types";

export default function TikTokIcon({ className = "w-4 h-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M15 4c.6 2 2 3.4 4 3.8V11c-1.5 0-2.9-.4-4-1.2V15a5 5 0 1 1-5-5c.3 0 .7 0 1 .1V13a2 2 0 1 0 1.4 1.9V4Z" />
    </svg>
  );
}
