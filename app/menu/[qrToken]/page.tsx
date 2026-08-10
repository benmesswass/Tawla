import { notFound } from "next/navigation";
import { prisma } from "@/lib/prisma";

export default async function MenuTablePage(props: PageProps<"/menu/[qrToken]">) {
  const { qrToken } = await props.params;

  const table = await prisma.table.findUnique({
    where: { qrToken },
    include: { restaurant: true },
  });

  if (!table) notFound();

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center gap-3 px-4 text-center">
      <h1 className="text-2xl font-semibold text-neutral-900">{table.restaurant.nom}</h1>
      <p className="text-sm text-neutral-600">Table {table.numero}</p>
      <p className="mt-6 text-sm text-neutral-500">
        Le menu digital et le panier arrivent à la Phase 1 de la roadmap. Ce QR code est déjà
        fonctionnel : il identifie bien la table {table.numero} du restaurant {table.restaurant.nom}.
      </p>
    </main>
  );
}
