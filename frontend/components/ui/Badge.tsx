import type { HTMLAttributes } from "react";

type Tone = "neutral" | "success" | "warning" | "danger" | "info";

type Props = HTMLAttributes<HTMLSpanElement> & {
  tone?: Tone;
  dark?: boolean;
};

const LIGHT_TONES: Record<Tone, string> = {
  neutral: "bg-neutral-100 text-neutral-600",
  success: "bg-emerald-100 text-emerald-700",
  warning: "bg-amber-100 text-amber-800",
  danger: "bg-red-100 text-red-700",
  info: "bg-indigo-100 text-indigo-700",
};

const DARK_TONES: Record<Tone, string> = {
  neutral: "bg-neutral-800 text-neutral-300",
  success: "bg-emerald-950 text-emerald-300",
  warning: "bg-amber-950 text-amber-300",
  danger: "bg-red-950 text-red-300",
  info: "bg-indigo-950 text-indigo-300",
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
