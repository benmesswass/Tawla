"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { setToken } from "@/lib/auth";
import { toFrenchMessage } from "@/lib/errors";
import { hankenGrotesk, lalezar } from "@/lib/fonts";
import TawlaMark from "@/components/brand/TawlaMark";

export default function SignupPage() {
  const router = useRouter();
  const [restaurantName, setRestaurantName] = useState("");
  const [managerName, setManagerName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const { access_token } = await api.register({
        restaurant_name: restaurantName,
        manager_name: managerName,
        email,
        password,
      });
      setToken(access_token);
      router.push("/dashboard");
    } catch (err) {
      setError(toFrenchMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass =
    "w-full rounded-lg px-3 py-1.5 outline-none focus:ring-2 focus:ring-[var(--harissa)]/40 focus:border-[var(--harissa)]";
  const inputStyle = { border: "1px solid var(--line)", background: "white" };

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
        <div className="flex flex-col items-center gap-3 pb-1 text-center">
          <TawlaMark size={44} />
          <div>
            <h1 className="text-lg font-semibold" style={{ color: "var(--encre)" }}>
              Créer mon établissement
            </h1>
            <p className="text-sm mt-1" style={{ color: "var(--ink-soft)" }}>
              Onboardez votre restaurant ou café et devenez son premier compte manager.
            </p>
          </div>
        </div>

        {error && <div className="text-sm bg-red-50 text-red-700 border border-red-200 rounded-lg p-3">{error}</div>}

        <div className="space-y-1">
          <label htmlFor="restaurantName" className="text-sm font-medium" style={{ color: "var(--encre)" }}>
            Nom de l&apos;établissement
          </label>
          <input
            id="restaurantName"
            type="text"
            required
            value={restaurantName}
            onChange={(e) => setRestaurantName(e.target.value)}
            className={inputClass}
            style={inputStyle}
          />
        </div>

        <div className="space-y-1">
          <label htmlFor="managerName" className="text-sm font-medium" style={{ color: "var(--encre)" }}>
            Votre nom
          </label>
          <input
            id="managerName"
            type="text"
            required
            value={managerName}
            onChange={(e) => setManagerName(e.target.value)}
            className={inputClass}
            style={inputStyle}
          />
        </div>

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
            className={inputClass}
            style={inputStyle}
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
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={inputClass}
            style={inputStyle}
          />
          <p className="text-xs" style={{ color: "var(--ink-soft)" }}>
            8 caractères minimum.
          </p>
        </div>

        <button
          type="submit"
          disabled={submitting}
          className={`${lalezar.className} w-full text-white text-base tracking-wide px-3 py-2 rounded-lg disabled:opacity-50 transition-colors`}
          style={{ background: "var(--harissa)" }}
        >
          {submitting ? "Création…" : "Créer mon établissement"}
        </button>

        <p className="text-sm text-center" style={{ color: "var(--ink-soft)" }}>
          Déjà un compte ?{" "}
          <Link href="/login" className="underline" style={{ color: "var(--menthe)" }}>
            Se connecter
          </Link>
        </p>
      </form>
    </div>
  );
}
