"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, StaffRole } from "@/lib/api";
import { setToken } from "@/lib/auth";
import { toFrenchMessage } from "@/lib/errors";
import { hankenGrotesk, lalezar } from "@/lib/fonts";
import TawlaMark from "@/components/brand/TawlaMark";

const HOME_BY_ROLE: Record<StaffRole, string> = {
  waiter: "/staff",
  kitchen: "/kitchen",
  manager: "/dashboard",
};

export default function LoginPage() {
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
      const { access_token, staff } = await api.login(email, password);
      setToken(access_token);
      router.push(HOME_BY_ROLE[staff.role]);
    } catch (err) {
      setError(toFrenchMessage(err));
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
            Connexion staff
          </h1>
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

        <p className="text-sm text-center" style={{ color: "var(--ink-soft)" }}>
          Nouvel établissement ?{" "}
          <Link href="/signup" className="underline" style={{ color: "var(--menthe)" }}>
            Créer mon compte
          </Link>
        </p>
      </form>
    </div>
  );
}
