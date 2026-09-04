"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Mécanique de carrousel partagée par les vitrines Client/Manager/Serveur de
 * ApercuProduit.tsx (Phase D2bis, exploration validée par Wassim le
 * 2026-09-04 : « je veux 3 iPhones distincts côte à côte », mockup dans
 * l'artifact « Home version problème »). La Cuisine n'en fait pas partie :
 * poste fixe unique, un seul écran à onglets (voir EcranCuisine).
 *
 * Débordement volontaire hors de son conteneur (max-w-4xl sur la home) vers
 * la pleine largeur de la fenêtre : sans lui, l'écran voisin ne serait pas
 * visible à moitié sur les côtés — tout l'intérêt du "3 iPhones distincts
 * côte à côte" par rapport à l'ancien switcher à onglets à un seul écran.
 * Largeur d'écran FIXE (pas en vw comme le prototype HTML) : un carrousel en
 * pourcentage de la fenêtre donnerait des iPhones énormes sur un écran de
 * bureau large — la marge de défilement (calc(50% - moitié de l'écran)) fait
 * le même effet de centrage quelle que soit la largeur de la fenêtre.
 */

export type EtapeCarrousel = {
  id: string;
  label: string;
  contenu: React.ReactNode;
};

const LARGEUR: Record<"phone" | "tablet", number> = { phone: 264, tablet: 360 };

export default function EcranCarrousel({
  etapes,
  device,
}: {
  etapes: EtapeCarrousel[];
  device: "phone" | "tablet";
}) {
  const largeur = LARGEUR[device];
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

  const allerA = useCallback((index: number) => {
    const el = piste.current;
    const cible = el?.children[index] as HTMLElement | undefined;
    if (!el || !cible) return;
    const reduit = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    el.scrollTo({
      left: cible.offsetLeft - (el.clientWidth - cible.offsetWidth) / 2,
      behavior: reduit ? "instant" : "smooth",
    });
  }, []);

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
    <div>
      <div className="w-screen overflow-hidden" style={{ marginInline: "calc(50% - 50vw)" }}>
        <div
          ref={piste}
          className="flex gap-4 overflow-x-auto snap-x snap-mandatory [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden cursor-grab active:cursor-grabbing"
          style={{ paddingInline: `calc(50% - ${largeur / 2}px)` }}
        >
          {etapes.map((etape, i) => (
            <div
              key={etape.id}
              className={`relative shrink-0 snap-center rounded-[2rem] transition-[filter] duration-200 motion-reduce:transition-none ${
                i === actif ? "" : "blur-[2px]"
              }`}
              style={{ width: largeur }}
            >
              <CadreAppareil device={device}>{etape.contenu}</CadreAppareil>
              <div
                aria-hidden
                className={`pointer-events-none absolute inset-0 rounded-[2rem] bg-[rgba(42,27,18,.45)] transition-opacity duration-200 motion-reduce:transition-none ${
                  i === actif ? "opacity-0" : "opacity-100"
                }`}
              />
            </div>
          ))}
        </div>
      </div>

      <p className="text-center text-xs font-semibold text-[var(--ink-faint)] mt-3 sm:hidden">
        ‹ Glissez l&apos;écran pour avancer ›
      </p>

      <div className="flex flex-wrap justify-center gap-1.5 mt-3">
        {etapes.map((etape, i) => (
          <button
            key={etape.id}
            type="button"
            onClick={() => allerA(i)}
            aria-current={i === actif}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold transition-colors duration-200 ${
              i === actif
                ? "bg-[var(--harissa)] text-[var(--semoule)]"
                : "bg-[var(--creme)] text-[var(--ink-soft)] hover:bg-[var(--line)]"
            }`}
          >
            {etape.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// Silhouette d'appareil COMPLÈTE (hauteur réelle via aspect-ratio, encoche ou
// point caméra) plutôt qu'un cadre qui se resserre sur son contenu — un cadre
// trop court se lit comme un fragment d'écran, pas un appareil entier.
function CadreAppareil({ device, children }: { device: "phone" | "tablet"; children: React.ReactNode }) {
  if (device === "tablet") {
    return (
      <div className="aspect-[3/4] rounded-[1.9rem] bg-[#15100b] p-4 shadow-[0_30px_60px_-20px_rgba(0,0,0,.7)] flex">
        <span className="absolute top-[14px] left-1/2 -translate-x-1/2 w-[5px] h-[5px] rounded-full bg-[rgba(243,236,224,.22)]" />
        <div className="flex-1 rounded-2xl bg-[var(--semoule)] overflow-hidden text-left">{children}</div>
      </div>
    );
  }
  return (
    <div className="aspect-[9/19.5] rounded-[2rem] bg-[#180f08] p-2 shadow-[0_30px_60px_-20px_rgba(0,0,0,.7)]">
      <span className="absolute top-3 left-1/2 -translate-x-1/2 w-[68px] h-[16px] rounded-[10px] bg-[#180f08] z-10" />
      <div className="h-full rounded-[1.5rem] bg-[var(--semoule)] overflow-hidden text-left">{children}</div>
      <span className="absolute bottom-[9px] left-1/2 -translate-x-1/2 w-[88px] h-1 rounded-[3px] bg-[rgba(42,27,18,.3)]" />
    </div>
  );
}
