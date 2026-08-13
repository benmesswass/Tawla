import type { SocketStatus } from "@/lib/useReconnectingSocket";

const LABELS: Record<SocketStatus, string> = {
  connected: "Connecté",
  connecting: "Connexion...",
  disconnected: "Déconnecté — reconnexion...",
  unauthorized: "Session expirée — reconnectez-vous",
};

const DOT_CLASS: Record<SocketStatus, string> = {
  connected: "bg-emerald-500",
  connecting: "bg-amber-500",
  disconnected: "bg-red-500",
  unauthorized: "bg-red-500",
};

export default function ConnectionBadge({ status, dark = false }: { status: SocketStatus; dark?: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 text-xs px-2 py-1 rounded-full ${
        dark ? "bg-neutral-800 text-neutral-300" : "bg-neutral-100 text-neutral-600"
      }`}
      role="status"
    >
      <span className={`w-2 h-2 rounded-full ${DOT_CLASS[status]}`} aria-hidden="true" />
      {LABELS[status]}
    </span>
  );
}
