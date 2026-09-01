"use client";

import { Suspense, useEffect, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { api, type LaunchPromoStatus, type SubscriptionTier } from "@/lib/api";
import { trackEvent } from "@/lib/analytics";
import { setToken } from "@/lib/auth";
import { toFrenchMessage } from "@/lib/errors";
import { hankenGrotesk, lalezar } from "@/lib/fonts";
import TawlaMark from "@/components/brand/TawlaMark";
import { TIERS } from "@/lib/offer";
import { currentMarket } from "@/lib/market";

export default function SignupPage() {
  return (
    <Suspense fallback={null}>
      <SignupForm />
    </Suspense>
  );
}

function SignupForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // Palier choisi sur la carte tarif cliquée depuis l'accueil
  // (`/signup?tier=pro`) — Essentiel par défaut pour tout autre chemin
  // d'arrivée (mailto, /signup direct).
  const requestedTier = searchParams.get("tier");
  // `arrivedWithoutTierChoice` distingue « venu direct sans choisir » (on ne
  // sait rien de sa taille, on le renvoie voir les paliers) de « a cliqué
  // Essentiel en connaissance de cause » (rien à lui dire de plus) — le
  // palier par défaut (Essentiel) ne change pas, seule la question posée
  // change : ne jamais décider de son palier à sa place.
  const arrivedWithoutTierChoice = !TIERS.some((t) => t.id === requestedTier);
  const tier = TIERS.find((t) => t.id === requestedTier) ?? TIERS.find((t) => t.id === "essentiel")!;

  const [restaurantName, setRestaurantName] = useState("");
  const [managerName, setManagerName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmedFit, setConfirmedFit] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  // Offre de lancement (2026-08-21, réglages configurables — voir
  // dashboard plateforme) : `null` tant que la disponibilité n'a pas été
  // vérifiée — on n'affiche jamais la bannière par optimisme avant de
  // savoir, elle apparaîtrait puis disparaîtrait au premier rendu.
  const [promo, setPromo] = useState<LaunchPromoStatus | null>(null);

  useEffect(() => {
    api
      .getLaunchPromoStatus()
      .then(setPromo)
      .catch(() => setPromo(null));
  }, []);

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
        tier: tier.id as SubscriptionTier,
      });
      trackEvent("signup_submitted", { tier: tier.id });
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
            <p className="text-xs mt-2" data-visite="signup-palier" style={{ color: "var(--ink-soft)" }}>
              Palier choisi : <span style={{ color: "var(--encre)" }}>{tier.name}</span> — {tier.priceDT}{" "}
              {currentMarket.currency.symbol} / mois
            </p>
            {arrivedWithoutTierChoice && (
              <p className="text-xs mt-1" style={{ color: "var(--harissa)" }}>
                Arrivé·e sans avoir choisi de palier ? Essentiel est pensé pour un petit café, une seule
                salle.{" "}
                <Link href="/#tarifs" className="underline">
                  Voir les trois paliers
                </Link>
                .
              </p>
            )}
          </div>
        </div>

        {promo?.available && (
          <div
            className="rounded-lg p-3 text-center"
            style={{ background: "var(--semoule)", border: "1px solid var(--harissa)" }}
          >
            <p className={`${lalezar.className} text-sm tracking-wide`} style={{ color: "var(--harissa)" }}>
              Offre de lancement — les {promo.max_grants} premières inscriptions
            </p>
            <p className="mt-1">
              <span className="text-sm line-through" style={{ color: "var(--ink-soft)" }}>
                {tier.priceDT} {currentMarket.currency.symbol}
              </span>{" "}
              <span className="text-lg font-semibold" style={{ color: "var(--encre)" }}>
                {promo.discount_percent >= 100
                  ? "Gratuit"
                  : `${Math.round((tier.priceDT * (100 - promo.discount_percent)) / 100)} ${currentMarket.currency.symbol}`}
              </span>
              <span className="text-sm" style={{ color: "var(--ink-soft)" }}> le premier mois</span>
            </p>
          </div>
        )}

        {error && <div className="text-sm bg-red-50 text-red-700 border border-red-200 rounded-lg p-3">{error}</div>}

        <div className="space-y-1" data-visite="signup-etablissement">
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

        {/* E-mail et mot de passe forment un seul bloc pour la visite guidée :
            c'est le compte manager qu'on présente, pas deux champs séparés. */}
        <div className="space-y-4" data-visite="signup-identifiants">
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
        </div>

        {/* Auto-qualification, jamais vérifiée côté serveur : Tawla se
            vend en personne à une cible étroite (CLAUDE.md, ROADMAP.md), et
            le self-service ne doit pas devenir la porte d'entrée des petits
            établissements que la stratégie exclut. Un simple frein, pas un
            blocage — le patron reste seul juge de sa situation. */}
        <label className="flex items-start gap-2 text-xs" style={{ color: "var(--ink-soft)" }}>
          <input
            type="checkbox"
            required
            checked={confirmedFit}
            onChange={(e) => setConfirmedFit(e.target.checked)}
            className="mt-0.5"
          />
          <span>
            Je confirme que mon établissement a du wifi ou du réseau à toutes les tables.
          </span>
        </label>

        <button
          type="submit"
          data-visite="signup-valider"
          disabled={submitting || !confirmedFit}
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
