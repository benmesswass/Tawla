type Props = {
  message: string;
  dark?: boolean;
  className?: string;
};

export default function EmptyState({ message, dark = false, className = "" }: Props) {
  return (
    <p className={`text-sm text-center py-6 ${dark ? "text-neutral-500" : "text-[var(--ink-soft)]"} ${className}`}>
      {message}
    </p>
  );
}
