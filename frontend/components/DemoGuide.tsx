"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Button from "@/components/ui/Button";

const STEPS = [
  {
    route: "/menu",
    title: "Client — scanner le QR",
    body: "Scannez le QR sur votre téléphone, parcourez la carte catégorisée, ajoutez 2-3 plats, laissez une note à la cuisine sur un plat, validez la commande. À souligner : zéro app à télécharger, ça marche en 10 secondes.",
  },
  {
    route: "/menu",
    title: "Mode hors ligne — le point fort",
    body: "Coupez le réseau du téléphone puis ajoutez un plat au panier. Montrez le message « enregistrée sur votre téléphone, envoyée automatiquement dès que la connexion revient ». Réactivez le réseau : la commande part seule.",
  },
  {
    route: "/staff",
    title: "Serveur — pool partagé",
    body: "Connectez-vous en tant que serveur. La commande apparaît dans le pool partagé. Cliquez Prendre en charge puis Confirmé vers cuisine.",
  },
  {
    route: "/kitchen",
    title: "Cuisine — le temps réel",
    body: "Connectez-vous en tant que cuisine. Le ticket apparaît en direct, sans rafraîchissement (WebSocket). Cliquez Commencer puis Prêt.",
  },
  {
    route: "/staff",
    title: "Paiement",
    body: "Retour côté serveur : encaissez en espèces, ou montrez le paiement carte simulé. Cliquez Payé.",
  },
  {
    route: "/dashboard",
    title: "Manager — l'écran qui vend",
    body: "Connectez-vous en tant que manager. Montrez la recette du jour, les commandes perdues, et /dashboard/preuve. Gardez cet écran ouvert le plus longtemps — c'est ce qui justifie le prix.",
  },
  {
    route: "/signup",
    title: "Si la question du prix arrive",
    body: "Les 3 paliers cliquables (Essentiel 50 / Pro 100 / Business 150 DT). Le prix ne bouge jamais une fois annoncé à un restaurateur.",
  },
];

function matchesRoute(pathname: string, route: string): boolean {
  return pathname === route || pathname.startsWith(`${route}/`);
}

const STORAGE_ACTIVE = "tawlaDemoGuideActive";
const STORAGE_STEP = "tawlaDemoGuideStep";
const STORAGE_COLLAPSED = "tawlaDemoGuideCollapsed";

// Aide-mémoire de démo pour Wassim, pas un tour guidé client : activé une
// fois via ?demo=1, puis persisté en localStorage pour survivre à la
// navigation entre /menu, /staff, /kitchen, /dashboard et /signup.
export default function DemoGuide() {
  const pathname = usePathname();
  const [active, setActive] = useState(false);
  const [step, setStep] = useState(0);
  const [collapsed, setCollapsed] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("demo") === "1") {
      localStorage.setItem(STORAGE_ACTIVE, "1");
      localStorage.setItem(STORAGE_STEP, "0");
      localStorage.removeItem(STORAGE_COLLAPSED);
    }
    setActive(localStorage.getItem(STORAGE_ACTIVE) === "1");
    setStep(Number(localStorage.getItem(STORAGE_STEP) ?? 0));
    setCollapsed(localStorage.getItem(STORAGE_COLLAPSED) === "1");
    setReady(true);
  }, []);

  function goTo(next: number) {
    const clamped = Math.max(0, Math.min(STEPS.length - 1, next));
    setStep(clamped);
    localStorage.setItem(STORAGE_STEP, String(clamped));
  }

  // Avance automatiquement dès qu'une page correspond à une étape plus loin
  // dans le parcours — jamais en arrière, pour ne pas défaire une avance
  // manuelle (ex: repasser par /staff après la cuisine, pour le paiement).
  useEffect(() => {
    if (!ready || !active) return;
    const matchIndex = STEPS.findIndex((s, i) => i >= step && matchesRoute(pathname, s.route));
    if (matchIndex !== -1 && matchIndex !== step) goTo(matchIndex);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname, ready, active]);

  function toggleCollapsed(next: boolean) {
    setCollapsed(next);
    localStorage.setItem(STORAGE_COLLAPSED, next ? "1" : "0");
  }

  function quit() {
    localStorage.removeItem(STORAGE_ACTIVE);
    localStorage.removeItem(STORAGE_STEP);
    localStorage.removeItem(STORAGE_COLLAPSED);
    setActive(false);
  }

  if (!ready || !active) return null;

  if (collapsed) {
    return (
      <button
        onClick={() => toggleCollapsed(false)}
        className="fixed bottom-4 right-4 z-[60] rounded-full bg-[var(--harissa)] text-[var(--semoule)] shadow-lg px-4 py-3 text-sm font-medium"
      >
        Démo {step + 1}/{STEPS.length}
      </button>
    );
  }

  const current = STEPS[step];

  return (
    <div
      role="dialog"
      aria-label="Guide de démo"
      className="fixed bottom-4 right-4 z-[60] w-[calc(100vw-2rem)] max-w-sm rounded-xl bg-white shadow-lg border border-[var(--line)] p-4"
    >
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--harissa)]">
          Guide démo · {step + 1}/{STEPS.length}
        </p>
        <div className="flex items-center gap-3">
          <button
            onClick={() => toggleCollapsed(true)}
            className="text-xs text-[var(--ink-soft)] hover:text-[var(--encre)]"
            aria-label="Réduire"
          >
            Réduire
          </button>
          <button onClick={quit} className="text-xs text-[var(--ink-soft)] hover:text-[var(--encre)]" aria-label="Quitter la démo">
            ✕
          </button>
        </div>
      </div>
      <h2 className="mt-1 text-base font-semibold text-[var(--encre)]">{current.title}</h2>
      <p className="mt-2 text-sm text-[var(--ink-soft)]">{current.body}</p>
      <div className="mt-4 flex gap-2">
        <Button variant="secondary" size="sm" onClick={() => goTo(step - 1)} disabled={step === 0}>
          Précédent
        </Button>
        {step < STEPS.length - 1 ? (
          <Button size="sm" onClick={() => goTo(step + 1)} className="flex-1">
            Suivant
          </Button>
        ) : (
          <Button size="sm" onClick={quit} className="flex-1">
            Terminer
          </Button>
        )}
      </div>
    </div>
  );
}
