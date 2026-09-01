"use client";

import { useRouter } from "next/navigation";
import { lalezar } from "@/lib/fonts";
import { CGV } from "@/lib/i18n/cgv";

/**
 * Conditions générales de vente — SaaS B2B (marché France).
 *
 * Page publique, atteignable depuis le pied de page — même emplacement et
 * même style de lien que /confidentialite.
 *
 * BROUILLON : texte en attente de validation par un professionnel avant
 * mise en ligne définitive (bandeau d'avertissement ci-dessous).
 */
export default function CgvPage() {
  const router = useRouter();
  const page = CGV;

  return (
    <main className="min-h-screen bg-[var(--semoule)]">
      <div className="max-w-2xl mx-auto px-5 py-8">
        <button onClick={() => router.back()} className="text-sm underline text-[var(--ink-soft)] mb-6 inline-block">
          Retour
        </button>

        <div
          role="status"
          className="rounded-lg border border-[var(--laiton)] bg-[var(--semoule-raised)] text-[var(--ink-soft)] text-xs px-4 py-2 mb-6"
        >
          Document en cours de finalisation — en attente de validation par un professionnel avant mise en ligne
          définitive.
        </div>

        <h1 className={`${lalezar.className} text-2xl sm:text-3xl mb-3`}>{page.title}</h1>
        <p className="text-[var(--ink-soft)]">{page.intro}</p>

        {page.sections.map((section) => (
          <section key={section.title} className="mt-8">
            <h2 className="font-semibold mb-2">{section.title}</h2>
            {section.paragraphs?.map((paragraph) => (
              <p key={paragraph} className="text-sm text-[var(--ink-soft)] mb-2 leading-relaxed">
                {paragraph}
              </p>
            ))}
            {section.list && (
              <ul className="list-disc pl-5 text-sm text-[var(--ink-soft)] mb-2 leading-relaxed space-y-1">
                {section.list.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            )}
          </section>
        ))}
      </div>
    </main>
  );
}
