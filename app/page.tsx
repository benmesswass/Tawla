import Link from "next/link";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 px-4 text-center">
      <h1 className="text-2xl font-semibold text-neutral-900">Tawla</h1>
      <p className="max-w-md text-sm text-neutral-600">
        Commande depuis la table pour restaurants tunisiens. Les clients passent par le QR code
        posé sur leur table ; l&apos;espace staff (serveurs, cuisine, manager) se trouve ci-dessous.
      </p>
      <Link
        href="/connexion"
        className="rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white"
      >
        Connexion staff
      </Link>
    </main>
  );
}
