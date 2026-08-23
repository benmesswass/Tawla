"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

type Rect = { top: number; left: number; width: number; height: number };

const MARGE = 12; // écart entre la cible et la bulle, et bord d'écran minimal
const LARGEUR_BULLE = 360;
const HAUTEUR_SUPPOSEE = 200; // sert seulement à choisir dessus/dessous
const SEUIL_FEUILLE = 640; // sous cette largeur, la bulle se pose en bas d'écran
const DELAI_RECHERCHE = 4000; // temps laissé à la page pour afficher sa cible

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
      // Un re-rendu peut avoir remplacé le nœud retenu (le tableau de bord se
      // redessine quand l'API répond) : mesurer un nœud détaché donnerait un
      // rectangle nul, donc un halo qui disparaît sans raison.
      if (element && !element.isConnected) element = document.querySelector<HTMLElement>(`[data-visite="${cible}"]`);
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
        if (chercher()) {
          clearInterval(attente);
          return;
        }
        if (Date.now() - debut <= DELAI_RECHERCHE) return;
        clearInterval(attente);
        // En production la bulle se recentre et personne ne voit rien — c'est
        // voulu, mais c'est aussi comme ça qu'une visite pourrit en silence
        // quand une refonte emporte un attribut. En développement, on le dit.
        if (process.env.NODE_ENV !== "production") {
          console.warn(
            `[visite] cible « ${cible} » introuvable après ${DELAI_RECHERCHE / 1000} s. ` +
              `L'attribut data-visite="${cible}" a-t-il été retiré de la page ? La bulle se recentre.`,
          );
        }
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
  const ancree = rect !== null;
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
  // pas là où une de deux lignes tient. Mesurer une fois après rendu ne
  // suffisait pas — la hauteur retenue restait celle de l'étape précédente et
  // la bulle passait sous le bord de l'écran. L'observateur suit la boîte,
  // fonte comprise, et se déclenche dès qu'on l'attache.
  useEffect(() => {
    const element = bulle.current;
    if (!element || typeof ResizeObserver === "undefined") return;
    const observateur = new ResizeObserver(() => {
      const mesuree = element.offsetHeight;
      setHauteur((precedente) => (Math.abs(mesuree - precedente) > 1 ? mesuree : precedente));
    });
    observateur.observe(element);
    return () => observateur.disconnect();
  }, [cle, ancree]);

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

  // Garde-fou : quoi que décide le placement, la bulle reste entièrement à
  // l'écran. Une hauteur mal mesurée doit produire un chevauchement, jamais un
  // bouton « Suivant » sous le bord de la fenêtre.
  const borner = (y: number) => Math.min(Math.max(y, MARGE), Math.max(fenetre.hauteur - hauteur - MARGE, MARGE));

  const POSITIONS: Record<string, Record<string, number | string | undefined>> = {
    bas: { top: borner(rect.top + rect.height + MARGE), left: gauche, width: largeur },
    haut: { top: borner(rect.top - MARGE - hauteur), left: gauche, width: largeur },
    droite: { top: borner(haut), left: rect.left + rect.width + MARGE, width: largeur },
    gauche: { top: borner(haut), left: rect.left - largeur - MARGE, width: largeur },
    // Cible plus grande que l'écran dans les deux sens : plus rien à préserver,
    // la bulle se pose en bas.
    ecran: { bottom: MARGE, left: gauche, width: largeur },
  };

  // Sur téléphone la bulle occupe toute la largeur : reste à choisir le bord.
  // En bas par défaut (le pouce y est), mais en haut dès que la cible occupe
  // la moitié basse — sinon la barre de panier, collée en bas de l'écran,
  // disparaît sous la bulle qui en parle.
  const positionBulle = enFeuille
    ? rect.top + rect.height / 2 > fenetre.hauteur / 2
      ? { left: MARGE, right: MARGE, top: MARGE }
      : { left: MARGE, right: MARGE, bottom: MARGE }
    : POSITIONS[place];

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
