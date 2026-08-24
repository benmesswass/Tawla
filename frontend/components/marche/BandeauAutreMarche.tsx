"use client";

import { useEffect, useState } from "react";

const DISMISSED_KEY = "tawla:bandeau-autre-marche-ferme";

/**
 * "Vous semblez être ailleurs" (F4, `MARCHE_FRANCE.md` §5) — discret,
 * jamais bloquant, fermé pour toujours dès le premier clic. N'apparaît QUE
 * sur la page d'accueil publique (voir `app/page.tsx`) : jamais sur le
 * parcours client (`/menu/…`), qui ne doit jamais rencontrer le sujet du
 * marché — voir le commentaire en tête de ce fichier-là.
 */
export default function BandeauAutreMarche({
  label,
  href,
}: {
  /** Ex: "Vous semblez être en France — voir Tawla France" */
  label: string;
  href: string;
}) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    try {
      if (window.localStorage.getItem(DISMISSED_KEY) !== "1") setVisible(true);
    } catch {
      setVisible(true);
    }
  }, []);

  if (!visible) return null;

  const fermer = () => {
    setVisible(false);
    try {
      window.localStorage.setItem(DISMISSED_KEY, "1");
    } catch {
      // Stockage indisponible (navigation privée…) — se referme quand même
      // pour cette visite, simplement pas mémorisé pour la suivante.
    }
  };

  return (
    <div
      role="status"
      className="flex items-center justify-between gap-3 bg-[var(--semoule-raised)] border-b border-[var(--line)] px-4 py-2 text-sm text-[var(--ink-soft)]"
    >
      <a href={href} className="underline text-[var(--encre)]">
        {label}
      </a>
      <button
        type="button"
        onClick={fermer}
        aria-label="Fermer"
        className="shrink-0 text-[var(--ink-faint)] px-1"
      >
        ✕
      </button>
    </div>
  );
}
