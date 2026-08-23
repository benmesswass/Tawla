"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

type Rect = { top: number; left: number; width: number; height: number };

const MARGE = 12; // écart entre la cible et la bulle, et bord d'écran minimal
const LARGEUR_BULLE = 360;
const HAUTEUR_SUPPOSEE = 200; // sert seulement à choisir dessus/dessous
const SEUIL_FEUILLE = 640; // sous cette largeur, la bulle se pose en bas d'écran

function mouvementReduit(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Suit l'élément portant `data-visite="<cible>"`.
 *
 * La page peut charger ses données après le montage (le tableau de bord
 * n'affiche sa recette du jour qu'une fois l'API répondue) : on réessaie
 * pendant quelques secondes avant d'abandonner. Une cible absente n'est pas
 * une erreur — la bulle se recentre, l'étape reste lisible.
 */
function useRectCible(cible: string | undefined, cle: string): Rect | null {
  const [rect, setRect] = useState<Rect | null>(null);

  useEffect(() => {
    setRect(null);
    if (!cible) return;

    let element: HTMLElement | null = null;

    function mesurer() {
      if (!element) return;
      const r = element.getBoundingClientRect();
      // Un élément masqué (onglet non actif, écran étroit) a un rect nul :
      // mieux vaut la bulle centrée qu'un halo collé dans un coin.
      if (r.width === 0 && r.height === 0) {
        setRect(null);
        return;
      }
      setRect({ top: r.top, left: r.left, width: r.width, height: r.height });
    }

    function chercher(): boolean {
      element = document.querySelector<HTMLElement>(`[data-visite="${cible}"]`);
      if (!element) return false;
      element.scrollIntoView({ block: "center", behavior: mouvementReduit() ? "auto" : "smooth" });
      mesurer();
      return true;
    }

    let attente: ReturnType<typeof setInterval> | undefined;
    if (!chercher()) {
      const debut = Date.now();
      attente = setInterval(() => {
        if (chercher() || Date.now() - debut > 4000) clearInterval(attente);
      }, 150);
    }

    // `true` : le défilement d'un conteneur interne remonte aussi jusqu'ici,
    // sinon le halo se décroche dès que la cible vit dans une zone scrollable.
    window.addEventListener("scroll", mesurer, true);
    window.addEventListener("resize", mesurer);
    return () => {
      if (attente) clearInterval(attente);
      window.removeEventListener("scroll", mesurer, true);
      window.removeEventListener("resize", mesurer);
    };
  }, [cible, cle]);

  return rect;
}

/**
 * Assombrit la page, découpe un trou autour de la cible, et pose la bulle à
 * côté.
 *
 * Le voile ne capte aucun clic (`pointer-events: none`) : pendant une démo, le
 * restaurateur doit pouvoir cliquer le bouton qu'on est en train de lui
 * montrer. La visite éclaire l'écran, elle ne le confisque pas.
 */
export default function Projecteur({
  cible,
  cle,
  children,
}: {
  cible?: string;
  cle: string;
  children: ReactNode;
}) {
  const rect = useRectCible(cible, cle);
  const [fenetre, setFenetre] = useState<{ largeur: number; hauteur: number } | null>(null);
  const bulle = useRef<HTMLDivElement>(null);
  const [hauteur, setHauteur] = useState(HAUTEUR_SUPPOSEE);

  useEffect(() => {
    function mesurer() {
      setFenetre({ largeur: window.innerWidth, hauteur: window.innerHeight });
    }
    mesurer();
    window.addEventListener("resize", mesurer);
    return () => window.removeEventListener("resize", mesurer);
  }, []);

  // La hauteur réelle décide du placement : une bulle de six lignes ne tient
  // pas là où une de deux lignes tient. Mesurée après rendu, donc un passage
  // de plus à chaque étape — mais pas de boucle : la bulle garde la même
  // largeur quel que soit le placement, sa hauteur ne dépend que du texte.
  useEffect(() => {
    const mesuree = bulle.current?.offsetHeight;
    if (mesuree && Math.abs(mesuree - hauteur) > 1) setHauteur(mesuree);
  }, [cle, hauteur]);

  if (!fenetre) return null;

  const voile = "rgba(36, 24, 17, .55)";
  const enFeuille = fenetre.largeur < SEUIL_FEUILLE;

  // Sans cible : voile plein et bulle au centre (introduction, conclusion).
  if (!rect) {
    return (
      <>
        <div aria-hidden className="fixed inset-0 z-[70] pointer-events-none" style={{ background: voile }} />
        <div className="fixed inset-0 z-[71] grid place-items-center p-4 pointer-events-none">
          <div ref={bulle} className="pointer-events-auto w-full" style={{ maxWidth: LARGEUR_BULLE }}>
            {children}
          </div>
        </div>
      </>
    );
  }

  const largeur = Math.min(LARGEUR_BULLE, fenetre.largeur - 2 * MARGE);
  const centre = (min: number, max: number, taille: number, milieu: number) =>
    Math.min(Math.max(milieu - taille / 2, min), Math.max(max - taille, min));
  const gauche = centre(MARGE, fenetre.largeur - MARGE, largeur, rect.left + rect.width / 2);
  const haut = centre(MARGE, fenetre.hauteur - MARGE, hauteur, rect.top + rect.height / 2);

  // Dessous d'abord, puis dessus, puis à côté. Une carte tarif ou une section
  // entière fait souvent plus haut que la place restante en dessous : la poser
  // « juste après » l'enverrait hors écran, et la coller en bas recouvrirait le
  // bas de ce qu'elle décrit. À côté, elle laisse la cible entièrement visible.
  const besoin = hauteur + MARGE;
  const place =
    fenetre.hauteur - (rect.top + rect.height) >= besoin
      ? "bas"
      : rect.top >= besoin
        ? "haut"
        : fenetre.largeur - (rect.left + rect.width) >= largeur + 2 * MARGE
          ? "droite"
          : rect.left >= largeur + 2 * MARGE
            ? "gauche"
            : "ecran";

  const POSITIONS: Record<string, Record<string, number | string | undefined>> = {
    bas: { top: rect.top + rect.height + MARGE, left: gauche, width: largeur },
    haut: { top: rect.top - MARGE, left: gauche, width: largeur, transform: "translateY(-100%)" },
    droite: { top: haut, left: rect.left + rect.width + MARGE, width: largeur },
    gauche: { top: haut, left: rect.left - largeur - MARGE, width: largeur },
    // Cible plus grande que l'écran dans les deux sens : plus rien à préserver,
    // la bulle se pose en bas.
    ecran: { bottom: MARGE, left: gauche, width: largeur },
  };

  const positionBulle = enFeuille ? { left: MARGE, right: MARGE, bottom: MARGE } : POSITIONS[place];

  return (
    <>
      {/* Le voile et le trou sont le même élément : une ombre portée de
          9999px autour du cadre de la cible. Pas de masque SVG, pas de quatre
          rectangles à faire coïncider au pixel près. */}
      <div
        aria-hidden
        className="fixed z-[70] pointer-events-none"
        style={{
          top: rect.top - 6,
          left: rect.left - 6,
          width: rect.width + 12,
          height: rect.height + 12,
          borderRadius: 12,
          border: "2px solid var(--harissa)",
          boxShadow: `0 0 0 9999px ${voile}`,
          transition: mouvementReduit() ? undefined : "top .18s ease, left .18s ease, width .18s ease, height .18s ease",
        }}
      />
      <div
        ref={bulle}
        className="fixed z-[71]"
        style={{ ...positionBulle, maxHeight: `calc(100vh - ${2 * MARGE}px)`, overflowY: "auto" }}
      >
        {children}
      </div>
    </>
  );
}
