"use client";

import { useEffect } from "react";

// Enregistrement du service worker (installabilité PWA + secours cache
// hors-ligne, voir public/sw.js) — silencieux si le navigateur ne le
// supporte pas, ce n'est jamais bloquant pour le reste de l'app.
export default function ServiceWorkerRegister() {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    }
  }, []);

  return null;
}
