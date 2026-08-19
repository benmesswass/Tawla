"use client";

import { useEffect, useState } from "react";
import QRCode from "qrcode";

/**
 * QR code vers la facture PDF — pour la retrouver sur un autre appareil que
 * celui qui a commandé, ou sans avoir laissé d'e-mail (confirmations de
 * paiement, 2026-08-19). Généré entièrement côté client, jamais envoyé à un
 * service tiers.
 */
export default function InvoiceQr({ url, caption }: { url: string; caption: string }) {
  const [dataUrl, setDataUrl] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    QRCode.toDataURL(url, { margin: 1, width: 160 })
      .then((generated) => {
        if (!cancelled) setDataUrl(generated);
      })
      .catch(() => {
        // Best-effort : sans QR, le lien de téléchargement juste au-dessus
        // reste utilisable tel quel.
      });
    return () => {
      cancelled = true;
    };
  }, [url]);

  if (!dataUrl) return null;

  return (
    <div className="flex flex-col items-center gap-1 mt-2">
      {/* eslint-disable-next-line @next/next/no-img-element -- data URL générée localement, pas une image distante */}
      <img src={dataUrl} alt="QR code de la facture" width={120} height={120} className="rounded-lg border" />
      <p className="text-xs text-neutral-500">{caption}</p>
    </div>
  );
}
