"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ChevronLeftIcon from "@/components/icons/ChevronLeftIcon";

/**
 * Mécanique de carrousel partagée par les vitrines Client/Manager/Serveur de
 * ApercuProduit.tsx (Phase D2bis de ROADMAP_DESIGN.md, exploration validée
 * par Wassim le 2026-09-04 : « je veux 3 iPhones distincts côte à côte »,
 * mockup dans l'artifact « Home version problème »). La Cuisine n'en fait pas
 * partie : poste fixe unique, un seul écran à onglets (voir EcranCuisine).
 *
 * Toujours EXACTEMENT un écran net et centré + une moitié de chaque voisin
 * (retour de Wassim, 2026-09-04, sur une première version en pixels fixes qui
 * laissait 3-4 écrans visibles sur un grand moniteur) : la largeur de chaque
 * écran et le remplissage de la piste sont en `vw`, pas en pixels — au
 * chargement, viewport (100vw) = remplissage gauche (25vw, où se glisse la
 * moitié droite du voisin précédent) + écran actif centré (50vw) +
 * remplissage droit (25vw, moitié gauche du voisin suivant), sans place pour
 * un quatrième fragment. Un dimensionnement en pixels fixes ne peut pas
 * donner ce résultat sur toutes les tailles d'écran à la fois (voir
 * ROADMAP_DESIGN.md pour le détail de cette contrainte).
 *
 * Débordement volontaire hors de son conteneur (max-w-4xl sur la home) vers
 * la pleine largeur de la fenêtre : sans lui, l'écran voisin ne serait pas
 * visible à moitié sur les côtés.
 *
 * Navigation par trois voies équivalentes : glisser (tactile natif, souris
 * via pointer events), flèches ‹ › cliquables (indispensable sur PC, où
 * glisser à la souris n'est pas un geste évident), et flèches du clavier
 * une fois le carrousel focus (accessibilité).
 */

export type EtapeCarrousel = {
  id: string;
  label: string;
  // Fonction plutôt que noeud statique : chaque écran affiche en haut un
  // onglet Menu/Panier/Suivi/Paiement (retour de Wassim, 2026-09-04) qui doit
  // pouvoir faire naviguer le carrousel jusqu'à un AUTRE écran — `irA` est
  // donc injecté par EcranCarrousel plutôt que remonté par un état local.
  contenu: (irA: (id: string) => void) => React.ReactNode;
};

export default function EcranCarrousel({
  etapes,
  device,
}: {
  etapes: EtapeCarrousel[];
  device: "phone" | "tablet";
}) {
  const piste = useRef<HTMLDivElement>(null);
  const [actif, setActif] = useState(0);

  const etapeLaPlusProche = useCallback(() => {
    const el = piste.current;
    if (!el) return 0;
    const centreCible = el.scrollLeft + el.clientWidth / 2;
    let meilleurIndex = 0;
    let meilleureDistance = Infinity;
    Array.from(el.children).forEach((enfant, i) => {
      const slide = enfant as HTMLElement;
      const distance = Math.abs(slide.offsetLeft + slide.offsetWidth / 2 - centreCible);
      if (distance < meilleureDistance) {
        meilleureDistance = distance;
        meilleurIndex = i;
      }
    });
    return meilleurIndex;
  }, []);

  useEffect(() => {
    const el = piste.current;
    if (!el) return;
    let armee = false;
    const onScroll = () => {
      if (armee) return;
      armee = true;
      requestAnimationFrame(() => {
        setActif(etapeLaPlusProche());
        armee = false;
      });
    };
    el.addEventListener("scroll", onScroll);
    return () => el.removeEventListener("scroll", onScroll);
  }, [etapeLaPlusProche]);

  const allerA = useCallback(
    (index: number) => {
      const el = piste.current;
      const cible = el?.children[Math.max(0, Math.min(index, etapes.length - 1))] as HTMLElement | undefined;
      if (!el || !cible) return;
      const reduit = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      el.scrollTo({
        left: cible.offsetLeft - (el.clientWidth - cible.offsetWidth) / 2,
        behavior: reduit ? "instant" : "smooth",
      });
    },
    [etapes.length]
  );

  const irA = useCallback(
    (id: string) => {
      const index = etapes.findIndex((e) => e.id === id);
      if (index >= 0) allerA(index);
    },
    [etapes, allerA]
  );

  // Glisser à la souris : le tactile défile nativement (overflow-x:auto
  // suffit), mais rien ne permet de glisser à la souris/au trackpad sans ce
  // geste explicite. scroll-snap coupé pendant le glisser — sinon le
  // navigateur re-snape la position à chaque frame et scrollLeft ne bouge
  // jamais — puis restauré au relâcher en (re)centrant sur l'étape la plus
  // proche.
  useEffect(() => {
    const el = piste.current;
    if (!el) return;
    let bas = false;
    let depart = 0;
    let scrollDepart = 0;
    const onDown = (e: PointerEvent) => {
      if (e.pointerType !== "mouse") return;
      bas = true;
      depart = e.clientX;
      scrollDepart = el.scrollLeft;
      el.style.scrollSnapType = "none";
      el.setPointerCapture(e.pointerId);
    };
    const onMove = (e: PointerEvent) => {
      if (!bas || e.pointerType !== "mouse") return;
      el.scrollLeft = scrollDepart - (e.clientX - depart);
    };
    const onUp = () => {
      if (!bas) return;
      bas = false;
      el.style.scrollSnapType = "";
      allerA(etapeLaPlusProche());
    };
    el.addEventListener("pointerdown", onDown);
    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerup", onUp);
    el.addEventListener("pointercancel", onUp);
    return () => {
      el.removeEventListener("pointerdown", onDown);
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerup", onUp);
      el.removeEventListener("pointercancel", onUp);
    };
  }, [allerA, etapeLaPlusProche]);

  return (
    <div
      className="relative w-screen overflow-hidden"
      style={{ marginInline: "calc(50% - 50vw)" }}
      onKeyDown={(e) => {
        if (e.key === "ArrowLeft") {
          e.preventDefault();
          allerA(actif - 1);
        } else if (e.key === "ArrowRight") {
          e.preventDefault();
          allerA(actif + 1);
        }
      }}
    >
      <div
        ref={piste}
        tabIndex={0}
        role="group"
        aria-label="Écrans du produit — flèches gauche/droite pour naviguer"
        className="flex gap-4 overflow-x-auto snap-x snap-mandatory [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden cursor-grab active:cursor-grabbing focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--harissa)] focus-visible:ring-inset"
        style={{ paddingInline: "25vw" }}
      >
        {etapes.map((etape, i) => (
          <div
            key={etape.id}
            className={`relative shrink-0 snap-center rounded-[2rem] transition-[filter] duration-200 motion-reduce:transition-none ${
              i === actif ? "" : "blur-[2px]"
            }`}
            style={{ width: "50vw" }}
          >
            <CadreAppareil device={device}>{etape.contenu(irA)}</CadreAppareil>
            <div
              aria-hidden
              className={`pointer-events-none absolute inset-0 rounded-[2rem] bg-[rgba(42,27,18,.45)] transition-opacity duration-200 motion-reduce:transition-none ${
                i === actif ? "opacity-0" : "opacity-100"
              }`}
            />
          </div>
        ))}
      </div>

      <FlecheCarrousel direction="left" disabled={actif === 0} onClick={() => allerA(actif - 1)} />
      <FlecheCarrousel direction="right" disabled={actif === etapes.length - 1} onClick={() => allerA(actif + 1)} />

      <p className="text-center text-xs font-semibold text-[var(--ink-faint)] mt-3 sm:hidden">
        ‹ Glissez l&apos;écran pour avancer ›
      </p>
    </div>
  );
}

