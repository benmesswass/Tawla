type Props = {
  filled: number;
  total?: number;
  rewardAvailable?: boolean;
};

// Carte à tamponner visuelle — remplace le texte brut "3 commandes, encore
// 7" par une rangée de jetons qui se remplissent, façon carte de fidélité
// papier qu'un serveur tamponnerait à chaque passage.
export default function LoyaltyStampCard({ filled, total = 10, rewardAvailable = false }: Props) {
  return (
    <div
      className="flex flex-wrap justify-center gap-1.5"
      role="img"
      aria-label={`${filled} sur ${total} tampons de fidélité`}
    >
      {Array.from({ length: total }).map((_, i) => {
        const isFilled = i < filled;
        return (
          <span
            key={i}
            className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-semibold shrink-0 ${
              isFilled ? "" : "border-2 border-dashed"
            }`}
            style={{
              backgroundColor: isFilled ? (rewardAvailable ? "var(--laiton)" : "var(--harissa)") : "transparent",
              borderColor: isFilled ? undefined : "var(--line)",
              color: isFilled ? "white" : "var(--ink-soft)",
            }}
          >
            {isFilled ? "✓" : ""}
          </span>
        );
      })}
    </div>
  );
}
