import type { ComponentType } from "react";
import BowlIcon from "@/components/icons/BowlIcon";
import TrayIcon from "@/components/icons/TrayIcon";
import CakeIcon from "@/components/icons/CakeIcon";
import CoffeeIcon from "@/components/icons/CoffeeIcon";
import MoonIcon from "@/components/icons/MoonIcon";
import LayersIcon from "@/components/icons/LayersIcon";
import WineIcon from "@/components/icons/WineIcon";
import BagIcon from "@/components/icons/BagIcon";
import UtensilsIcon from "@/components/icons/UtensilsIcon";
import type { IconProps } from "@/components/icons/types";

type Teinte = "harissa" | "menthe" | "laiton" | "neutre";

/**
 * Correspondance exacte, même logique que AR_LABELS dans lib/menuCategories —
 * une catégorie hors liste (donnée historique, import CSV, autre marché)
 * retombe sur la tuile neutre plutôt que sur une erreur.
 */
const VISUELS: Record<string, { Icon: ComponentType<IconProps>; tint: Teinte }> = {
  Entrées: { Icon: BowlIcon, tint: "menthe" },
  Plats: { Icon: TrayIcon, tint: "harissa" },
  Desserts: { Icon: CakeIcon, tint: "laiton" },
  Boissons: { Icon: CoffeeIcon, tint: "menthe" },
  Ftour: { Icon: MoonIcon, tint: "laiton" },
  Formules: { Icon: LayersIcon, tint: "harissa" },
  Vins: { Icon: WineIcon, tint: "laiton" },
  "À emporter": { Icon: BagIcon, tint: "menthe" },
};

const FOND: Record<Teinte, string> = {
  harissa: "bg-[var(--tuile-harissa-fond)] border-[var(--tuile-harissa-bord)]",
  menthe: "bg-[var(--tuile-menthe-fond)] border-[var(--tuile-menthe-bord)]",
  laiton: "bg-[var(--tuile-laiton-fond)] border-[var(--tuile-laiton-bord)]",
  neutre: "bg-[var(--creme)] border-[var(--line)]",
};
const TRAIT: Record<Teinte, string> = {
  harissa: "text-[var(--harissa)]",
  menthe: "text-[var(--menthe)]",
  laiton: "text-[var(--laiton)]",
  neutre: "text-[var(--ink-faint)]",
};

/**
 * Vignette d'un plat sans photo : une tuile teintée par catégorie plutôt
 * qu'une case vide, le temps que le patron envoie la vraie (Phase D1,
 * ROADMAP_DESIGN.md). Une icône ne prétend jamais être le plat réel — une
 * fausse photo générique, si.
 */
export default function VignetteCategorie({ category }: { category: string }) {
  const { Icon, tint } = VISUELS[category] ?? { Icon: UtensilsIcon, tint: "neutre" as const };
  return (
    <div className={`w-[72px] h-[72px] rounded-xl border flex items-center justify-center ${FOND[tint]}`}>
      <Icon className={`w-[30px] h-[30px] ${TRAIT[tint]}`} />
    </div>
  );
}
