import { redirect } from "next/navigation";
import Image from "next/image";
import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { genererQrCodeDataUrl, urlMenuTable } from "@/lib/qrcode";

export default async function TablesPage() {
  const session = await auth();
  if (!session?.user) redirect("/connexion");
  if (session.user.role !== "MANAGER") redirect("/tableau-de-bord");

  const tables = await prisma.table.findMany({
    where: { restaurantId: session.user.restaurantId },
    orderBy: { numero: "asc" },
  });

  const baseUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

  const tablesAvecQr = await Promise.all(
    tables.map(async (table) => {
      const url = urlMenuTable(table.qrToken, baseUrl);
      return { ...table, url, qr: await genererQrCodeDataUrl(url) };
    })
  );

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="mb-6 text-2xl font-semibold text-neutral-900">QR codes par table</h1>
      <div className="grid grid-cols-2 gap-6 sm:grid-cols-3">
        {tablesAvecQr.map((table) => (
          <div
            key={table.id}
            className="flex flex-col items-center gap-2 rounded-lg border border-neutral-200 p-4"
          >
            <p className="text-sm font-medium text-neutral-700">Table {table.numero}</p>
            <Image
              src={table.qr}
              alt={`QR code table ${table.numero}`}
              width={160}
              height={160}
              unoptimized
            />
            <p className="break-all text-center text-xs text-neutral-500">{table.url}</p>
          </div>
        ))}
      </div>
    </main>
  );
}
