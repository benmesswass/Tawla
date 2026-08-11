"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { setToken } from "@/lib/auth";
import { toFrenchMessage } from "@/lib/errors";

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

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm border rounded-lg p-6 space-y-4">
        <div>
          <h1 className="text-lg font-semibold">Créer mon établissement — Tawla</h1>
          <p className="text-sm text-neutral-500 mt-1">
            Onboardez votre restaurant ou café et devenez son premier compte manager.
          </p>
        </div>

        {error && <div className="text-sm bg-red-50 text-red-700 border border-red-200 rounded-lg p-3">{error}</div>}

        <div className="space-y-1">
          <label htmlFor="restaurantName" className="text-sm font-medium">
            Nom de l&apos;établissement
          </label>
          <input
            id="restaurantName"
            type="text"
            required
            value={restaurantName}
            onChange={(e) => setRestaurantName(e.target.value)}
            className="w-full border rounded px-2 py-1.5"
          />
        </div>

        <div className="space-y-1">
          <label htmlFor="managerName" className="text-sm font-medium">
            Votre nom
          </label>
          <input
            id="managerName"
            type="text"
            required
            value={managerName}
            onChange={(e) => setManagerName(e.target.value)}
            className="w-full border rounded px-2 py-1.5"
          />
        </div>

        <div className="space-y-1">
          <label htmlFor="email" className="text-sm font-medium">
            E-mail
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full border rounded px-2 py-1.5"
          />
        </div>

        <div className="space-y-1">
          <label htmlFor="password" className="text-sm font-medium">
            Mot de passe
          </label>
          <input
            id="password"
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full border rounded px-2 py-1.5"
          />
          <p className="text-xs text-neutral-500">8 caractères minimum.</p>
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full bg-neutral-900 text-white text-sm px-3 py-2 rounded-lg disabled:opacity-50"
        >
          {submitting ? "Création…" : "Créer mon établissement"}
        </button>

        <p className="text-sm text-center text-neutral-500">
          Déjà un compte ?{" "}
          <Link href="/login" className="underline">
            Se connecter
          </Link>
        </p>
      </form>
    </div>
  );
}
