import type { HTMLAttributes } from "react";

type Tone = "default" | "info" | "warning" | "success" | "danger" | "urgent";
type Padding = "sm" | "md";

type Props = HTMLAttributes<HTMLDivElement> & {
  tone?: Tone;
  padding?: Padding;
  dark?: boolean;
};

const LIGHT_TONES: Record<Tone, string> = {
  default: "border border-[var(--line)] bg-white",
  info: "border border-sky-200 bg-sky-50",
  warning: "border border-amber-200 bg-amber-50",
  success: "border border-emerald-200 bg-emerald-50",
  danger: "border border-red-200 bg-red-50",
  urgent: "border border-rose-200 bg-rose-50",
};

const DARK_TONES: Record<Tone, string> = {
  default: "border border-neutral-800 bg-neutral-900",
  info: "border border-indigo-800 bg-indigo-950",
  warning: "border border-amber-800 bg-amber-950",
  success: "border border-emerald-800 bg-emerald-950",
  danger: "border border-red-800 bg-red-950",
  urgent: "border border-rose-800 bg-rose-950",
};

const PADDINGS: Record<Padding, string> = { sm: "p-3", md: "p-4" };

export default function Card({ tone = "default", padding = "md", dark = false, className = "", ...rest }: Props) {
  const palette = dark ? DARK_TONES : LIGHT_TONES;
  return <div {...rest} className={`rounded-lg ${PADDINGS[padding]} ${palette[tone]} ${className}`} />;
}
