"use client";

import { useState } from "react";
import { lalezar } from "@/lib/fonts";
import Card from "@/components/ui/Card";
import { formatMoney } from "@/lib/currency";

/**
 * Vitrine à quatre écrans sur la home (Phase D2bis de ROADMAP_DESIGN.md,
 * comparatif BipOrder — mockup validé par Wassim avant ce code). Chaque rôle
 * reprend les vraies couleurs de son écran réel (client/manager en clair,
 * serveur/cuisine en sombre comme /staff et /kitchen) plutôt qu'une charte
 * inventée pour la démo. Données Dar Chaabane, restaurant de démo déjà utilisé
 * par la visite guidée et le seed (`backend/scripts/seed_demo.py`).
 */

type Role = "client" | "manager" | "serveur" | "cuisine";

const ROLES: { id: Role; label: string }[] = [
  { id: "client", label: "Client" },
  { id: "manager", label: "Manager" },
  { id: "serveur", label: "Serveur" },
  { id: "cuisine", label: "Cuisine" },
];

const CARTE_DEMO = [
  {
    nom: "Entrées",
    plats: [
      { nom: "Salade méchouia", prix: 6 },
      { nom: "Brik à l'œuf", prix: 5 },
    ],
  },
  {
    nom: "Plats",
    plats: [
      { nom: "Couscous au poisson", prix: 22 },
      { nom: "Kefta grillée", prix: 18 },
    ],
  },
  {
    nom: "Desserts",
    plats: [{ nom: "Baklawa", prix: 5 }],
  },
];

export default function ApercuProduit() {
  const [role, setRole] = useState<Role>("client");

  return (
    <div>
      <div role="tablist" aria-label="Voir l'écran de chaque rôle" className="flex flex-wrap justify-center gap-2 mb-8">
        {ROLES.map((r) => (
          <button
            key={r.id}
            type="button"
            role="tab"
            aria-selected={role === r.id}
            onClick={() => setRole(r.id)}
            className={`rounded-full px-4 py-2 text-sm font-medium transition-colors duration-200 ${
              role === r.id
                ? "bg-[var(--laiton)] text-[var(--espresso)]"
                : "bg-[var(--line-on-espresso)] text-[var(--ink-on-espresso-strong)] hover:bg-[var(--line-on-espresso-strong)]"
            }`}
          >
            {r.label}
          </button>
        ))}
      </div>

      <div className="flex justify-center">
        {role === "client" && <EcranClient />}
        {role === "manager" && <EcranManager />}
        {role === "serveur" && <EcranServeur />}
        {role === "cuisine" && <EcranCuisine />}
      </div>
    </div>
  );
}

function ChromeBar({ dark = false }: { dark?: boolean }) {
  return (
    <div className={`flex items-center gap-1.5 px-3 py-2 ${dark ? "bg-[#180f08]" : "bg-[var(--semoule-raised)] border-b border-[var(--line)]"}`}>
      <span className="w-2.5 h-2.5 rounded-full bg-[var(--harissa)]" />
      <span className="w-2.5 h-2.5 rounded-full bg-[var(--laiton)]" />
      <span className="w-2.5 h-2.5 rounded-full bg-[var(--menthe)]" />
    </div>
  );
}

