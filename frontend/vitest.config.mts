import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

// Vitest ne lit pas les alias TypeScript de tsconfig.json tout seul —
// jusqu'ici sans conséquence, aucun test ne touchait un fichier hors de
// lib/ utilisant l'alias "@/…" (France, étape 8 : lib/visite/etapes.ts
// importe "@/lib/market", le premier cas réel). Miroir manuel plutôt que
// la dépendance vite-tsconfig-paths, pour une seule entrée ("@" -> racine
// du projet, comme tsconfig.json "paths": { "@/*": ["./*"] }).
export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL(".", import.meta.url)),
    },
  },
});
