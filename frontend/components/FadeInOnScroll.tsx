"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Fondu + léger glissement vers le haut à l'entrée dans le viewport (Phase D2
 * point 2 de ROADMAP_DESIGN.md). Un seul déclenchement, jamais un va-et-vient
 * si l'utilisateur remonte puis redescend — voir .fondu-scroll dans
 * globals.css, qui gère aussi `prefers-reduced-motion`.
 */
export default function FadeInOnScroll({
  children,
  delayMs = 0,
}: {
  children: React.ReactNode;
  delayMs?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        timer = setTimeout(() => setVisible(true), delayMs);
        observer.disconnect();
      },
      { threshold: 0.2 }
    );
    observer.observe(node);
    return () => {
      observer.disconnect();
      clearTimeout(timer);
    };
  }, [delayMs]);

  return (
    <div ref={ref} className={`fondu-scroll ${visible ? "visible" : ""}`}>
      {children}
    </div>
  );
}
