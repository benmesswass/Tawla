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

// Notification "commande prête" — opt-in explicite du client sur la page
// de suivi (voir menu/[qrToken]/page.tsx), touche l'appareil même si
// l'onglet a été quitté, contrairement au WebSocket de suivi seul.
self.addEventListener("push", (event) => {
  let payload = { title: "Tawla", body: "Votre commande a évolué." };
  if (event.data) {
    try {
      payload = event.data.json();
    } catch {
      payload.body = event.data.text();
    }
  }

  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body,
      icon: "/pwa-icon-192",
      badge: "/pwa-icon-192",
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clientList) => {
      if (clientList.length > 0) return clientList[0].focus();
      return self.clients.openWindow("/");
    })
  );
});
