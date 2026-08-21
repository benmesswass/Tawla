"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { platformAdminApi, PlatformAdminApiError, setAdminToken } from "@/lib/platformAdmin";
import { hankenGrotesk, lalezar } from "@/lib/fonts";
import TawlaMark from "@/components/brand/TawlaMark";

function errorMessage(err: unknown): string {
  if (err instanceof PlatformAdminApiError && err.code === "INVALID_CREDENTIALS") {
    return "E-mail ou mot de passe incorrect.";
  }
  if (err instanceof PlatformAdminApiError && err.code === "ACCOUNT_DISABLED") {
    return "Ce compte a été désactivé.";
  }
  if (err instanceof PlatformAdminApiError && err.code === "RATE_LIMITED") {
    return "Trop de tentatives. Patientez une minute avant de réessayer.";
  }
  return "Une erreur est survenue. Réessayez dans un instant.";
}

export default function PlatformAdminLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const { access_token } = await platformAdminApi.login(email, password);
      setAdminToken(access_token);
      router.push("/admin");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className={`${hankenGrotesk.className} flex min-h-screen items-center justify-center p-4`}
      style={{ background: "var(--semoule)" }}
    >
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-xl p-6 space-y-4 shadow-sm"
        style={{ background: "var(--semoule-raised)", border: "1px solid var(--line)" }}
      >
        <div className="flex flex-col items-center gap-3 pb-1">
          <TawlaMark size={44} />
          <h1 className="text-lg font-semibold" style={{ color: "var(--encre)" }}>
            Tableau de bord plateforme
          </h1>
          <p className="text-sm text-center" style={{ color: "var(--ink-soft)" }}>
            Vue d&apos;ensemble tous restaurants confondus — réservée à l&apos;opérateur de Tawla.
          </p>
        </div>

        {error && <div className="text-sm bg-red-50 text-red-700 border border-red-200 rounded-lg p-3">{error}</div>}

        <div className="space-y-1">
          <label htmlFor="email" className="text-sm font-medium" style={{ color: "var(--encre)" }}>
            E-mail
          </label>
          <input
            id="email"
            type="email"
            required
            autoFocus
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg px-3 py-1.5 outline-none focus:ring-2 focus:ring-[var(--harissa)]/40 focus:border-[var(--harissa)]"
            style={{ border: "1px solid var(--line)", background: "white" }}
          />
        </div>

        <div className="space-y-1">
          <label htmlFor="password" className="text-sm font-medium" style={{ color: "var(--encre)" }}>
            Mot de passe
          </label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg px-3 py-1.5 outline-none focus:ring-2 focus:ring-[var(--harissa)]/40 focus:border-[var(--harissa)]"
            style={{ border: "1px solid var(--line)", background: "white" }}
          />
        </div>

        <button
          type="submit"
          disabled={submitting}
          className={`${lalezar.className} w-full text-white text-base tracking-wide px-3 py-2 rounded-lg disabled:opacity-50 transition-colors`}
          style={{ background: "var(--harissa)" }}
        >
          {submitting ? "Connexion…" : "Se connecter"}
        </button>
      </form>
    </div>
  );
}
