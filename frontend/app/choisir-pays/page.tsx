/**
 * Le hub (France, MARCHE_FRANCE.md Phase F4 §5) : deux options claires,
 * rendues côté serveur, en `<a href>` réels — fonctionne sans JavaScript.
 * Aucun appel API, aucun accès base : cette page ne doit jamais pouvoir
 * tomber en même temps qu'un backend.
 *
 * Le parcours client (`/menu/<qr_token>`) ne passe JAMAIS par cette page —
 * rien dans ce fichier n'y fait référence, et rien dans `/menu/[qrToken]`
 * ne référence celui-ci : la garantie tient par construction, pas par un
 * garde-fou ajouté après coup.
 *
 * Cookie déjà posé (retour sur le hub) → redirection immédiate, sauf
 * `?choisir=1` (échappatoire utilisée par le lien « changer de pays » d'un
 * site de marché — Phase F4 étape 2). `?market=` seul saute directement la
 * page et redirige (spec §5, "indispensable pour les tests, les
 * démonstrations et les liens de campagne").
 */
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { detectMarketFromHeaders } from "@/lib/geoMarket";
import { isSupportedMarketCode } from "@/lib/marketUrls";

const OPTIONS: { code: "tn" | "fr"; name: string }[] = [
  { code: "tn", name: "Tunisie" },
  { code: "fr", name: "France" },
];

export default async function ChoisirPaysPage({
  searchParams,
}: {
  searchParams: Promise<{ market?: string; choisir?: string }>;
}) {
  const params = await searchParams;

  if (isSupportedMarketCode(params.market ?? null)) {
    redirect(`/api/choisir-marche?market=${params.market}`);
  }

  const existing = (await cookies()).get("tawla-market")?.value ?? null;
  if (params.choisir !== "1" && isSupportedMarketCode(existing)) {
    redirect(`/api/choisir-marche?market=${existing}`);
  }

  const detected = detectMarketFromHeaders(await headers());
  const options = detected ? [...OPTIONS].sort((a, b) => (a.code === detected ? -1 : b.code === detected ? 1 : 0)) : OPTIONS;

  return (
    <main className="min-h-screen flex items-center justify-center px-4 py-16" style={{ background: "var(--semoule)" }}>
      <div className="w-full max-w-md">
        <h1 className="text-2xl font-semibold text-center mb-2" style={{ color: "var(--espresso)" }}>
          Choisissez votre pays
        </h1>
        <p className="text-center mb-8" style={{ color: "var(--ink-soft)" }}>
          Tawla fonctionne un peu différemment selon le pays.
        </p>
        <ul className="flex flex-col gap-4">
          {options.map((option) => (
            <li key={option.code}>
              <a
                href={`/api/choisir-marche?market=${option.code}`}
                className="flex items-center justify-between rounded-2xl border-2 px-6 py-4 min-h-[56px] transition-colors"
                style={{
                  borderColor: option.code === detected ? "var(--harissa)" : "var(--line)",
                  background: "var(--semoule-raised)",
                  color: "var(--espresso)",
                }}
              >
                <span className="text-lg font-medium">{option.name}</span>
                {option.code === detected && (
                  // harissa-pressed, pas harissa : harissa+semoule ne tient
                  // que 3.97:1 (sous les 4.5:1 WCAG AA pour du texte de cette
                  // taille) — vérifié au calcul, pas à l'œil.
                  <span className="text-sm rounded-full px-3 py-1" style={{ background: "var(--harissa-pressed)", color: "var(--semoule)" }}>
                    Détecté
                  </span>
                )}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </main>
  );
}
