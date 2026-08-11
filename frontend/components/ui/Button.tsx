import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger" | "success";
type Size = "sm" | "md";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  dark?: boolean;
};

const LIGHT_VARIANTS: Record<Variant, string> = {
  primary: "bg-[var(--harissa)] hover:bg-[var(--harissa-dark)] text-white",
  secondary: "border border-[var(--line)] text-[var(--encre)] bg-white hover:bg-[var(--semoule)]",
  danger: "border border-red-200 text-red-600 hover:bg-red-50",
  success: "bg-[var(--menthe)] hover:bg-emerald-800 text-white",
};

const DARK_VARIANTS: Record<Variant, string> = {
  primary: "bg-[var(--harissa)] hover:bg-[var(--harissa-dark)] text-white",
  secondary: "border border-neutral-700 text-neutral-200 bg-neutral-800 hover:bg-neutral-700",
  danger: "border border-red-800 text-red-300 hover:bg-red-950",
  success: "bg-[var(--menthe)] hover:bg-emerald-800 text-white",
};

const SIZES: Record<Size, string> = {
  sm: "text-xs px-2 py-1",
  md: "text-sm px-3 py-2",
};

export default function Button({ variant = "primary", size = "md", dark = false, className = "", ...rest }: Props) {
  const palette = dark ? DARK_VARIANTS : LIGHT_VARIANTS;
  return (
    <button
      {...rest}
      className={`font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap ${SIZES[size]} ${palette[variant]} ${className}`}
    />
  );
}
