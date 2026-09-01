"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { trackEvent } from "@/lib/analytics";
import { setToken } from "@/lib/auth";
import { enregistrerSessionDemo } from "@/lib/visite/etat";

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
}: {
  className?: string;
  libelle?: string;
}) {
  const router = useRouter();
  const [enCours, setEnCours] = useState(false);

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
    <button type="button" onClick={ouvrir} disabled={enCours} className={className}>
      {enCours ? "Préparation…" : libelle}
    </button>
  );
}
