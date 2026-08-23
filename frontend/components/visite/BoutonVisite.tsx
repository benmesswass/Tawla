"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { setToken } from "@/lib/auth";
import { demarrerVisite, enregistrerSessionDemo } from "@/lib/visite/etat";

/**
 * Démarre la visite guidée depuis la page d'accueil, qui est un composant
 * serveur — d'où ce bouton client minuscule plutôt qu'un `onClick` sur place.
 *
 * Il ouvre d'abord un établissement de démonstration jetable
 * (`POST /api/v1/demo/sessions`) et connecte le visiteur dessus : sans compte,
 * la visite s'arrête à la porte du tableau de bord, et le parcours client est
 * hors de portée faute de connaître une table. Un établissement par visiteur,
 * jamais un compte partagé — voir `backend/app/modules/demo/service.py`.
 *
 * Si l'ouverture échoue (API injoignable, plafond de démos atteint), la visite
 * démarre quand même, en version visiteur : mieux vaut quatorze étapes qu'un
 * bouton qui ne fait rien.
 *
 * Le libellé dit « démo » parce que c'est le mot du restaurateur ; le code
 * garde « visite » partout, pour ne pas se confondre avec `?demo=1`, qui est
 * l'aide-mémoire du vendeur (`components/DemoGuide.tsx`).
 */
export default function BoutonVisite({
  className = "",
  libelle = "Voir la démo",
}: {
  className?: string;
  libelle?: string;
}) {
  const [enCours, setEnCours] = useState(false);

  async function ouvrir() {
    if (enCours) return;
    setEnCours(true);
    try {
      const session = await api.createDemoSession();
      setToken(session.access_token);
      enregistrerSessionDemo({
        qrToken: session.qr_token,
        expireLe: session.expires_at,
        nom: session.restaurant_name,
      });
    } catch {
      // Silencieux volontairement : le visiteur n'a pas demandé un compte, il
      // a demandé à voir le produit. Il le verra, en version réduite.
    } finally {
      setEnCours(false);
      demarrerVisite();
    }
  }

  return (
    <button type="button" onClick={ouvrir} disabled={enCours} className={className}>
      {enCours ? "Préparation…" : libelle}
    </button>
  );
}
