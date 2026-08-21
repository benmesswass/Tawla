// Secret de l'écran admin (2026-08-20) — distinct du JWT staff (auth.ts) :
// pas un compte, un mot de passe unique que Wassim seul détient.
const ADMIN_SECRET_KEY = "tawla_admin_secret";

export function getAdminSecret(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ADMIN_SECRET_KEY);
}

export function setAdminSecret(secret: string): void {
  localStorage.setItem(ADMIN_SECRET_KEY, secret);
}

export function clearAdminSecret(): void {
  localStorage.removeItem(ADMIN_SECRET_KEY);
}
