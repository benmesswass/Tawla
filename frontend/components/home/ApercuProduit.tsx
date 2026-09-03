"use client";

import { useState } from "react";
import { lalezar } from "@/lib/fonts";
import Card from "@/components/ui/Card";
import { formatMoney } from "@/lib/currency";
import { BENEFITS_PAR_ROLE } from "@/lib/offer";

/**
 * Vitrine à quatre écrans sur la home (Phase D2bis de ROADMAP_DESIGN.md,
 * comparatif BipOrder — mockup validé par Wassim avant ce code). Chaque rôle
 * reprend les vraies couleurs de son écran réel (client/manager en clair,
 * serveur/cuisine en sombre comme /staff et /kitchen) plutôt qu'une charte
 * inventée pour la démo. Données Dar Chaabane, restaurant de démo déjà utilisé
 * par la visite guidée et le seed (`backend/scripts/seed_demo.py`).
 *
 * Les 3 couples problème/solution (`BENEFITS_PAR_ROLE`, lib/offer.ts)
 * changent avec l'onglet actif au lieu de vivre dans un bloc générique
 * au-dessus (test demandé par Wassim, 2026-09-03) : chaque rôle défend son
 * propre triptyque plutôt qu'un compromis valable pour aucun des quatre.
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

      <div className="max-w-xl mx-auto mb-8 space-y-3">
        {BENEFITS_PAR_ROLE[role].map((b) => (
          <div key={b.probleme} className="text-sm leading-snug">
            <p className="text-[var(--ink-on-espresso-strong)]">{b.probleme}</p>
            <p className="text-[var(--semoule)] flex items-start gap-1.5 mt-0.5">
              <span className="text-[var(--menthe-on-espresso-text)] shrink-0" aria-hidden>
                ✓
              </span>
              <span>{b.solution}</span>
            </p>
          </div>
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

// Reprend le vrai en-tête du dashboard manager : mêmes onglets qu'
// EnteteManager.tsx (PAGES), mêmes deux chiffres de tête qu'
// RecetteDuJour.tsx — jamais "commandes"/"panier moyen"/"activité par
// serveur" présentés comme un seul coup d'œil : ces chiffres-là vivent sur
// les onglets Activité du jour / Preuve du pilote, pas sur l'écran d'accueil.
function EcranManager() {
  return (
    <div className="w-full max-w-[460px] rounded-xl overflow-hidden shadow-[0_30px_60px_-20px_rgba(0,0,0,.5)] bg-white">
      <ChromeBar />
      <div className="p-5">
        <div className="flex gap-3 text-xs font-medium border-b border-[var(--line)] pb-2.5 mb-4 overflow-x-auto">
          <span className="shrink-0 text-[var(--harissa)]">Carte</span>
          <span className="shrink-0 text-[var(--ink-faint)]">Activité du jour</span>
          <span className="shrink-0 text-[var(--ink-faint)]">Preuve du pilote</span>
          <span className="shrink-0 text-[var(--ink-faint)]">Rapport d&apos;équipe</span>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div className="col-span-2 rounded-lg bg-[var(--harissa)] text-white p-3">
            <p className="text-[11px] text-white/80">Ventes du jour</p>
            <p className="text-2xl font-semibold tabular-nums mt-0.5">{formatMoney(842)}</p>
          </div>
          <Card padding="sm" className="text-center flex flex-col justify-center">
            <p className="text-[10px] text-[var(--ink-soft)]">Attente moyenne</p>
            <p className="text-lg font-semibold tabular-nums text-[var(--encre)] mt-0.5">6 min</p>
          </Card>
        </div>
        <p className="text-[11px] text-[var(--ink-faint)] mt-3">
          Détail par serveur et comparaison avant/après sur les deux autres onglets.
        </p>
      </div>
    </div>
  );
}

// Le vrai écran serveur (app/staff/page.tsx) est sombre au niveau de la
// page, mais le panneau "Commandes à confirmer" lui-même est un carton clair
// posé dessus (bg-[var(--semoule-raised)]) — jamais des tickets teintés sur
// fond sombre. Le bouton reste harissa plein dans les deux états : seul son
// libellé change, "Prendre en charge" devient "Confirmer" une fois la même
// commande prise en charge par ce serveur.
function EcranServeur() {
  const commandes = [
    { table: "Table 4", numero: "#12", plats: "1× Couscous au poisson · 1× Thé à la menthe", action: "Prendre en charge" },
    { table: "Table 2", numero: "#11", plats: "2× Salade méchouia", action: "Confirmer" },
  ];
  return (
    <div className="w-full max-w-[460px] rounded-xl overflow-hidden shadow-[0_30px_60px_-20px_rgba(0,0,0,.6)] bg-[var(--espresso)]">
      <ChromeBar dark />
      <div className="p-5">
        <div className="rounded-2xl border border-[var(--line)] bg-[var(--semoule-raised)] overflow-hidden">
          <div className="px-3.5 py-2.5 border-b border-[var(--line)] flex items-center gap-2.5">
            <span className="w-[9px] h-5 rounded-[3px] shrink-0 bg-[var(--harissa)]" />
            <span className="text-[13px] font-bold text-[var(--encre)]">Commandes à confirmer</span>
            <span className="inline-flex items-center justify-center min-w-5 h-5 px-1.5 rounded-full text-[11px] font-bold text-[var(--semoule)] bg-[var(--harissa)]">
              {commandes.length}
            </span>
          </div>
          {commandes.map((o) => (
            <div key={o.numero} className="flex items-center gap-3 px-3.5 py-3 border-b border-[#efe6d2] last:border-b-0">
              <span className={`${lalezar.className} text-xl leading-none text-[var(--encre)]`}>{o.table}</span>
              <div className="min-w-0 flex-1">
                <p className="text-[12.5px] font-semibold text-[var(--encre)]">Commande {o.numero}</p>
                <p className="text-[11px] text-[var(--ink-soft)] truncate">{o.plats}</p>
              </div>
              <button
                type="button"
                className="shrink-0 rounded-lg px-3 py-2 text-xs font-bold bg-[var(--harissa)] text-[var(--semoule)]"
              >
                {o.action}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// La vraie cuisine (app/kitchen/page.tsx) n'a pas de colonnes par statut :
// une commande "prête" quitte l'écran (c'est au serveur de venir la
// chercher, plus à la cuisine). Une seule grille, l'urgence se lit à la
// couleur de la carte — neutre en attente, verte en préparation.
function EcranCuisine() {
  const commandes = [
    { table: "Table 4", depuis: "1 min", enCours: false, plats: ["1× Couscous au poisson"] },
    { table: "Table 2", depuis: "4 min", enCours: true, plats: ["2× Salade méchouia"] },
    { table: "Table 7", depuis: "2 min", enCours: false, plats: ["1× Baklawa"] },
  ];
  return (
    <div className="w-full max-w-[600px] rounded-xl overflow-hidden shadow-[0_30px_60px_-20px_rgba(0,0,0,.6)] bg-[var(--espresso)]">
      <ChromeBar dark />
      <div className="p-5">
        <p className="text-xs text-[var(--ink-on-espresso)] mb-3">Écran cuisine</p>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {commandes.map((c) => (
            <div
              key={c.table}
              className="rounded-[10px] overflow-hidden bg-[var(--espresso-card)]"
              style={{ border: `1px solid ${c.enCours ? "rgba(31,107,79,.55)" : "var(--line-on-espresso-strong)"}` }}
            >
              <div
                className="px-2.5 py-1.5 flex items-center justify-between"
                style={{ backgroundColor: c.enCours ? "rgba(31,107,79,.22)" : "var(--line-on-espresso)" }}
              >
                <span className="text-[13px] font-semibold text-[var(--semoule)]">{c.table}</span>
                <span className="text-[11px] font-bold tabular-nums text-[var(--semoule)]">{c.depuis}</span>
              </div>
              <div className="px-2.5 py-2 text-[11px] leading-snug text-[var(--semoule)] space-y-0.5">
                {c.plats.map((p) => (
                  <div key={p}>{p}</div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
