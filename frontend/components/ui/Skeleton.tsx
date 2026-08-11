type Props = {
  className?: string;
  dark?: boolean;
};

export default function Skeleton({ className = "", dark = false }: Props) {
  return <div className={`animate-pulse rounded ${dark ? "bg-neutral-800" : "bg-neutral-200"} ${className}`} />;
}
