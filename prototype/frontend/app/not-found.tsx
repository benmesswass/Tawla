export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center p-6 text-center">
      <div>
        <h1 className="text-xl font-semibold mb-2">Page introuvable</h1>
        <p className="text-neutral-600 max-w-sm">Vérifiez le QR code scanné, ou l&apos;adresse saisie.</p>
      </div>
    </div>
  );
}
