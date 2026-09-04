"use client";

import { useState } from "react";
import { lalezar } from "@/lib/fonts";
import Card from "@/components/ui/Card";
import { BellIcon } from "@/components/icons";
import { formatMoney } from "@/lib/currency";
import { currentMarket } from "@/lib/market";
import { BENEFITS_PAR_ROLE } from "@/lib/offer";
import EcranCarrousel, { type EtapeCarrousel } from "@/components/home/EcranCarrousel";

/**
 * Vitrine à quatre écrans sur la home (Phase D2bis de ROADMAP_DESIGN.md,
 * comparatif BipOrder — mockup validé par Wassim avant ce code). Chaque rôle
 * reprend les vraies couleurs, le vrai vocabulaire et les vrais libellés de
 * son écran réel plutôt qu'une charte inventée pour la démo — voir les
 * commentaires au fil du fichier pour la source de chaque fragment copié.
 *
 * Client, Manager et Serveur sont un CARROUSEL de plusieurs écrans distincts
 * (EcranCarrousel) — retour de Wassim du 2026-09-03 : « je veux 3 iPhones
 * distincts côte à côte », pas un seul écran dont le contenu change. La
 * Cuisine reste un poste fixe unique, sans carrousel (son vrai fonctionnement
 * à onglets tient déjà sur un seul écran).
 *
 * Données Dar Chaabane (Tunisie) et Le Petit Bouchon (France) — un restaurant
 * de démo par marché, jamais le même sur les deux (même raison que
 * culturalFacts.ts) : le marché tunisien reste Dar Chaabane, déjà utilisé par
 * la visite guidée et le seed (`backend/scripts/seed_demo.py`) ; le marché
 * français ne réutilise ni ce nom, ni ces plats, ni ces prénoms d'équipe,
 * spécifiquement tunisiens et hors de propos devant un prospect français.
 * Prix identiques d'un marché à l'autre (seule la devise change, via
 * `formatMoney`) — ce mockup illustre l'écran, pas une politique tarifaire.
 *
 * Les 3 couples problème/solution (`BENEFITS_PAR_ROLE`, lib/offer.ts)
 * changent avec l'onglet actif : chaque rôle défend son propre triptyque.
 * Section hôte volontairement SANS fond sombre : un essai avait empilé cette
 * section en --espresso ET les écrans serveur/cuisine (déjà sombres pour
 * coller à /staff et /kitchen) — deux grands cadres bruns l'un dans l'autre,
 * jugé trop sombre et encombré (Wassim, 2026-09-03). Un seul cadre sombre
 * par écran suffit ; le reste de la page reste clair.
 */

type Role = "client" | "manager" | "serveur" | "cuisine";

const ROLES: { id: Role; label: string }[] = [
  { id: "client", label: "Client" },
  { id: "manager", label: "Manager" },
  { id: "serveur", label: "Serveur" },
  { id: "cuisine", label: "Cuisine" },
];

const DEMO_TN = {
  restaurant: "Dar Chaabane",
  table: "Table 7",
  carte: [
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
  ],
  panier: [
    { nom: "Salade méchouia", prix: 6 },
    { nom: "Couscous au poisson", prix: 22 },
    { nom: "Baklawa", prix: 5 },
  ],
  commandeNumero: "48",
  appelTable: "Table 2",
  pretTable: "Table 4",
  pretCommandeNumero: "47",
  encaissementTable: "Table 4",
  encaissementCommandeNumero: "47",
  encaissementMethode: "Espèces" as const,
  equipe: [
    { nom: "Sami", commandes: 18, pourboires: 142 },
    { nom: "Amine", commandes: 14, pourboires: 98 },
  ],
};

const DEMO_FR = {
  restaurant: "Le Petit Bouchon",
  table: "Table 7",
  carte: [
    {
      nom: "Entrées",
      plats: [
        { nom: "Soupe à l'oignon", prix: 6 },
        { nom: "Œuf mimosa", prix: 5 },
      ],
    },
    {
      nom: "Plats",
      plats: [
        { nom: "Bœuf bourguignon", prix: 22 },
        { nom: "Steak-frites", prix: 18 },
      ],
    },
    {
      nom: "Desserts",
      plats: [{ nom: "Crème brûlée", prix: 5 }],
    },
  ],
  panier: [
    { nom: "Soupe à l'oignon", prix: 6 },
    { nom: "Bœuf bourguignon", prix: 22 },
    { nom: "Crème brûlée", prix: 5 },
  ],
  commandeNumero: "48",
  appelTable: "Table 2",
  pretTable: "Table 4",
  pretCommandeNumero: "47",
  encaissementTable: "Table 4",
  encaissementCommandeNumero: "47",
  encaissementMethode: "Carte" as const,
  equipe: [
    { nom: "Julien", commandes: 18, pourboires: 142 },
    { nom: "Camille", commandes: 14, pourboires: 98 },
  ],
};

