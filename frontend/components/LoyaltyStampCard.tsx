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
      className="flex flex-wrap justify-center gap-[5px]"
      role="img"
      aria-label={`${filled} sur ${total} tampons de fidélité`}
    >
      {Array.from({ length: total }).map((_, i) => {
        const isFilled = i < filled;
        return (
          <span
            key={i}
            className="w-[23px] h-[23px] rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 border"
            style={{
              backgroundColor: isFilled ? "var(--laiton)" : "var(--semoule-raised)",
              borderColor: isFilled ? "var(--laiton)" : "var(--line-strong)",
              color: isFilled ? (rewardAvailable ? "var(--espresso)" : "var(--semoule)") : "transparent",
            }}
          >
            {isFilled ? "✓" : ""}
          </span>
        );
      })}
    </div>
  );
}
