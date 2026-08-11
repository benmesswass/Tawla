import "./globals.css";
import ServiceWorkerRegister from "@/components/ServiceWorkerRegister";

export const metadata = {
  title: "Resto QR Menu",
  description: "Commande via QR code sur table",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className="bg-neutral-50 text-neutral-900">
        {children}
        <ServiceWorkerRegister />
      </body>
    </html>
  );
}
