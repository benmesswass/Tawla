"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { api, StaffRole } from "@/lib/api";
import { setToken } from "@/lib/auth";
import { toFrenchMessage } from "@/lib/errors";

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
    <div className="flex min-h-screen items-center justify-center p-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm border rounded-lg p-6 space-y-4">
        <h1 className="text-lg font-semibold">Connexion staff — Tawla</h1>

        {error && <div className="text-sm bg-red-50 text-red-700 border border-red-200 rounded-lg p-3">{error}</div>}

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
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full border rounded px-2 py-1.5"
          />
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full bg-neutral-900 text-white text-sm px-3 py-2 rounded-lg disabled:opacity-50"
        >
          {submitting ? "Connexion…" : "Se connecter"}
        </button>
      </form>
    </div>
  );
}
