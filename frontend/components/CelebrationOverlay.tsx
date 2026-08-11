import type { CSSProperties } from "react";

const CONFETTI = [
  { tx: "-60px", ty: "-90px", color: "var(--harissa)", delay: "0s" },
  { tx: "60px", ty: "-80px", color: "var(--menthe)", delay: "0.05s" },
  { tx: "-90px", ty: "10px", color: "var(--laiton)", delay: "0.1s" },
  { tx: "90px", ty: "20px", color: "var(--harissa)", delay: "0.05s" },
  { tx: "-30px", ty: "-110px", color: "var(--laiton)", delay: "0.15s" },
  { tx: "30px", ty: "-100px", color: "var(--menthe)", delay: "0.1s" },
];

export default function CelebrationOverlay() {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none animate-celebration-fade">
      <div className="relative">
        {CONFETTI.map((c, i) => (
          <span
            key={i}
            className="absolute top-1/2 left-1/2 w-2.5 h-2.5 rounded-full animate-confetti"
            style={
              {
                backgroundColor: c.color,
                animationDelay: c.delay,
                "--tx": c.tx,
                "--ty": c.ty,
              } as CSSProperties
            }
          />
        ))}
        <div
          className="w-20 h-20 rounded-full flex items-center justify-center animate-celebration-pop"
          style={{ backgroundColor: "var(--menthe)" }}
        >
          <svg
            viewBox="0 0 24 24"
            className="w-10 h-10 text-white"
            fill="none"
            stroke="currentColor"
            strokeWidth={3}
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M4 12l5 5L20 6" />
          </svg>
        </div>
      </div>
    </div>
  );
}
