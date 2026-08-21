import type { HTMLAttributes } from "react";

type Tone = "neutral" | "success" | "warning" | "danger" | "info";

type Props = HTMLAttributes<HTMLSpanElement> & {
  tone?: Tone;
  dark?: boolean;
};

// success/warning/danger/info alignés sur le tableau des badges de connexion
// (connecté / connexion.../déconnecté / session expirée) — voir ConnectionBadge.
const LIGHT_TONES: Record<Tone, string> = {
  neutral: "bg-[var(--creme)] text-[var(--ink-soft)]",
  success: "bg-[rgba(31,107,79,.12)] text-[#1f6b4f]",
  warning: "bg-[rgba(184,134,46,.12)] text-[#8a6420]",
  danger: "bg-[rgba(214,64,30,.1)] text-[var(--harissa)]",
  info: "bg-[var(--espresso)] text-[var(--semoule)]",
};

const DARK_TONES: Record<Tone, string> = {
  neutral: "bg-[var(--line-on-espresso)] text-[var(--ink-on-espresso-strong)]",
  success: "bg-[var(--menthe-on-espresso-bg)] text-[var(--menthe-on-espresso-text)]",
  warning: "bg-[var(--laiton-on-espresso-bg)] text-[var(--laiton-on-espresso-text)]",
  danger: "bg-[var(--harissa-on-espresso-bg)] text-[var(--harissa-on-espresso-text)]",
  info: "bg-[var(--semoule)] text-[var(--espresso)]",
};

export default function Badge({ tone = "neutral", dark = false, className = "", ...rest }: Props) {
  const palette = dark ? DARK_TONES : LIGHT_TONES;
  return (
    <span
      {...rest}
      className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full font-medium whitespace-nowrap ${palette[tone]} ${className}`}
    />
  );
}
