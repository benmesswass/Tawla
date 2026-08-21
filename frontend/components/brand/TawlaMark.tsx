type Variant = "harissa" | "encre" | "aplat" | "reserve" | "reserveSombre" | "mono";

type Props = {
  size?: number;
  variant?: Variant;
  className?: string;
};

// Méandre sur une grille de 13 × 13 modules (1 module = 13 unités du viewBox).
// Trait d'un module, angles vifs, symétrie à 180°.
const TRAITS: [number, number, number, number][] = [
  [130, 0, 39, 13],
  [156, 0, 13, 65],
  [130, 52, 39, 13],
  [130, 52, 13, 91],
  [52, 130, 65, 13],
  [104, 104, 13, 39],
  [0, 104, 39, 13],
  [0, 104, 13, 65],
  [0, 156, 39, 13],
  [78, 26, 13, 117],
  [26, 78, 117, 13],
  [26, 26, 13, 91],
  [52, 26, 65, 13],
  [52, 26, 13, 39],
];

// Carrés d'accent : 1,3 module, centrés sur un module vide.
const ACCENTS: [number, number][] = [
  [128, 24],
  [102, 50],
  [50, 102],
  [24, 128],
];

const VARIANTS: Record<Variant, { trait: string; accent: string; fond?: string }> = {
  // Logo maître : trait encre, carrés harissa. Le rouge reste la couleur d'action.
  encre: { trait: "#2A1B12", accent: "#D6401E" },
  // Traduction du deux-tons d'origine : trait harissa, carrés laiton.
  harissa: { trait: "#D6401E", accent: "#B8862E" },
  // Tuile pleine, motif en réserve : favicon, icône PWA.
  aplat: { trait: "#F6EFDD", accent: "#241811", fond: "#D6401E" },
  // Sur un aplat harissa déjà en place (en-tête client).
  reserve: { trait: "#F6EFDD", accent: "#241811" },
  // Sur fond espresso (écran cuisine) : accent relevé pour rester lisible.
  reserveSombre: { trait: "#F6EFDD", accent: "#E0BE79" },
  // Impression noir sur blanc (chevalets de table, cf. qr_card.py).
  mono: { trait: "#2A1B12", accent: "#2A1B12" },
};

export default function TawlaMark({ size = 40, variant = "encre", className }: Props) {
  const { trait, accent, fond } = VARIANTS[variant];
  // La tuile ajoute 2,5 modules de marge autour du motif.
  const box = fond ? "-32 -32 233 233" : "0 0 169 169";

  return (
    <svg
      viewBox={box}
      width={size}
      height={size}
      className={className}
      role="img"
      aria-label="Tawla"
    >
      {fond && <rect x={-32} y={-32} width={233} height={233} rx={26} fill={fond} />}
      {TRAITS.map(([x, y, w, h]) => (
        <rect key={`t${x}-${y}-${w}`} x={x} y={y} width={w} height={h} fill={trait} />
      ))}
      {ACCENTS.map(([x, y]) => (
        <rect key={`a${x}-${y}`} x={x} y={y} width={17} height={17} fill={accent} />
      ))}
    </svg>
  );
}
