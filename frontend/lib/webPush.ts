// Web Push exige la clé VAPID en Uint8Array, pas en base64url brut —
// conversion standard, aucune lib externe nécessaire pour ça. Partagée entre
// le parcours client (menu/[qrToken]/page.tsx) et l'écran serveur
// (app/staff/page.tsx), qui s'abonnent tous les deux.
export function urlBase64ToUint8Array(base64url: string): Uint8Array {
  const padding = "=".repeat((4 - (base64url.length % 4)) % 4);
  const base64 = (base64url + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}
