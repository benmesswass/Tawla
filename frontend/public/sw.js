// Service worker minimal : réseau d'abord, secours cache si hors-ligne.
// Aucun pré-chargement à l'installation (les URLs du menu sont dynamiques
// par QR token) — le cache se remplit au fil de la navigation réelle,
// suffisant pour que l'app rouvre depuis le cache pendant une coupure.
const CACHE_NAME = "tawla-shell-v1";

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
