"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Button from "@/components/ui/Button";
import { getToken } from "@/lib/auth";
import Projecteur from "@/components/visite/Projecteur";
import { etapesDe, resoudreVisite, type Parcours } from "@/lib/visite/etapes";
import {
  arreterVisite,
  demarrerVisite,
  enregistrerEtape,
  etapeEnregistree,
  EVENEMENT_VISITE,
  parcoursEnregistre,
  sessionDemo,
  visiteEnCours,
  type SessionDemo,
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
 * seulement via `?visite=1` dans l'URL (le lien « Voir la visite guidée » de
 * la page d'accueil). Cliquer « Voir la démo » n'y suffit plus depuis le
 * 2026-08-27 : ce bouton ouvre directement le tableau de bord de démo, sans
 * bulles par-dessus (voir BoutonVisite.tsx). Un restaurateur qui arrive sur le
 * site n'a donc rien à fermer.
 *
 * Le parcours s'adapte à ce que le visiteur peut réellement ouvrir : sans
 * compte staff, les sept écrans de direction et de service sortent de la
 * liste (voir `acces` dans `etapes.ts`) et une étape de clôture prend leur
 * place. Sinon la visite marchait droit sur `/dashboard`, l'application la
 * renvoyait sur `/login`, et elle restait plantée sur une pastille.
 *
 * Deux parcours qui ne se croisent jamais (voir `Parcours` dans `etapes.ts`) :
 * celui de vente sur l'ordinateur, celui du client sur le téléphone qui a
 * scanné le QR. Sur `/menu/…`, seules les étapes du parcours client
 * s'affichent — jamais la pastille d'une visite en cours ailleurs : l'écran du
 * client attablé doit rester nu.
 */
export default function VisiteGuidee() {
  const router = useRouter();
  const chemin = usePathname();
  const [active, setActive] = useState(false);
  const [parcours, setParcours] = useState<Parcours>("vente");
  const [index, setIndex] = useState(0);
  const [reduite, setReduite] = useState(false);
  const [pret, setPret] = useState(false);
  // Lu dès le premier rendu, pas seulement dans l'effet : à `false` par
  // défaut, un manager voyait « 1/14 » le temps d'une image avant que le
  // compteur ne se corrige en « 1/20 ». Sûr côté serveur — `getToken` y rend
  // `null`, et rien de ce composant n'est rendu avant le montage.
  const [connecte, setConnecte] = useState(() => getToken() !== null);
  const [demo, setDemo] = useState<SessionDemo | null>(null);
  const bulle = useRef<HTMLDivElement>(null);

  // Mémorisé : `aller` en dépend, et un nouveau tableau à chaque rendu
  // réabonnerait le clavier à chaque frappe.
  const etapes = useMemo(() => etapesDe(parcours, connecte), [parcours, connecte]);

  const relire = useCallback(() => {
    const enregistre = parcoursEnregistre();
    setActive(visiteEnCours());
    setParcours(enregistre);
    setIndex(Math.min(etapeEnregistree(), etapesDe(enregistre).length - 1));
    setReduite(false);
    // Relus ici aussi, et pas seulement au changement de page : le bouton
    // « Voir la démo » ouvre une session et pose le jeton juste avant
    // d'émettre l'événement, sans navigation. Sans ces deux lignes, la visite
    // démarrait en « 1/14 » puis sautait à « 9/20 » au premier changement de
    // page — un compteur qui recule au milieu d'une démonstration.
    setConnecte(getToken() !== null);
    setDemo(sessionDemo());
  }, []);

  useEffect(() => {
    // `?visite=1` ouvre au début, `?visite=tarif-pro` (ou `?visite=6`) droit à
    // l'étape — de quoi renvoyer un patron sur le point exact dont on a parlé.
    // Sur la carte d'une table, c'est le parcours client qui s'ouvre.
    // L'événement émis ici ne réveille personne (l'écouteur n'est posé qu'en
    // dessous) : c'est `relire` juste après qui prend l'état en compte.
    const demande = new URLSearchParams(window.location.search).get("visite");
    if (demande) {
      const { parcours: voulu, index: depuis } = resoudreVisite(demande, window.location.pathname);
      demarrerVisite(depuis, voulu);
    }
    relire();
    setPret(true);
    window.addEventListener(EVENEMENT_VISITE, relire);
    return () => window.removeEventListener(EVENEMENT_VISITE, relire);
  }, [relire]);

  const aller = useCallback(
    (cible: number, naviguer: boolean) => {
      const borne = Math.max(0, Math.min(etapes.length - 1, cible));
      const etape = etapes[borne];
      setIndex(borne);
      setReduite(false);
      enregistrerEtape(borne);
      if (naviguer && !surLaRoute(chemin, etape.route)) router.push(etape.lien ?? etape.route);
    },
    [chemin, router, etapes],
  );

  const quitter = useCallback(() => {
    arreterVisite();
    setActive(false);
  }, []);

  // Relu à chaque changement de page, pas seulement au montage : un visiteur
  // qui crée son établissement en cours de visite passe de « sans compte » à
  // « connecté », et les sept écrans de service doivent apparaître.
  useEffect(() => {
    setConnecte(getToken() !== null);
    setDemo(sessionDemo());
  }, [chemin, pret]);

  // Avance seule quand on atterrit sur la page d'une étape plus loin : le
  // restaurateur qui clique le vrai bouton « Créer mon compte » plutôt que
  // « Suivant » doit retrouver la visite au bon endroit. Jamais en arrière,
  // sinon un retour sur l'accueil défait tout le parcours déjà fait.
  useEffect(() => {
    if (!pret || !active) return;
    const trouve = etapes.findIndex((e, i) => i >= index && surLaRoute(chemin, e.route));
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

  // Borné ici et pas ailleurs : la liste raccourcit quand un compte se ferme,
  // et l'étape mémorisée peut alors pointer au-delà de la fin.
  const total = etapes.length;
  const rang = Math.min(index, total - 1);
  const etape = etapes[rang];
  const derniere = rang === total - 1;
  const surLaBonnePage = surLaRoute(chemin, etape.route);

  // La carte d'une table est l'écran d'un client qui mange : une visite en
  // cours ailleurs n'y laisse même pas une pastille.
  if (!surLaBonnePage && surLaRoute(chemin, "/menu")) return null;

  // Hors de la page de l'étape (ou repliée à la main) : une pastille, jamais un
  // panneau qui recouvre un écran dont la visite n'a rien à dire.
  if (!surLaBonnePage || reduite) {
    return (
      <button
        onClick={() => (surLaBonnePage ? setReduite(false) : aller(rang, true))}
        className="fixed bottom-4 right-4 z-[71] rounded-full bg-[var(--harissa)] text-[var(--semoule)] shadow-lg px-4 py-3 text-sm font-medium"
      >
        Visite guidée {rang + 1}/{total}
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
        aria-label={`Visite guidée, étape ${rang + 1} sur ${total}`}
        className="rounded-xl bg-white shadow-xl border border-[var(--line)] p-4 outline-none"
      >
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--harissa)]">
            Visite guidée · {rang + 1}/{total}
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
            style={{ width: `${((rang + 1) / total) * 100}%` }}
          />
        </div>

        <h2 className="mt-3 text-base font-semibold text-[var(--encre)]">{etape.titre}</h2>
        <p className="mt-1.5 text-sm leading-relaxed text-[var(--ink-soft)]">{etape.corps}</p>

        {/* Le seul chemin vers le parcours client depuis un ordinateur : il
            faut le `qr_token` de la démo, qu'aucun texte figé ne peut porter.
            Absent si la démo n'a pas pu s'ouvrir — le texte de l'étape reste
            vrai, il parle alors du QR posé sur la table. */}
        {etape.carteDemo && demo && (
          <a
            href={`/menu/${demo.qrToken}?visite=1`}
            className="mt-3 inline-block text-sm font-medium underline text-[var(--menthe)]"
          >
            Ouvrir la carte de la table 1 →
          </a>
        )}

        <div className="mt-4 flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => aller(rang - 1, true)} disabled={rang === 0}>
            Précédent
          </Button>
          {derniere ? (
            <Button size="sm" onClick={quitter} className="flex-1">
              Terminer
            </Button>
          ) : (
            <Button size="sm" onClick={() => aller(rang + 1, true)} className="flex-1">
              Suivant
            </Button>
          )}
        </div>
      </div>
    </Projecteur>
  );
}
