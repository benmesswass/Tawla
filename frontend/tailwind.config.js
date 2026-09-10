/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        semoule: "var(--semoule)",
        "semoule-raised": "var(--semoule-raised)",
        espresso: "var(--espresso)",
        encre: "var(--encre)",
        creme: "var(--creme)",
        harissa: "var(--harissa)",
        "harissa-dark": "var(--harissa-dark)",
        "harissa-pressed": "var(--harissa-pressed)",
        "on-harissa": "var(--on-harissa)",
        // Réservés au texte — voir la note de globals.css : les accents en
        // aplat ne passent pas le seuil AA une fois posés en texte.
        "harissa-text": "var(--harissa-text)",
        "laiton-text": "var(--laiton-text)",
        menthe: "var(--menthe)",
        laiton: "var(--laiton)",
        line: "var(--line)",
        "line-strong": "var(--line-strong)",
        "ink-soft": "var(--ink-soft)",
        "ink-faint": "var(--ink-faint)",
      },

      // Sept tailles nommées par rôle, contre 25 tailles en dur relevées le
      // 2026-09-09 (de 9 à 28 px, par pas de 0,5 — des paliers qui ne se
      // distinguent pas à l'œil, seulement dans le diff). `corps` n'existe
      // qu'une fois : ce qui sépare le texte courant du texte appuyé est la
      // graisse, pas la taille.
      fontSize: {
        "affiche-xl": ["34px", { lineHeight: "1.05" }],
        affiche: ["28px", { lineHeight: "1.05" }],
        titre: ["19px", { lineHeight: "1.25" }],
        corps: ["15px", { lineHeight: "1.5" }],
        etiquette: ["13px", { lineHeight: "1.35" }],
        legende: ["12px", { lineHeight: "1.4" }],
        surtitre: ["11px", { lineHeight: "1", letterSpacing: "0.14em" }],
      },

      // Nommés par rôle et non par taille : « une carte de plat est-elle en md
      // ou en lg ? » est une question sans réponse, et c'est de là que vient
      // la dérive. Les `rounded-lg/xl/2xl` de Tailwind restent disponibles —
      // les 140 usages existants ne sont pas réécrits ici, ils migrent au fur
      // et à mesure que chaque page est reprise.
      borderRadius: {
        champ: "6px",
        controle: "10px",
        carte: "14px",
        feuille: "20px",
      },

      boxShadow: {
        pose: "var(--elev-pose)",
        carte: "var(--elev-carte)",
        barre: "var(--elev-barre)",
        couche: "var(--elev-couche)",
      },

      transitionDuration: {
        micro: "var(--motion-micro)",
        rapide: "var(--motion-fast)",
        normal: "var(--motion-normal)",
        lent: "var(--motion-slow)",
        sortie: "var(--motion-exit)",
      },

      transitionTimingFunction: {
        entree: "var(--ease-enter)",
        sortie: "var(--ease-exit)",
        deplacement: "var(--ease-move)",
      },
    },
  },
  plugins: [],
};
