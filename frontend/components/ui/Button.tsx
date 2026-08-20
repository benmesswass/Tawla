import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger" | "success" | "laiton";
type Size = "sm" | "md";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  dark?: boolean;
};

// primary = harissa, seule couleur d'action cliquable par défaut ; success est
// réservé aux validations terminales cuisine (Marquer prête) ; laiton sert aux
// actions d'encaissement en salle. Le bouton primaire porte l'ombre basse
// harissa-pressed et s'enfonce visuellement au clic (règle : un seul harissa
// cliquable par zone de décision, jamais un simple hover de teinte).
const LIGHT_VARIANTS: Record<Variant, string> = {
  primary:
    "bg-[var(--harissa)] text-[var(--semoule)] shadow-[0_2px_0_var(--harissa-pressed)] hover:brightness-95 active:shadow-none active:translate-y-[2px]",
  secondary: "border border-[var(--line)] text-[var(--encre)] bg-white hover:bg-[var(--semoule)]",
  danger: "border border-[var(--harissa)] text-[var(--harissa)] bg-transparent hover:bg-[rgba(214,64,30,.08)]",
  success: "bg-[var(--menthe)] text-[var(--semoule)] hover:brightness-95",
  laiton: "bg-[var(--laiton)] text-[var(--espresso)] hover:brightness-95",
};

const DARK_VARIANTS: Record<Variant, string> = {
  primary:
    "bg-[var(--harissa)] text-[var(--semoule)] shadow-[0_2px_0_var(--harissa-pressed)] hover:brightness-95 active:shadow-none active:translate-y-[2px]",
  secondary:
    "border border-[var(--line-on-espresso-strong)] text-[var(--ink-on-espresso-strong)] bg-[var(--line-on-espresso)] hover:bg-[var(--line-on-espresso-strong)]",
  danger:
    "border border-[var(--harissa-on-espresso-border)] text-[var(--harissa-on-espresso-text)] bg-[var(--harissa-on-espresso-bg)]",
  success: "bg-[var(--menthe)] text-[var(--semoule)] hover:brightness-95",
  laiton: "bg-[var(--laiton)] text-[var(--espresso)] hover:brightness-95",
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
