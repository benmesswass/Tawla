import type { HTMLAttributes } from "react";

type Tone = "default" | "info" | "warning" | "success" | "danger" | "urgent";
type Padding = "sm" | "md";

type Props = HTMLAttributes<HTMLDivElement> & {
  tone?: Tone;
  padding?: Padding;
  dark?: boolean;
};

// info et warning partagent le laiton (fidélité, état transitoire) ; danger et
// urgent partagent le harissa (action requise) — le système n'a que trois
// accents, pas un par tonalité.
const LIGHT_TONES: Record<Tone, string> = {
  default: "border border-[var(--line)] bg-[var(--semoule-raised)]",
  info: "border border-[rgba(184,134,46,.5)] bg-[rgba(184,134,46,.12)]",
  warning: "border border-[rgba(184,134,46,.5)] bg-[rgba(184,134,46,.12)]",
  success: "border border-[rgba(31,107,79,.45)] bg-[rgba(31,107,79,.1)]",
  danger: "border border-[rgba(214,64,30,.55)] bg-[rgba(214,64,30,.1)]",
  urgent: "border border-[rgba(214,64,30,.55)] bg-[rgba(214,64,30,.1)]",
};

const DARK_TONES: Record<Tone, string> = {
  default: "border border-[var(--line-on-espresso)] bg-[var(--espresso-card)]",
  info: "border border-[var(--laiton-on-espresso-border)] bg-[var(--laiton-on-espresso-bg)]",
  warning: "border border-[var(--laiton-on-espresso-border)] bg-[var(--laiton-on-espresso-bg)]",
  success: "border border-[var(--menthe-on-espresso-border)] bg-[var(--menthe-on-espresso-bg)]",
  danger: "border border-[var(--harissa-on-espresso-border)] bg-[var(--harissa-on-espresso-bg)]",
  urgent: "border border-[var(--harissa-on-espresso-border)] bg-[var(--harissa-on-espresso-bg)]",
};

const PADDINGS: Record<Padding, string> = { sm: "p-3", md: "p-4" };

export default function Card({ tone = "default", padding = "md", dark = false, className = "", ...rest }: Props) {
  const palette = dark ? DARK_TONES : LIGHT_TONES;
  return <div {...rest} className={`rounded-lg ${PADDINGS[padding]} ${palette[tone]} ${className}`} />;
}
