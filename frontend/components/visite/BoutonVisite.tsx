"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { trackEvent } from "@/lib/analytics";
import { setToken } from "@/lib/auth";
import { enregistrerSessionDemo } from "@/lib/visite/etat";

/**
 * `POST /api/v1/demo/sessions` répond en une seule transaction — pas de
 * vraies étapes à faire remonter du backend. Mais le palier gratuit Render
 * met le service en veille après 15 min d'inactivité (voir
 * `AUDIT_COUTS_PRODUCTION.md` §4.1), et le réveil rapproche l'attente réelle
 * de la minute : sans rien à l'écran pendant tout ce temps, le bouton a l'air
 * bloqué. Ces libellés décrivent ce que `creer_demo` fait réellement
 * (équipe, tables, carte) dans l'ordre où ça se produit — une approximation
 * du vrai déroulé, pas des étapes mesurées. Affichés sous le bouton, pas
 * dedans : le bouton garde toujours le même texte (« Préparation… ») pour ne
 * pas changer de largeur à chaque étape.
 */
const ETAPES_PREPARATION = [
  "Création de l'établissement…",
  "Ajout de l'équipe (manager, serveur, cuisine)…",
  "Installation des tables et QR codes…",
  "Chargement de la carte…",
  "Presque prêt…",
];
const INTERVALLE_ETAPE_MS = 3000;

/**
 * Ouvre un établissement de démonstration jetable (`POST /api/v1/demo/sessions`),
 * connecte le visiteur dessus en manager, et l'emmène directement sur son
 * tableau de bord déjà peuplé (équipe, tables et QR codes, carte). Un
 * établissement par visiteur, jamais un compte partagé — voir
 * `backend/app/modules/demo/service.py`.
 *
 * Ne démarre plus la visite guidée automatiquement (retour de Wassim après une
 * démo client, 2026-08-27 : les bulles qui s'ouvrent en même temps que le
 * tableau de bord rendent le parcours illisible pendant une démo commentée en
 * direct). La visite reste accessible à la demande, via `?visite=1` ou le lien
 * « Voir la visite guidée » de la page d'accueil.
 *
 * Le libellé dit « démo » parce que c'est le mot du restaurateur ; le code
 * garde « visite » partout pour le mécanisme sous-jacent, pour ne pas se
 * confondre avec `?demo=1`, qui est l'aide-mémoire du vendeur
 * (`components/DemoGuide.tsx`).
 */
export default function BoutonVisite({
  className = "",
  libelle = "Voir la démo",
  etapeClassName = "text-[var(--ink-soft)]",
}: {
  className?: string;
  libelle?: string;
  /** Couleur du message d'étape, à adapter au fond derrière le bouton
   * (le composant ne connaît pas son contexte d'appel). */
  etapeClassName?: string;
}) {
  const router = useRouter();
  const [enCours, setEnCours] = useState(false);
  const [etapeIndex, setEtapeIndex] = useState(0);

  useEffect(() => {
    if (!enCours) {
      setEtapeIndex(0);
      return;
    }
    const intervalle = setInterval(() => {
      setEtapeIndex((i) => Math.min(i + 1, ETAPES_PREPARATION.length - 1));
    }, INTERVALLE_ETAPE_MS);
    return () => clearInterval(intervalle);
  }, [enCours]);

  async function ouvrir() {
    if (enCours) return;
    trackEvent("demo_clicked");
    setEnCours(true);
    try {
      const session = await api.createDemoSession();
      setToken(session.access_token);
      enregistrerSessionDemo({
        qrToken: session.qr_token,
        expireLe: session.expires_at,
        nom: session.restaurant_name,
        managerToken: session.access_token,
        waiterToken: session.waiter_access_token,
        kitchenToken: session.kitchen_access_token,
      });
      router.push("/dashboard");
    } catch {
      // Silencieux volontairement : le visiteur n'a pas demandé un compte, il
      // a demandé à voir le produit — rien à ouvrir si la démo échoue
      // maintenant (API injoignable, plafond atteint).
    } finally {
      setEnCours(false);
    }
  }

  return (
    <span className="relative inline-block">
      <button type="button" onClick={ouvrir} disabled={enCours} className={className}>
        {enCours ? "Préparation…" : libelle}
      </button>
      {enCours && (
        <span
          className={`pointer-events-none absolute left-0 top-full mt-1 w-max max-w-[16rem] text-xs ${etapeClassName}`}
        >
          {ETAPES_PREPARATION[etapeIndex]}
        </span>
      )}
    </span>
  );
}
