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
        menthe: "var(--menthe)",
        laiton: "var(--laiton)",
        line: "var(--line)",
        "ink-soft": "var(--ink-soft)",
      },
    },
  },
  plugins: [],
};
