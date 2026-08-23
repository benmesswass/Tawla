"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Button from "@/components/ui/Button";
import Projecteur from "@/components/visite/Projecteur";
import { ETAPES, indexEtape } from "@/lib/visite/etapes";
import {
  arreterVisite,
  demarrerVisite,
  enregistrerEtape,
  etapeEnregistree,
  EVENEMENT_VISITE,
  visiteEnCours,
} from "@/lib/visite/etat";

function surLaRoute(chemin: string, route: string): boolean {
  return chemin === route || chemin.startsWith(`${route}/`);
}

/**
 * Visite guidée du produit, façon bulle d'aide pas à pas — sans dépendance ni
 * service tiers.
 *
 * Montée une fois dans le layout, elle survit à la navigation : les étapes
 * portent leur route, « Suivant » emmène sur la page suivante quand il faut, et
 * la position est gardée en localStorage. Elle ne démarre jamais toute seule —
 * `?visite=1` dans l'URL, ou le bouton « Visite guidée » de la page d'accueil.
 * Un restaurateur qui arrive sur le site n'a donc rien à fermer.
 *
 * Elle ne s'affiche pas sur le parcours client (`/menu/…`) : cet écran-là est
 * celui du client attablé, il doit rester nu même pendant une démonstration.
 */
export default function VisiteGuidee() {
  const router = useRouter();
  const chemin = usePathname();
  const [active, setActive] = useState(false);
  const [index, setIndex] = useState(0);
  const [reduite, setReduite] = useState(false);
  const [pret, setPret] = useState(false);
  const bulle = useRef<HTMLDivElement>(null);

  const relire = useCallback(() => {
    setActive(visiteEnCours());
    setIndex(Math.min(etapeEnregistree(), ETAPES.length - 1));
    setReduite(false);
  }, []);

  useEffect(() => {
    // `?visite=1` ouvre au début, `?visite=tarif-pro` (ou `?visite=6`) droit à
    // l'étape — de quoi renvoyer un patron sur le point exact dont on a parlé.
    // L'événement émis ici ne réveille personne (l'écouteur n'est posé qu'en
    // dessous) : c'est `relire` juste après qui prend l'état en compte.
    const demande = new URLSearchParams(window.location.search).get("visite");
    if (demande) demarrerVisite(indexEtape(demande));
    relire();
    setPret(true);
    window.addEventListener(EVENEMENT_VISITE, relire);
    return () => window.removeEventListener(EVENEMENT_VISITE, relire);
  }, [relire]);

  const aller = useCallback(
    (cible: number, naviguer: boolean) => {
      const borne = Math.max(0, Math.min(ETAPES.length - 1, cible));
      const etape = ETAPES[borne];
      setIndex(borne);
      setReduite(false);
      enregistrerEtape(borne);
      if (naviguer && !surLaRoute(chemin, etape.route)) router.push(etape.lien ?? etape.route);
    },
    [chemin, router],
  );

  const quitter = useCallback(() => {
    arreterVisite();
    setActive(false);
  }, []);

  // Avance seule quand on atterrit sur la page d'une étape plus loin : le
  // restaurateur qui clique le vrai bouton « Créer mon compte » plutôt que
  // « Suivant » doit retrouver la visite au bon endroit. Jamais en arrière,
  // sinon un retour sur l'accueil défait tout le parcours déjà fait.
  useEffect(() => {
    if (!pret || !active) return;
    const trouve = ETAPES.findIndex((e, i) => i >= index && surLaRoute(chemin, e.route));
    if (trouve !== -1 && trouve !== index) aller(trouve, false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chemin, pret, active]);

  useEffect(() => {
    if (!active || reduite) return;
    function auClavier(e: KeyboardEvent) {
      if (e.key === "Escape") {
        quitter();
        return;
      }
      // Les flèches appartiennent au champ qu'on est en train de remplir —
      // la visite passe par-dessus le formulaire d'inscription.
      const cible = e.target as HTMLElement | null;
      if (cible && ["INPUT", "TEXTAREA", "SELECT"].includes(cible.tagName)) return;
      if (e.key === "ArrowRight") aller(index + 1, true);
      if (e.key === "ArrowLeft") aller(index - 1, true);
    }
    window.addEventListener("keydown", auClavier);
    return () => window.removeEventListener("keydown", auClavier);
  }, [active, reduite, index, aller, quitter]);

  // Le lecteur d'écran doit entendre la nouvelle étape ; `preventScroll` pour
  // ne pas contrarier le défilement vers la cible lancé par le projecteur.
  useEffect(() => {
    if (!active || reduite) return;
    bulle.current?.focus({ preventScroll: true });
  }, [index, active, reduite]);

  if (!pret || !active) return null;
  if (surLaRoute(chemin, "/menu")) return null;

  const etape = ETAPES[index];
  const total = ETAPES.length;
  const derniere = index === total - 1;
  const surLaBonnePage = surLaRoute(chemin, etape.route);

  // Hors de la page de l'étape (ou repliée à la main) : une pastille, jamais un
  // panneau qui recouvre un écran dont la visite n'a rien à dire.
  if (!surLaBonnePage || reduite) {
    return (
      <button
        onClick={() => (surLaBonnePage ? setReduite(false) : aller(index, true))}
        className="fixed bottom-4 right-4 z-[71] rounded-full bg-[var(--harissa)] text-[var(--semoule)] shadow-lg px-4 py-3 text-sm font-medium"
      >
        Visite guidée {index + 1}/{total}
        {!surLaBonnePage && " · reprendre"}
      </button>
    );
  }

  return (
    <Projecteur cible={etape.cible} cle={etape.id}>
      <div
        ref={bulle}
        tabIndex={-1}
        role="dialog"
        aria-label={`Visite guidée, étape ${index + 1} sur ${total}`}
        className="rounded-xl bg-white shadow-xl border border-[var(--line)] p-4 outline-none"
      >
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--harissa)]">
            Visite guidée · {index + 1}/{total}
          </p>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setReduite(true)}
              className="text-xs text-[var(--ink-soft)] hover:text-[var(--encre)]"
            >
              Réduire
            </button>
            <button
              onClick={quitter}
              aria-label="Quitter la visite guidée"
              className="text-xs text-[var(--ink-soft)] hover:text-[var(--encre)]"
            >
              ✕
            </button>
          </div>
        </div>

        <div className="mt-2 h-1 rounded-full bg-[var(--line)]" aria-hidden>
          <div
            className="h-1 rounded-full bg-[var(--harissa)] transition-[width] duration-200"
            style={{ width: `${((index + 1) / total) * 100}%` }}
          />
        </div>

        <h2 className="mt-3 text-base font-semibold text-[var(--encre)]">{etape.titre}</h2>
        <p className="mt-1.5 text-sm leading-relaxed text-[var(--ink-soft)]">{etape.corps}</p>

        <div className="mt-4 flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => aller(index - 1, true)} disabled={index === 0}>
            Précédent
          </Button>
          {derniere ? (
            <Button size="sm" onClick={quitter} className="flex-1">
              Terminer
            </Button>
          ) : (
            <Button size="sm" onClick={() => aller(index + 1, true)} className="flex-1">
              Suivant
            </Button>
          )}
        </div>
      </div>
    </Projecteur>
  );
}
