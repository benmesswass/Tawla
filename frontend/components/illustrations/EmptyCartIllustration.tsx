type Props = {
  className?: string;
};

export default function EmptyCartIllustration({ className = "w-10 h-10" }: Props) {
  return (
    <svg
      viewBox="0 0 48 48"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M8 14h4l3 20a3 3 0 0 0 3 2.5h14a3 3 0 0 0 3-2.5l2.5-14H15" />
      <circle cx="19" cy="41" r="1.6" fill="currentColor" stroke="none" />
      <circle cx="31" cy="41" r="1.6" fill="currentColor" stroke="none" />
      <path d="M20 24l4 4m0-4l-4 4" opacity="0.5" />
    </svg>
  );
}