const DEMO = currentMarket.code === "fr" ? DEMO_FR : DEMO_TN;

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
                : "bg-[var(--creme)] text-[var(--ink-soft)] hover:bg-[var(--line)]"
            }`}
          >
            {r.label}
          </button>
        ))}
      </div>

      <div className="max-w-xl mx-auto mb-10 space-y-3">
        {BENEFITS_PAR_ROLE[role].map((b, i) => {
          const harissa = i % 2 === 0;
          return (
            <div
              key={b.probleme}
              className={`probleme-apparait flex flex-col gap-3 rounded-lg bg-white p-5 border-l-4 ${
                harissa ? "border-[var(--harissa)]" : "border-[var(--laiton)]"
              }`}
              style={{ animationDelay: `${i * 90}ms` }}
            >
              <p className="flex gap-1.5 items-start text-sm text-[var(--ink-soft)]">
                <span className="text-[var(--ink-faint)] shrink-0" aria-hidden>
                  ✗
                </span>
                <span>{b.probleme}</span>
              </p>
              <div
                className={`flex gap-2.5 rounded-md border p-3 text-sm ${
                  harissa
                    ? "bg-[var(--tuile-harissa-fond)] border-[var(--tuile-harissa-bord)]"
                    : "bg-[var(--tuile-laiton-fond)] border-[var(--tuile-laiton-bord)]"
                }`}
              >
                <span className={harissa ? "text-[var(--harissa)]" : "text-[var(--laiton)]"} aria-hidden>
                  ✓
                </span>
                <span className="text-[var(--encre)]">{b.solution}</span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex justify-center">
        {role === "client" && <CarrouselClient />}
        {role === "manager" && <CarrouselManager />}
        {role === "serveur" && <CarrouselServeur />}
        {role === "cuisine" && <EcranCuisine />}
      </div>
    </div>
  );
}

function EnTete({ label, titre }: { label: string; titre?: string }) {
  return (
    <div className="px-4 pt-3.5 pb-2.5">
      <p className="text-[9.5px] font-bold uppercase tracking-wide text-[var(--ink-faint)]">{label}</p>
      {titre && <h3 className="text-lg mt-0.5 text-[var(--encre)]">{titre}</h3>}
    </div>
  );
}

/* ---------------------------- CLIENT ---------------------------- */
// Parcours vérifié contre app/menu/[qrToken]/page.tsx : il n'existe pas de
// pages "panier"/"suivi"/"paiement" séparées dans le vrai produit — tout vit
// sur une seule page qui change d'état. Les 4 étapes ci-dessous sont une
// simplification de présentation assumée, mais chaque libellé (Valider la
// commande, Commande envoyée 🎉, la timeline à 5 étapes, Appeler le serveur,
// Sans/5%/10%, les 3 boutons de paiement) est copié du vrai code, jamais
// inventé.
function CarrouselClient() {
  const etapes: EtapeCarrousel[] = [
    { id: "menu", label: "Menu", contenu: <EtapeMenu /> },
    { id: "panier", label: "Panier", contenu: <EtapePanier /> },
    { id: "suivi", label: "Suivi", contenu: <EtapeSuivi /> },
    { id: "paiement", label: "Paiement", contenu: <EtapePaiement /> },
  ];
  return <EcranCarrousel device="phone" etapes={etapes} />;
}

function EtapeMenu() {
  const [categorie, setCategorie] = useState(0);
  return (
    <div className="h-full flex flex-col">
      <div className="bg-[var(--harissa)] text-[var(--semoule)] px-4 pt-3.5 pb-3">
        <h3 className={`${lalezar.className} text-xl leading-none text-balance`}>{DEMO.restaurant}</h3>
        <p className="text-[11px] font-medium text-[rgba(246,239,221,.82)] mt-1">{DEMO.table}</p>
      </div>
      <div className="flex gap-1.5 px-3 py-2.5 overflow-x-auto border-b border-[var(--line)]">
        {DEMO.carte.map((cat, i) => (
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
        {DEMO.carte[categorie].plats.map((plat) => (
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
  );
}

function EtapePanier() {
  const total = DEMO.panier.reduce((sum, l) => sum + l.prix, 0);
  return (
    <div className="h-full flex flex-col">
      <EnTete label={DEMO.table} titre="Votre panier" />
      <div className="px-4 space-y-3 flex-1">
        {DEMO.panier.map((ligne) => (
          <div key={ligne.nom} className="flex items-center justify-between gap-2">
            <div className="min-w-0">
              <p className="text-sm font-medium text-[var(--encre)] truncate">{ligne.nom}</p>
              <p className="text-xs text-[var(--ink-soft)]">{formatMoney(ligne.prix)}</p>
            </div>
            <div className="shrink-0 flex items-center gap-2">
              <span className="w-6 h-6 rounded-full border border-[var(--laiton)] text-[var(--laiton)] text-sm font-bold flex items-center justify-center">
                −
              </span>
              <span className="text-sm font-bold text-[var(--encre)] w-3 text-center">1</span>
              <span className="w-6 h-6 rounded-full border border-[var(--laiton)] text-[var(--laiton)] text-sm font-bold flex items-center justify-center">
                +
              </span>
            </div>
          </div>
        ))}
      </div>
      <div className="bg-[var(--encre)] text-[var(--semoule)] px-4 py-3 flex items-center justify-between gap-3">
        <div>
          <p className="text-[9px] font-bold uppercase tracking-wide text-[rgba(243,239,221,.65)]">
            {DEMO.panier.length} articles
          </p>
          <p className="text-[15px] font-bold tabular-nums">{formatMoney(total)}</p>
        </div>
        <span className="rounded-full bg-[var(--harissa)] text-[var(--semoule)] text-[11px] font-bold px-3.5 py-2 whitespace-nowrap">
          Valider la commande
        </span>
      </div>
    </div>
  );
}

// Timeline copiée de fr.ts (orderStatusLabels) : Commande reçue, Confirmée
// par le serveur, En cuisine, Prête à servir, Servie.
function EtapeSuivi() {
  const etapes = [
    { texte: "Commande reçue", etat: "fait" as const },
    { texte: "Confirmée par le serveur", etat: "fait" as const },
    { texte: "En cuisine", etat: "actif" as const },
    { texte: "Prête à servir", etat: "reste" as const },
    { texte: "Servie", etat: "reste" as const },
  ];
  return (
    <div className="h-full px-4 pt-5 pb-4 flex flex-col">
      <p className="text-base font-bold text-[var(--encre)]">Commande envoyée 🎉</p>
      <p className="text-[11px] text-[var(--ink-faint)] mb-4">
        {DEMO.table} — commande #{DEMO.commandeNumero}
      </p>
      <ol className="space-y-2 flex-1">
        {etapes.map((e) => (
          <li key={e.texte} className="flex items-center gap-2.5 text-xs">
            <span
              className={`shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                e.etat === "fait"
                  ? "bg-[var(--menthe)] text-white"
                  : e.etat === "actif"
                    ? "bg-[var(--harissa)] text-white"
                    : "bg-[var(--semoule-raised)] border border-[var(--line)] text-[var(--ink-faint)]"
              }`}
            >
              {e.etat === "fait" ? "✓" : ""}
            </span>
            <span
              className={
                e.etat === "reste" ? "text-[var(--ink-faint)]" : "text-[var(--encre)] font-semibold"
              }
            >
              {e.texte}
            </span>
          </li>
        ))}
      </ol>
      <span className="inline-flex items-center justify-center gap-1.5 text-xs font-semibold border border-[var(--line)] bg-white text-[var(--encre)] rounded-full px-3 py-2.5 self-start">
        <BellIcon className="w-3.5 h-3.5 shrink-0" />
        Appeler le serveur
      </span>
    </div>
  );
}

// Pourboire et 3 boutons copiés de app/menu/[qrToken]/page.tsx (tipNone,
// payByCard, payByCardTerminal, payByCash) et du taux réel [0, 0.05, 0.1].
function EtapePaiement() {
  const total = DEMO.panier.reduce((sum, l) => sum + l.prix, 0);
  return (
    <div className="h-full px-4 pt-5 pb-4 flex flex-col">
      <p className="text-base font-bold text-[var(--encre)]">Paiement</p>
      <p className="text-[11px] text-[var(--ink-faint)] mb-4">Total à régler : {formatMoney(total)}</p>
      <p className="text-[10.5px] text-[var(--ink-soft)] mb-1.5">Pourboire (facultatif, pour un paiement par carte)</p>
      <div className="flex gap-1.5 mb-4">
        {["Sans", "5%", "10%"].map((label, i) => (
          <span
            key={label}
            className={`flex-1 text-center rounded-lg border py-1.5 text-xs font-semibold ${
              i === 1
                ? "bg-[var(--laiton)] border-[var(--laiton)] text-[var(--encre)]"
                : "border-[var(--line)] text-[var(--encre)]"
            }`}
          >
            {label}
          </span>
        ))}
      </div>
      <div className="mt-auto space-y-1.5">
        <span className="block text-center rounded-lg bg-[var(--harissa)] text-[var(--semoule)] py-2.5 text-xs font-bold">
          Payer en ligne par carte
        </span>
        <span className="block text-center rounded-lg border border-[var(--line)] text-[var(--encre)] py-2.5 text-xs font-semibold">
          Carte à table (terminal serveur)
        </span>
        <span className="block text-center rounded-lg border border-[var(--line)] text-[var(--encre)] py-2.5 text-xs font-semibold">
          Espèces (le serveur passe encaisser)
        </span>
      </div>
    </div>
  );
}

/* ---------------------------- MANAGER ---------------------------- */
// Vérifié contre les 4 vraies pages (app/dashboard/{page,stats,preuve,
// equipe}.tsx) : Carte reprend RecetteDuJour (Ventes du jour + attente
// moyenne) ; Activité reprend les statuts réels d'OrderStatus regroupés en 3
// paliers ; Preuve reprend les 3 métriques réelles de dashboard/preuve
// (Commandes annulées, Délai commande → cuisine, Panier moyen) ; Équipe
// reprend la colonne "Panier moyen"/pourboires de dashboard/equipe.
function CarrouselManager() {
  const etapes: EtapeCarrousel[] = [
    { id: "carte", label: "Carte", contenu: <EtapeManagerCarte /> },
    { id: "activite", label: "Activité", contenu: <EtapeManagerActivite /> },
    { id: "preuve", label: "Preuve", contenu: <EtapeManagerPreuve /> },
    { id: "equipe", label: "Équipe", contenu: <EtapeManagerEquipe /> },
  ];
  return <EcranCarrousel device="tablet" etapes={etapes} />;
}

function EtapeManagerCarte() {
  return (
    <div className="p-4">
      <EnTeteTablette>Aujourd&apos;hui · {DEMO.restaurant}</EnTeteTablette>
      <div className="grid grid-cols-2 gap-2.5 mt-2">
        <div className="rounded-lg bg-[var(--harissa)] text-white p-2.5">
          <p className="text-[10px] text-white/80">Ventes du jour</p>
          <p className="text-lg font-semibold tabular-nums mt-0.5">{formatMoney(842)}</p>
        </div>
        <Card padding="sm" className="text-center flex flex-col justify-center">
          <p className="text-[9px] text-[var(--ink-soft)]">Attente moyenne</p>
          <p className="text-base font-semibold tabular-nums text-[var(--encre)] mt-0.5">6 min</p>
        </Card>
      </div>
    </div>
  );
}

function EtapeManagerActivite() {
  const paliers = [
    { libelle: "En attente de confirmation", valeur: 2, couleur: "var(--harissa)" },
    { libelle: "En cuisine", valeur: 3, couleur: "var(--laiton)" },
    { libelle: "Prêtes à servir", valeur: 1, couleur: "var(--menthe)" },
  ];
  return (
    <div className="p-4">
      <EnTeteTablette>Activité du jour</EnTeteTablette>
      <p className="text-[10px] font-bold text-[var(--ink-soft)] mt-2 mb-1.5">Commandes en cours · 6</p>
      <div className="space-y-1">
        {paliers.map((p) => (
          <div
            key={p.libelle}
            className="flex items-center justify-between gap-2 text-[11px] text-[var(--encre)] py-1 border-b border-[var(--line)] last:border-b-0"
          >
            <span className="min-w-0">{p.libelle}</span>
            <span
              className="shrink-0 min-w-5 h-5 px-1.5 rounded-full text-[10px] font-bold text-[var(--semoule)] flex items-center justify-center"
              style={{ backgroundColor: p.couleur }}
            >
              {p.valeur}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function EtapeManagerPreuve() {
  const metriques = [
    { libelle: "Commandes annulées", valeur: "1", delta: "▼ 2", positif: true },
    { libelle: "Délai commande → cuisine", valeur: "4 min", delta: "▼ 1 min", positif: true },
    { libelle: "Panier moyen", valeur: formatMoney(28), delta: "▲ " + formatMoney(2), positif: true },
  ];
  return (
    <div className="p-4">
      <EnTeteTablette>Preuve du pilote</EnTeteTablette>
      <div className="space-y-1.5 mt-2">
        {metriques.map((m) => (
          <div key={m.libelle} className="rounded-lg border border-[var(--line)] bg-[var(--semoule-raised)] px-2.5 py-1.5">
            <p className="text-[9.5px] text-[var(--ink-soft)]">{m.libelle}</p>
            <div className="flex items-baseline gap-1.5 mt-0.5">
              <span className="text-[12.5px] font-bold tabular-nums text-[var(--encre)]">{m.valeur}</span>
              <span className="text-[9.5px] font-bold text-[var(--menthe)]">{m.delta}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function EtapeManagerEquipe() {
  return (
    <div className="p-4">
      <EnTeteTablette>Rapport d&apos;équipe</EnTeteTablette>
      <div className="space-y-1.5 mt-2">
        {DEMO.equipe.map((membre) => (
          <div key={membre.nom} className="rounded-lg border border-[var(--line)] bg-[var(--semoule-raised)] px-2.5 py-1.5">
            <p className="text-[11px] font-bold text-[var(--encre)]">{membre.nom}</p>
            <p className="text-[9.5px] text-[var(--ink-soft)] mt-0.5">
              {membre.commandes} commandes · {formatMoney(membre.pourboires)} de pourboires
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function EnTeteTablette({ children }: { children: React.ReactNode }) {
  return <p className="text-[10px] font-bold uppercase tracking-wide text-[var(--ink-faint)]">{children}</p>;
}

/* ---------------------------- SERVEUR ---------------------------- */
// Les 4 panneaux réels de app/staff/page.tsx (EntetePanneau) : "Commandes à
// confirmer" (harissa), "Appels serveur" (harissa, "Vous appelle"/"Je
// prends"), "Prêtes à servir" (menthe, "Servie"), "Demandes d'encaissement"
// (laiton, bouton laiton/espresso) — 4 des 5 panneaux réels (« Demandes de
// modification » omis, narrative déjà assez longue à 4 écrans).
function CarrouselServeur() {
  const etapes: EtapeCarrousel[] = [
    { id: "confirmer", label: "Confirmer", contenu: <EtapeServeurConfirmer /> },
    { id: "appels", label: "Appels", contenu: <EtapeServeurAppels /> },
    { id: "prete", label: "Prête", contenu: <EtapeServeurPrete /> },
    { id: "encaisser", label: "Encaisser", contenu: <EtapeServeurEncaisser /> },
  ];
  return <EcranCarrousel device="phone" etapes={etapes} />;
}

function PanneauServeur({
  titre,
  couleur,
  children,
}: {
  titre: string;
  couleur: string;
  children: React.ReactNode;
}) {
  return (
    <div className="h-full flex flex-col">
      <EnTete label="Écran serveur" />
      <div className="mx-3 mb-3 rounded-2xl border border-[var(--line)] bg-[var(--semoule-raised)] overflow-hidden flex-1">
        <div
          className="px-3 py-2 flex items-center gap-2 text-[12px] font-bold text-white"
          style={{ backgroundColor: couleur }}
        >
          {titre}
        </div>
        {children}
      </div>
    </div>
  );
}

function EtapeServeurConfirmer() {
  return (
    <PanneauServeur titre="Commandes à confirmer" couleur="var(--harissa)">
      <div className="px-3 py-2.5">
        <div className="flex items-center gap-2.5">
          <span className={`${lalezar.className} text-xl leading-none text-[var(--encre)]`}>{DEMO.appelTable}</span>
          <div className="min-w-0 flex-1">
            <p className="text-[12px] font-semibold text-[var(--encre)]">Commande #46</p>
            <p className="text-[10.5px] text-[var(--ink-soft)] truncate">2× {DEMO.panier[0].nom}</p>
          </div>
          <span className="shrink-0 rounded-lg px-2.5 py-1.5 text-[11px] font-bold bg-[var(--harissa)] text-[var(--semoule)]">
            Confirmer
          </span>
        </div>
      </div>
    </PanneauServeur>
  );
}

function EtapeServeurAppels() {
  return (
    <PanneauServeur titre="Appels serveur" couleur="var(--harissa)">
      <div className="px-3 py-2.5" style={{ backgroundColor: "rgba(214,64,30,.06)" }}>
        <div className="flex items-center gap-2.5">
          <span className={`${lalezar.className} text-xl leading-none text-[var(--encre)]`}>{DEMO.appelTable}</span>
          <div className="min-w-0 flex-1 text-[12px] font-semibold text-[var(--encre)] inline-flex items-center gap-1.5">
            <BellIcon className="w-3.5 h-3.5 shrink-0 text-[var(--harissa)]" />
            Vous appelle
          </div>
          <span className="shrink-0 rounded-lg px-2.5 py-1.5 text-[11px] font-bold bg-[var(--harissa)] text-[var(--semoule)]">
            Je prends
          </span>
        </div>
      </div>
    </PanneauServeur>
  );
}

function EtapeServeurPrete() {
  return (
    <PanneauServeur titre="Prêtes à servir" couleur="var(--menthe)">
      <div className="px-3 py-2.5">
        <div className="flex items-center gap-2.5">
          <span className={`${lalezar.className} text-xl leading-none text-[var(--encre)]`}>{DEMO.pretTable}</span>
          <div className="min-w-0 flex-1 text-[12px] font-semibold text-[var(--encre)]">
            Commande #{DEMO.pretCommandeNumero} — prête en cuisine
          </div>
          <span className="shrink-0 rounded-lg px-2.5 py-1.5 text-[11px] font-bold bg-[var(--menthe)] text-[var(--semoule)]">
            Servie
          </span>
        </div>
      </div>
    </PanneauServeur>
  );
}

function EtapeServeurEncaisser() {
  const total = DEMO.panier.reduce((sum, l) => sum + l.prix, 0);
  return (
    <PanneauServeur titre="Demandes d'encaissement" couleur="var(--laiton)">
      <div className="px-3 py-2.5">
        <div className="flex items-center gap-2.5">
          <span className={`${lalezar.className} text-xl leading-none text-[var(--encre)]`}>
            {DEMO.encaissementTable}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-[12px] font-semibold text-[var(--encre)]">
              Commande #{DEMO.encaissementCommandeNumero} — {formatMoney(total)}
            </p>
            <p className="text-[10px] text-[var(--ink-soft)] mt-0.5">{DEMO.encaissementMethode}</p>
          </div>
          <span className="shrink-0 rounded-lg px-2.5 py-1.5 text-[11px] font-bold bg-[var(--laiton)] text-[var(--espresso)]">
            Encaisser
          </span>
        </div>
      </div>
    </PanneauServeur>
  );
}

/* ---------------------------- CUISINE ---------------------------- */
// Poste fixe unique, sans carrousel (retour de Wassim : la cuisine ne
// bouge pas de table, contrairement au client/manager/serveur). La vraie
// cuisine (app/kitchen/page.tsx) n'a pas de colonnes par statut : une
// commande "prête" quitte l'écran (c'est au serveur de venir la chercher,
// plus à la cuisine). Une seule grille, l'urgence se lit à la couleur de la
// carte — neutre en attente, verte en préparation.
function EtapeCuisine() {
  const commandes = [
    { table: "Table 4", depuis: "1 min", enCours: false, plats: ["1× " + DEMO.panier[1].nom] },
    { table: "Table 2", depuis: "4 min", enCours: true, plats: ["2× " + DEMO.panier[0].nom] },
    { table: "Table 7", depuis: "2 min", enCours: false, plats: ["1× " + DEMO.panier[2].nom] },
  ];
  return (
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
  );
}

function ChromeBar() {
  return (
    <div className="flex items-center gap-1.5 px-3 py-2 bg-[#180f08]">
      <span className="w-2.5 h-2.5 rounded-full bg-[var(--harissa)]" />
      <span className="w-2.5 h-2.5 rounded-full bg-[var(--laiton)]" />
      <span className="w-2.5 h-2.5 rounded-full bg-[var(--menthe)]" />
    </div>
  );
}

function EcranCuisine() {
  return (
    <div className="w-full max-w-[600px] rounded-xl overflow-hidden shadow-[0_30px_60px_-20px_rgba(0,0,0,.6)] bg-[var(--espresso)]">
      <ChromeBar />
      <EtapeCuisine />
    </div>
  );
}
