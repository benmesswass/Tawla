"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { EVENEMENT_VISITE, sessionDemo, type SessionDemo } from "@/lib/visite/etat";

function restant(expireLe: string): string {
  const minutes = Math.max(0, Math.round((new Date(expireLe).getTime() - Date.now()) / 60000));
  if (minutes >= 60) {
    const heures = Math.floor(minutes / 60);
    return `${heures} h ${String(minutes % 60).padStart(2, "0")}`;
  }
  return `${minutes} min`;
}

/**
 * Rappelle que l'établissement ouvert est une démonstration temporaire.
 *
 * Ce n'est pas de la décoration : le visiteur est connecté en manager sur un
 * vrai tableau de bord, avec de vraies tables. Sans ce rappel, il croit avoir
 * un compte — et découvre deux heures plus tard que tout a disparu. Le dire
 * d'avance est la seule version honnête.
 *
 * Absent du parcours client (`/menu/…`) : cet écran est celui d'un convive
 * attablé, il doit rester nu.
 */
export default function BandeauDemo() {
  const chemin = usePathname();
  const [session, setSession] = useState<SessionDemo | null>(null);

  useEffect(() => {
    const relire = () => setSession(sessionDemo());
    relire();
    // Une minute suffit : le bandeau donne un ordre de grandeur, pas l'heure.
    const horloge = setInterval(relire, 60_000);
    window.addEventListener(EVENEMENT_VISITE, relire);
    return () => {
      clearInterval(horloge);
      window.removeEventListener(EVENEMENT_VISITE, relire);
    };
  }, [chemin]);

  if (!session || chemin === "/menu" || chemin.startsWith("/menu/")) return null;

  return (
    <div
      className="fixed top-0 inset-x-0 z-[60] flex justify-center px-3 pt-2 pointer-events-none"
      role="status"
    >
      <p className="rounded-full bg-[var(--espresso)] text-[var(--semoule)] text-xs px-3.5 py-1.5 shadow-lg">
        Démonstration — établissement temporaire, effacé dans {restant(session.expireLe)}
      </p>
    </div>
  );
}
