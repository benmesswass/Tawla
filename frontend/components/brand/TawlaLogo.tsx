import TawlaMark from "./TawlaMark";

type Props = {
  size?: number;
  /** Empilé (motif au-dessus du mot) plutôt qu'en ligne. */
  vertical?: boolean;
  /** Reprend le mot-symbole en réserve claire sur fond harissa ou espresso. */
  inverse?: boolean;
  className?: string;
};

export default function TawlaLogo({ size = 40, vertical = false, inverse = false, className }: Props) {
  const couleur = inverse ? "var(--semoule)" : "var(--encre)";

  return (
    <div
      className={`flex ${vertical ? "flex-col" : "flex-row"} items-center ${
        vertical ? "gap-4" : "gap-2.5"
      } ${className ?? ""}`}
    >
      <TawlaMark size={size} variant={inverse ? "reserve" : "encre"} />
      {/* Capitales interlettrées, comme le logo fourni. Le décalage à gauche
          compense l'espace de fin ajouté par letter-spacing. */}
      <span
        className="font-extrabold uppercase"
        style={{
          color: couleur,
          fontSize: size * 0.46,
          letterSpacing: "0.34em",
          marginLeft: "0.17em",
          lineHeight: 1,
        }}
      >
        Tawla
      </span>
    </div>
  );
}