function FlecheCarrousel({
  direction,
  disabled,
  onClick,
}: {
  direction: "left" | "right";
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={direction === "left" ? "Écran précédent" : "Écran suivant"}
      className={`absolute top-1/2 -translate-y-1/2 z-10 w-9 h-9 rounded-full bg-white shadow-md border border-[var(--line)] flex items-center justify-center text-[var(--encre)] transition-opacity disabled:opacity-0 disabled:pointer-events-none ${
        direction === "left" ? "left-2 sm:left-6" : "right-2 sm:right-6"
      }`}
    >
      <ChevronLeftIcon className={`w-4 h-4 ${direction === "right" ? "rotate-180" : ""}`} />
    </button>
  );
}

// Silhouette d'appareil COMPLÈTE (hauteur réelle via aspect-ratio, encoche ou
// point caméra) plutôt qu'un cadre qui se resserre sur son contenu — un cadre
// trop court se lit comme un fragment d'écran, pas un appareil entier.
//
// max-height + width:auto (jamais une largeur fixe : cela romprait le calcul
// « 1 écran + 2 demis » de EcranCarrousel, qui dimensionne la PISTE en vw) —
// sans ce plafond, un écran à 50vw sur un moniteur large donne un iPhone de
// plus de 1300px de haut, presque vide sous son contenu (retour de Wassim,
// 2026-09-04). La piste, elle, reste à 50vw pile : seul l'appareil DESSINÉ à
// l'intérieur de son emplacement rétrécit et se centre.
function CadreAppareil({ device, children }: { device: "phone" | "tablet"; children: React.ReactNode }) {
  if (device === "tablet") {
    return (
      <div className="aspect-[3/4] max-h-[520px] w-auto mx-auto rounded-[1.9rem] bg-[#15100b] p-4 shadow-[0_30px_60px_-20px_rgba(0,0,0,.7)] flex">
        <span
          aria-hidden
          className="pointer-events-none absolute top-[14px] left-1/2 -translate-x-1/2 w-[5px] h-[5px] rounded-full bg-[rgba(243,236,224,.22)]"
        />
        <div className="flex-1 rounded-2xl bg-[var(--semoule)] overflow-hidden text-left flex flex-col">
          {children}
        </div>
      </div>
    );
  }
  return (
    <div className="aspect-[9/19.5] max-h-[620px] w-auto mx-auto rounded-[2rem] bg-[#180f08] p-2 shadow-[0_30px_60px_-20px_rgba(0,0,0,.7)]">
      <span
        aria-hidden
        className="pointer-events-none absolute top-3 left-1/2 -translate-x-1/2 w-[68px] h-[16px] rounded-[10px] bg-[#180f08] z-10"
      />
      {/* pt-5 : dégage l'encoche (top-3 + h-4 ≈ 28px depuis le cadre, 20px
          depuis ce conteneur une fois le p-2 du cadre déduit) — sans cette
          marge, l'onglet Menu/Panier/Suivi/Paiement du haut de chaque écran
          se retrouvait à moitié caché derrière l'encoche. */}
      <div className="h-full rounded-[1.5rem] bg-[var(--semoule)] overflow-hidden text-left flex flex-col pt-5">
        {children}
      </div>
      <span
        aria-hidden
        className="pointer-events-none absolute bottom-[9px] left-1/2 -translate-x-1/2 w-[88px] h-1 rounded-[3px] bg-[rgba(42,27,18,.3)]"
      />
    </div>
  );
}
