import TrayIcon from "@/components/icons/TrayIcon";

type Props = {
  message: string;
  dark?: boolean;
  className?: string;
};

export default function EmptyState({ message, dark = false, className = "" }: Props) {
  const tone = dark ? "text-neutral-500" : "text-[var(--ink-soft)]";
  return (
    <div className={`flex flex-col items-center gap-2 text-center py-6 ${tone} ${className}`}>
      <TrayIcon className="w-8 h-8 opacity-60" />
      <p className="text-sm">{message}</p>
    </div>
  );
}
