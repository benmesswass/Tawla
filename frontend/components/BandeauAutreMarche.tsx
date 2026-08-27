"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { currentMarket } from "@/lib/market";
import { selecteurAutorise } from "@/lib/marketBanner";

const CLE_STOCKAGE = "tawla-bandeau-autre-marche-ferme";
const NOMS: Record<string, string> = { tn: "Tunisie", fr: "France" };

/**
 * « Vous semblez être ailleurs » (France, MARCHE_FRANCE.md Phase F4 §5).
 *
 * Détection via `/api/geo` (côté client, après montage) plutôt qu'un
 * `headers()` direct dans ce composant : ce composant est monté depuis le
 * layout racine, donc lu par CHAQUE page — un accès serveur aux en-têtes
 * ici forcerait tout le site à sortir du rendu statique. Isoler la lecture
 * dans une route API dédiée garde `/`, `/confidentialite` etc. statiques.
 *
 * Fermable pour toujours (spec §5) : mémorisé en `localStorage`, jamais un
 * cookie — ce n'est qu'une suggestion, pas un état qui doit traverser les
 * appareils ou survivre à un « effacer les données ». Jamais bloquant : une
 * croix, rien d'autre à faire pour continuer sa visite.
 *
 * Absent du parcours client (`/menu/…`), comme `BandeauDemo` — voir
 * `lib/marketBanner.ts` pour le garde-fou testé.
 */
export default function BandeauAutreMarche() {
  const chemin = usePathname();
  const [autre, setAutre] = useState<{ nom: string; url: string } | null>(null);
  const [ferme, setFerme] = useState(true); // true par défaut : pas de flash avant la lecture du localStorage

  useEffect(() => {
    let annule = false;
    fetch("/api/geo")
      .then((res) => res.json())
      .then((data: { market: string | null; url: string | null }) => {
        if (annule || !data.market || data.market === currentMarket.code || !data.url) return;
        setAutre({ nom: NOMS[data.market] ?? data.market, url: data.url });
      })
      .catch(() => {
        // Détection indisponible (réseau, route absente) : dégradation
        // silencieuse, le bandeau ne s'affiche simplement pas.
      });
    try {
      setFerme(window.localStorage.getItem(CLE_STOCKAGE) === "1");
    } catch {
      setFerme(false);
    }
    return () => {
      annule = true;
    };
  }, []);

  if (!autre || ferme || !selecteurAutorise(chemin)) return null;

  function fermer() {
    setFerme(true);
    try {
      window.localStorage.setItem(CLE_STOCKAGE, "1");
    } catch {
      // Stockage indisponible : le bandeau reviendra au prochain chargement, sans gravité.
    }
  }

  return (
    // Positionnement (fixed/z-index) porté par le conteneur commun dans
    // app/layout.tsx, partagé avec BandeauDemo — pour que les deux s'empilent
    // au lieu de se superposer quand les deux sont visibles.
    <div
      role="status"
      className="pointer-events-auto flex items-center gap-3 rounded-full bg-[var(--espresso)] text-[var(--semoule)] text-xs px-4 py-2 shadow-lg"
    >
      <span>
        Vous semblez être en {autre.nom} —{" "}
        <a href={autre.url} className="underline font-medium">
          voir Tawla {autre.nom}
        </a>
      </span>
      <button onClick={fermer} aria-label="Fermer" className="shrink-0 opacity-70 hover:opacity-100">
        ✕
      </button>
    </div>
  );
}
