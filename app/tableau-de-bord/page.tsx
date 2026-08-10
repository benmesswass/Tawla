import Link from "next/link";
import { redirect } from "next/navigation";
import { auth, signOut } from "@/lib/auth";

const LIBELLE_ROLE: Record<string, string> = {
  SERVEUR: "Serveur",
  CUISINE: "Cuisine",
  MANAGER: "Manager",
};

export default async function TableauDeBordPage() {
  const session = await auth();

  if (!session?.user) {
    redirect("/connexion");
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 px-4 py-10">
      <div>
        <p className="text-sm text-neutral-500">Connecté en tant que</p>
        <h1 className="text-2xl font-semibold text-neutral-900">{session.user.name}</h1>
        <p className="text-sm text-neutral-600">
          {LIBELLE_ROLE[session.user.role] ?? session.user.role} — {session.user.email}
        </p>
      </div>

      <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-4 text-sm text-neutral-600">
        Fondations posées (Phase 0 de ROADMAP.md). Les écrans serveur / cuisine / manager
        arriveront dans les phases suivantes de la roadmap.
      </div>

      {session.user.role === "MANAGER" && (
        <Link
          href="/manager/tables"
          className="w-fit rounded-md bg-neutral-900 px-3 py-2 text-sm font-medium text-white"
        >
          Voir les QR codes des tables
        </Link>
      )}

      <form
        action={async () => {
          "use server";
          await signOut({ redirectTo: "/connexion" });
        }}
      >
        <button
          type="submit"
          className="rounded-md border border-neutral-300 px-3 py-2 text-sm font-medium text-neutral-700"
        >
          Se déconnecter
        </button>
      </form>
    </main>
  );
}
