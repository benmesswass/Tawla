type Props = {
  size?: number;
  className?: string;
};

// Marque "Le Duo Encadré" — un seul cadre partagé en deux zones (lignes de
// commande + coche de validation) plutôt que deux formes qui se chevauchent.
export default function TawlaMark({ size = 40, className }: Props) {
  return (
    <svg
      viewBox="0 0 100 100"
      width={size}
      height={size}
      className={className}
      role="img"
      aria-label="Tawla"
    >
      <rect x="10" y="28" width="80" height="44" rx="8" fill="#D6401E" />
      <line x1="62" y1="28" x2="62" y2="72" stroke="#F6EFDD" strokeWidth={4} />
      <path
        d="M68,50 L74,56 L86,40"
        fill="none"
        stroke="#F6EFDD"
        strokeWidth={7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
