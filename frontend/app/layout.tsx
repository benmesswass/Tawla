import "./globals.css";
import Analytics from "@/components/Analytics";
import ServiceWorkerRegister from "@/components/ServiceWorkerRegister";
import DemoGuide from "@/components/DemoGuide";
import VisiteGuidee from "@/components/visite/VisiteGuidee";
import BandeauDemo from "@/components/visite/BandeauDemo";
import BandeauAutreMarche from "@/components/BandeauAutreMarche";
import { hankenGrotesk } from "@/lib/fonts";

export const metadata = {
  title: "Tawla — Commande au restaurant",
  description: "Commande via QR code sur table",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body
        className={`${hankenGrotesk.className} bg-[var(--semoule)] text-[var(--espresso)]`}
      >
        {children}
        <Analytics />
        <ServiceWorkerRegister />
        <DemoGuide />
        {/* Bandeaux du haut empilés ici plutôt que positionnés en `fixed`
            chacun de leur côté : sinon, démo + décalage de marché détectés en
            même temps se superposent exactement et l'un cache l'autre. */}
        <div className="fixed top-0 inset-x-0 z-[72] flex flex-col items-center gap-2 px-3 pt-2 pointer-events-none">
          {/* BandeauAutreMarche d'abord : sa position reste stable quand le
              panneau de BandeauDemo s'ouvre et grandit, au lieu d'être
              repoussé plus bas à chaque clic. */}
          <BandeauAutreMarche />
          <BandeauDemo />
        </div>
        <VisiteGuidee />
      </body>
    </html>
  );
}
