"use client";

import { useRouter } from "next/navigation";
import { lalezar } from "@/lib/fonts";
import { useLocale } from "@/lib/i18n/useLocale";
import { getPrivacyPage } from "@/lib/i18n/privacy";
import { currentMarket } from "@/lib/market";

/**
 * Politique de confidentialité (Phase 16).
 *
 * Page publique, atteignable sans commande en cours : c'est le lien affiché
 * sous le champ « numéro de téléphone » du parcours client, et un client doit
 * pouvoir la relire après coup.
 *
 * Réutilise la langue déjà choisie sur le menu (même clé de stockage) — un
 * client qui commande en arabe ne doit pas retomber sur du français ici.
 */
export default function PrivacyPage() {
  const router = useRouter();
  const { locale, toggleLocale, t } = useLocale();
  const page = getPrivacyPage(locale);
  // Langue "autre" que celle du bouton de bascule — dérivée du marché
  // (fr/ar en Tunisie, fr/en en France), jamais "ar" en dur (F5-A9).
  const otherLanguage = currentMarket().languages.find((code) => code !== locale) ?? locale;

  return (
    <main dir={page.dir} className="min-h-screen bg-[var(--semoule)]">
      <div className="max-w-2xl mx-auto px-5 py-8">
        <div className="flex items-center justify-between gap-4 mb-6">
          <button onClick={() => router.back()} className="text-sm underline text-[var(--ink-soft)]">
            {page.backToMenu}
          </button>
          <button
            onClick={toggleLocale}
            className="text-sm border rounded-lg px-3 py-1.5 bg-white"
            lang={otherLanguage}
          >
            {t.localeSwitchLabel}
          </button>
        </div>

        <h1 className={`${lalezar.className} text-2xl sm:text-3xl mb-3`}>{page.title}</h1>
        <p className="text-[var(--ink-soft)]">{page.intro}</p>
        <p className="text-xs text-[var(--ink-soft)] mt-2">{page.updatedAt}</p>

        {page.sections.map((section) => (
          <section key={section.title} className="mt-8">
            <h2 className="font-semibold mb-2">{section.title}</h2>
            {section.paragraphs.map((paragraph) => (
              <p key={paragraph} className="text-sm text-[var(--ink-soft)] mb-2 leading-relaxed">
                {paragraph}
              </p>
            ))}
          </section>
        ))}
      </div>
    </main>
  );
}