// Bezel + carton harissa comme le vrai en-tête du menu client
// (app/menu/[qrToken]/page.tsx) — nom du restaurant en lalezar, table en
// dessous, plutôt qu'un titre générique inventé pour la démo.
function EcranClient() {
  const [categorie, setCategorie] = useState(0);
  return (
    <div className="w-[240px] rounded-[2rem] bg-[#180f08] p-2 shadow-[0_30px_60px_-20px_rgba(0,0,0,.6)]">
      <div className="rounded-[1.5rem] bg-[var(--semoule)] overflow-hidden">
        <div className="bg-[var(--harissa)] text-[var(--semoule)] px-4 pt-3 pb-3">
          <h3 className={`${lalezar.className} text-xl leading-none text-balance`}>Dar Chaabane</h3>
          <p className="text-[11px] font-medium text-[rgba(246,239,221,.82)] mt-1">Table 7</p>
        </div>
        <div className="flex gap-1.5 px-3 py-2.5 overflow-x-auto border-b border-[var(--line)]">
          {CARTE_DEMO.map((cat, i) => (
            <button
              key={cat.nom}
              type="button"
              onClick={() => setCategorie(i)}
              className={`shrink-0 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors duration-200 ${
                i === categorie
                  ? "bg-[var(--harissa)] text-[var(--semoule)] border-[var(--harissa)]"
                  : "border-[var(--line-strong)] text-[var(--ink-soft)]"
              }`}
            >
              {cat.nom}
            </button>
          ))}
        </div>
        <div className="px-4 py-3 space-y-3">
          {CARTE_DEMO[categorie].plats.map((plat) => (
            <div key={plat.nom} className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-medium text-[var(--encre)] truncate">{plat.nom}</p>
                <p className="text-xs text-[var(--ink-soft)]">{formatMoney(plat.prix)}</p>
              </div>
              <span
                aria-hidden
                className="shrink-0 flex items-center justify-center w-7 h-7 rounded-full bg-[var(--harissa)] text-white text-base leading-none"
              >
                +
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function EcranManager() {
  return (
    <div className="w-full max-w-[460px] rounded-xl overflow-hidden shadow-[0_30px_60px_-20px_rgba(0,0,0,.5)] bg-white">
      <ChromeBar />
      <div className="p-5">
        <p className="text-xs text-[var(--ink-soft)] mb-3">Aujourd&apos;hui · Dar Chaabane</p>
        <div className="grid grid-cols-3 gap-3 mb-5">
          <Card padding="sm" className="text-center">
            <p className="text-lg font-semibold tabular-nums text-[var(--encre)]">47</p>
            <p className="text-[10px] text-[var(--ink-soft)]">Commandes</p>
          </Card>
          <Card padding="sm" className="text-center">
            <p className="text-lg font-semibold tabular-nums text-[var(--encre)]">{formatMoney(28)}</p>
            <p className="text-[10px] text-[var(--ink-soft)]">Panier moyen</p>
          </Card>
          <Card padding="sm" className="text-center">
            <p className="text-lg font-semibold tabular-nums text-[var(--encre)]">11 min</p>
            <p className="text-[10px] text-[var(--ink-soft)]">Temps cuisine</p>
          </Card>
        </div>
        <p className="text-xs font-semibold text-[var(--encre)] mb-2 uppercase tracking-wide">Activité par serveur</p>
        <div className="space-y-2">
          {[
            { nom: "Sami", commandes: 18 },
            { nom: "Amine", commandes: 14 },
          ].map((s) => (
            <div
              key={s.nom}
              className="flex items-center justify-between text-sm rounded-md border border-[var(--line)] px-3 py-2"
            >
              <span className="text-[var(--encre)]">{s.nom}</span>
              <span className="tabular-nums text-[var(--ink-soft)]">{s.commandes} commandes</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function EcranServeur() {
  return (
    <div className="w-full max-w-[460px] rounded-xl overflow-hidden shadow-[0_30px_60px_-20px_rgba(0,0,0,.6)] bg-[var(--espresso)]">
      <ChromeBar dark />
      <div className="p-5 space-y-3">
        <p className="text-xs text-[var(--ink-on-espresso)]">Écran serveur</p>
        <Card dark tone="warning" padding="sm">
          <p className="text-sm font-semibold text-[var(--semoule)] mb-1.5">Table 4 · Commande #12</p>
          <p className="text-xs text-[var(--ink-on-espresso-strong)] mb-3">1× Couscous au poisson · 1× Thé à la menthe</p>
          <button
            type="button"
            className="text-xs font-medium rounded-md border border-[var(--laiton-on-espresso-border)] text-[var(--laiton-on-espresso-text)] px-3 py-1.5"
          >
            Prendre en charge
          </button>
        </Card>
        <Card dark tone="danger" padding="sm">
          <p className="text-sm font-semibold text-[var(--semoule)] mb-1.5">Table 2 · Commande #11</p>
          <p className="text-xs text-[var(--ink-on-espresso-strong)] mb-3">2× Salade méchouia</p>
          <button type="button" className="text-xs font-medium rounded-md bg-[var(--harissa)] text-white px-3 py-1.5">
            Confirmer
          </button>
        </Card>
      </div>
    </div>
  );
}

function EcranCuisine() {
  const colonnes = [
    { titre: "Confirmée", tickets: ["Table 4 · Couscous au poisson"] },
    { titre: "En préparation", tickets: ["Table 2 · Salade méchouia", "Table 7 · Baklawa"] },
    { titre: "Prête", tickets: ["Table 1 · Thé à la menthe"] },
  ];
  return (
    <div className="w-full max-w-[600px] rounded-xl overflow-hidden shadow-[0_30px_60px_-20px_rgba(0,0,0,.6)] bg-[var(--espresso)]">
      <ChromeBar dark />
      <div className="p-5">
        <p className="text-xs text-[var(--ink-on-espresso)] mb-3">Écran cuisine</p>
        <div className="grid grid-cols-3 gap-3">
          {colonnes.map((col) => (
            <div key={col.titre}>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--ink-on-espresso-strong)] mb-2">
                {col.titre}
              </p>
              <div className="space-y-2">
                {col.tickets.map((t) => (
                  <Card key={t} dark padding="sm" className="text-[11px] leading-snug text-[var(--semoule)]">
                    {t}
                  </Card>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
