import type { ButtonHTMLAttributes, ReactNode } from "react";
import CheckIcon from "@/components/icons/CheckIcon";
import SpinnerIcon from "@/components/icons/SpinnerIcon";

type Variant = "primary" | "secondary" | "danger" | "success" | "laiton";
type Size = "sm" | "md" | "lg";

type Props = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> & {
  variant?: Variant;
  size?: Size;
  dark?: boolean;
  children?: ReactNode;
  /**
   * L'action est partie et on attend la réponse. Le bouton se verrouille de
   * lui-même — sans ça, le double clic sur « Envoyer la commande » envoie deux
   * commandes, et c'est un vrai incident en salle, pas un défaut cosmétique.
   */
  loading?: boolean;
  /**
   * L'action a réussi. État transitoire, piloté par l'appelant (lui seul sait
   * combien de temps la confirmation doit rester, et quand la vue change) —
   * le bouton ne porte aucune minuterie.
   */
  success?: boolean;
};

// primary = harissa, seule couleur d'action cliquable par défaut ; success est
// réservé aux validations terminales cuisine (Marquer prête) ; laiton sert aux
// actions d'encaissement en salle. Règle : un seul harissa cliquable par zone
// de décision, jamais un simple hover de teinte.
//
// Le libellé du primaire est en --on-harissa (blanc) et non --semoule : sur
// l'aplat harissa, semoule donnait 3,97:1, sous le seuil AA de 4,5:1.
const LIGHT_VARIANTS: Record<Variant, string> = {
  primary:
    "bg-[var(--harissa)] text-[var(--on-harissa)] shadow-[0_2px_0_var(--harissa-pressed)] hover:brightness-95 active:shadow-none active:translate-y-[2px]",
  secondary:
    "border border-[var(--line)] text-[var(--encre)] bg-white hover:bg-[var(--semoule)] active:bg-[var(--creme)] active:translate-y-[1px]",
  danger:
    "border border-[var(--harissa)] text-[var(--harissa)] bg-transparent hover:bg-[rgba(214,64,30,.08)] active:bg-[rgba(214,64,30,.16)] active:translate-y-[1px]",
  success:
    "bg-[var(--menthe)] text-[var(--semoule)] shadow-[0_2px_0_#143f2f] hover:brightness-95 active:shadow-none active:translate-y-[2px]",
  laiton:
    "bg-[var(--laiton)] text-[var(--espresso)] shadow-[0_2px_0_#8a6420] hover:brightness-95 active:shadow-none active:translate-y-[2px]",
};

const DARK_VARIANTS: Record<Variant, string> = {
  primary:
    "bg-[var(--harissa)] text-[var(--on-harissa)] shadow-[0_2px_0_var(--harissa-pressed)] hover:brightness-95 active:shadow-none active:translate-y-[2px]",
  secondary:
    "border border-[var(--line-on-espresso-strong)] text-[var(--ink-on-espresso-strong)] bg-[var(--line-on-espresso)] hover:bg-[var(--line-on-espresso-strong)] active:translate-y-[1px]",
  danger:
    "border border-[var(--harissa-on-espresso-border)] text-[var(--harissa-on-espresso-text)] bg-[var(--harissa-on-espresso-bg)] active:translate-y-[1px]",
  success:
    "bg-[var(--menthe)] text-[var(--semoule)] shadow-[0_2px_0_#143f2f] hover:brightness-95 active:shadow-none active:translate-y-[2px]",
  laiton:
    "bg-[var(--laiton)] text-[var(--espresso)] shadow-[0_2px_0_#8a6420] hover:brightness-95 active:shadow-none active:translate-y-[2px]",
};

// sm et md sont inchangés : les redimensionner ici retoucherait d'un coup les
// boutons de seize fichiers. lg est le nouveau format des actions principales
// sur téléphone — 44 px de haut, la cible qu'un pouce atteint sans viser.
const SIZES: Record<Size, string> = {
  sm: "text-xs px-2 py-1 gap-1",
  md: "text-sm px-3 py-2 gap-1.5",
  lg: "text-etiquette px-4 py-2.5 min-h-11 gap-2",
};

export default function Button({
  variant = "primary",
  size = "md",
  dark = false,
  loading = false,
  success = false,
  disabled = false,
  className = "",
  children,
  ...rest
}: Props) {
  const palette = dark ? DARK_VARIANTS : LIGHT_VARIANTS;
  const offset = dark ? "focus-visible:ring-offset-[var(--espresso)]" : "focus-visible:ring-offset-[var(--semoule)]";

  // Un bouton en attente n'est pas « désactivé » au sens de l'utilisateur : il
  // travaille. On le rend inopérant, mais aria-busy dit lequel des deux c'est.
  const inerte = disabled || loading;

  return (
    <button
      {...rest}
      disabled={inerte}
      aria-busy={loading || undefined}
      className={`inline-flex items-center justify-center font-medium rounded-controle whitespace-nowrap
        transition-[background-color,border-color,color,box-shadow,transform,filter]
        duration-micro ease-deplacement
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--harissa)] focus-visible:ring-offset-2 ${offset}
        disabled:cursor-not-allowed ${loading ? "cursor-progress" : "disabled:opacity-50"}
        ${SIZES[size]} ${palette[variant]} ${className}`}
    >
      {/* L'icône s'ajoute devant le libellé au lieu de le remplacer : un
          libellé qui disparaît fait rétrécir le bouton au moment précis où
          l'utilisateur regarde s'il a bien cliqué. */}
      {loading && <SpinnerIcon className="w-4 h-4 shrink-0" />}
      {!loading && success && <CheckIcon className="w-4 h-4 shrink-0" />}
      {children}
    </button>
  );
}
