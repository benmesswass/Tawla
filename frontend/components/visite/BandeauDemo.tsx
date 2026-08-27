"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { EVENEMENT_VISITE, sessionDemo, type SessionDemo } from "@/lib/visite/etat";
import { lienDemo } from "@/lib/demoLien";

function restant(expireLe: string): string {
  const minutes = Math.max(0, Math.round((new Date(expireLe).getTime() - Date.now()) / 60000));
  if (minutes >= 60) {
    const heures = Math.floor(minutes / 60);
    return `${heures} h ${String(minutes % 60).padStart(2, "0")}`;
  }
  return `${minutes} min`;
}

const ROLES: { route: string; label: string; champ: keyof Pick<SessionDemo, "managerToken" | "waiterToken" | "kitchenToken"> }[] = [
  { route: "/dashboard", label: "Tableau de bord", champ: "managerToken" },
  { route: "/staff", label: "Écran serveur", champ: "waiterToken" },
  { route: "/kitchen", label: "Écran cuisine", champ: "kitchenToken" },
];

/**
 * Rappelle que l'établissement ouvert est une démonstration temporaire, et
 * donne un lien par rôle pour l'ouvrir, déjà connecté, sur un AUTRE appareil.
 *
 * Le rappel d'échéance n'est pas de la décoration : le visiteur est connecté
 * en manager sur un vrai tableau de bord, avec de vraies tables. Sans lui, il
 * croit avoir un compte — et découvre deux heures plus tard que tout a
 * disparu.
 *
 * Les liens résolvent un vrai mur : montrer Tawla à un restaurateur en
 * commandant depuis son téléphone pendant que l'écran serveur reste ouvert
 * ailleurs est impossible sur un seul onglet — et les comptes serveur/cuisine
 * de la démo ont un mot de passe généré aléatoirement, jamais révélé (voir
 * `backend/app/modules/demo/service.py`), donc aucun moyen de s'y connecter
 * à la main sur un deuxième appareil. Un lien copié ouvre l'écran sans mot de
 * passe (`lib/demoLien.ts`).
 *
 * Absent du parcours client (`/menu/…`) : cet écran est celui d'un convive
 * attablé, il doit rester nu.
 */
export default function BandeauDemo() {
  const chemin = usePathname();
  const [session, setSession] = useState<SessionDemo | null>(null);
  const [ouvert, setOuvert] = useState(false);
  const [copie, setCopie] = useState<string | null>(null);

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

  async function copier(route: string, jeton: string) {
    try {
      await navigator.clipboard.writeText(lienDemo(route, jeton));
      setCopie(route);
      setTimeout(() => setCopie((c) => (c === route ? null : c)), 2000);
    } catch {
      // Presse-papiers indisponible (contexte non sécurisé, permission
      // refusée) : le bouton reste cliquable, seule la confirmation manque.
    }
  }

  return (
    // Positionnement (fixed/z-index) porté par le conteneur commun dans
    // app/layout.tsx, partagé avec BandeauAutreMarche — pour que les deux
    // s'empilent au lieu de se superposer quand les deux sont visibles.
    <div className="pointer-events-auto flex flex-col items-center gap-2" role="status">
      <div className="flex items-center gap-1.5 rounded-full bg-[var(--espresso)] text-[var(--semoule)] text-xs pl-3.5 pr-1.5 py-1.5 shadow-lg">
        <span>Démonstration — effacée dans {restant(session.expireLe)}</span>
        {/* Bouton distinct de l'annonce du délai : la phrase seule ne se
            lisait pas comme cliquable (retour de Wassim après une démo
            client, 2026-08-27). */}
        <button
          onClick={() => setOuvert((o) => !o)}
          className="flex items-center gap-1 rounded-full bg-white/15 hover:bg-white/25 px-2.5 py-1 font-medium transition-colors"
        >
          {ouvert ? "Masquer" : "Partager sur un autre appareil"}
          <span aria-hidden className={`inline-block transition-transform ${ouvert ? "rotate-180" : ""}`}>
            ▾
          </span>
        </button>
      </div>

      {ouvert && (
        <div className="w-[calc(100vw-1.5rem)] max-w-sm rounded-xl bg-white shadow-xl border border-[var(--line)] p-3 flex flex-col gap-2">
          <p className="text-xs text-[var(--ink-soft)]">
            Ouvre l&apos;écran, déjà connecté, sur un ordinateur ou une tablette — pour montrer le service en direct pendant qu&apos;un client commande sur son téléphone.
          </p>
          <p className="text-xs text-[var(--harissa)]">
            Un appareil par lien : les ouvrir dans deux onglets du même navigateur déconnecte le premier.
          </p>
          {ROLES.map((r) => (
            <div key={r.route} className="flex items-center justify-between gap-2">
              <span className="text-sm text-[var(--encre)]">{r.label}</span>
              <button
                onClick={() => copier(r.route, session[r.champ])}
                className="shrink-0 text-xs font-medium rounded-full border border-[var(--line)] px-3 py-1.5 text-[var(--harissa)]"
              >
                {copie === r.route ? "Copié ✓" : "Copier le lien"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
