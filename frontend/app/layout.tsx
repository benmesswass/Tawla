import "./globals.css";
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
        <ServiceWorkerRegister />
        <DemoGuide />
        <BandeauDemo />
        <BandeauAutreMarche />
        <VisiteGuidee />
      </body>
    </html>
  );
}
