import type { SocketStatus } from "@/lib/useReconnectingSocket";

const LABELS: Record<SocketStatus, string> = {
  connected: "Connecté",
  connecting: "Connexion...",
  disconnected: "Déconnecté — reconnexion...",
  unauthorized: "Session expirée — reconnectez-vous",
};

type Palette = { bg: string; border: string; text: string; dot: string };

// Menthe = connecté, laiton = connexion en cours (état transitoire), harissa =
// déconnecté (action requise : ça va se reconnecter tout seul, mais ça mérite
// l'œil). Session expirée est le seul aplat plein de l'écran — volontairement,
// c'est le seul badge qui demande une vraie action du serveur.
const LIGHT_STYLES: Record<SocketStatus, Palette> = {
  connected: { bg: "rgba(31,107,79,.12)", border: "rgba(31,107,79,.5)", text: "#1f6b4f", dot: "#1f6b4f" },
  connecting: { bg: "rgba(184,134,46,.12)", border: "rgba(184,134,46,.55)", text: "#8a6420", dot: "#b8862e" },
  disconnected: { bg: "rgba(214,64,30,.1)", border: "rgba(214,64,30,.55)", text: "#d6401e", dot: "#d6401e" },
  unauthorized: { bg: "#241811", border: "#241811", text: "#f6efdd", dot: "#f6efdd" },
};

// Sur fond espresso (cuisine) : mêmes rôles, contraste relevé. La session
// expirée passe en crème pleine — le seul aplat clair de l'écran cuisine, pour
// être vu depuis le passe.
const DARK_STYLES: Record<SocketStatus, Palette> = {
  connected: { bg: "rgba(31,107,79,.22)", border: "rgba(31,107,79,.7)", text: "#7fc5a6", dot: "#7fc5a6" },
  connecting: { bg: "rgba(184,134,46,.2)", border: "rgba(184,134,46,.75)", text: "#e0be79", dot: "#e0be79" },
  disconnected: { bg: "rgba(214,64,30,.24)", border: "#d6401e", text: "#f0a48c", dot: "#f0a48c" },
  unauthorized: { bg: "#f6efdd", border: "#f6efdd", text: "#241811", dot: "#241811" },
};

const PULSE_CLASS: Partial<Record<SocketStatus, string>> = {
  connected: "animate-tw-pulse-v",
  disconnected: "animate-tw-pulse",
};

export default function ConnectionBadge({ status, dark = false }: { status: SocketStatus; dark?: boolean }) {
  const s = (dark ? DARK_STYLES : LIGHT_STYLES)[status];
  return (
    <span
      className="inline-flex items-center gap-2 text-[13px] font-semibold px-3 py-[6px] rounded-full border whitespace-nowrap"
      style={{ backgroundColor: s.bg, borderColor: s.border, color: s.text }}
      role="status"
    >
      <span
        className={`w-2 h-2 rounded-full shrink-0 ${PULSE_CLASS[status] ?? ""}`}
        style={{ backgroundColor: s.dot }}
        aria-hidden="true"
      />
      {LABELS[status]}
    </span>
  );
}
