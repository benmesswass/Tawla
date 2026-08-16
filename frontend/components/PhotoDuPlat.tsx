"use client";

import { useRef, useState } from "react";
import { mediaUrl, type MenuItem } from "@/lib/api";
import { FORMATS_ACCEPTES } from "@/lib/photo";
import { UtensilsIcon } from "@/components/icons";

/**
 * La vignette d'un plat **est** la zone de dépôt : le manager fait glisser la
 * photo dessus, ou clique pour la choisir. Pas de champ, pas de modale, pas de
 * bouton « parcourir » — une carte de quarante plats se garnit en quarante
 * gestes, et chaque écran intermédiaire en aurait fait quatre-vingts.
 */
export default function PhotoDuPlat({
  item,
  enCours,
  onFichier,
  onRetirer,
}: {
  item: MenuItem;
  enCours: boolean;
  onFichier: (fichier: File) => void;
  onRetirer: () => void;
}) {
  const [survol, setSurvol] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const photo = mediaUrl(item.image_url);

  function deposer(e: React.DragEvent) {
    e.preventDefault();
    setSurvol(false);
    const fichier = Array.from(e.dataTransfer.files).find((f) => FORMATS_ACCEPTES.includes(f.type));
    if (fichier) onFichier(fichier);
  }

  return (
    <div className="relative shrink-0 group">
      <button
        type="button"
        onClick={() => input.current?.click()}
        onDragOver={(e) => {
          // Sans annuler ces deux événements, le navigateur ouvre l'image dans
          // un onglet au lieu de la laisser tomber sur la vignette.
          e.preventDefault();
          setSurvol(true);
        }}
        onDragLeave={() => setSurvol(false)}
        onDrop={deposer}
        aria-label={photo ? `Remplacer la photo de ${item.name}` : `Ajouter une photo à ${item.name}`}
        className={`w-11 h-11 rounded-lg overflow-hidden flex items-center justify-center transition-all ${
          survol
            ? "ring-2 ring-[var(--harissa)] ring-offset-1 scale-105"
            : "ring-1 ring-[var(--line)]"
        } ${photo ? "" : "bg-neutral-100 text-neutral-400"}`}
      >
        {enCours ? (
          <span className="text-[10px] text-neutral-500">…</span>
        ) : photo ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={photo} alt={item.name} className="w-full h-full object-cover" />
        ) : (
          <UtensilsIcon className="w-5 h-5" />
        )}
      </button>

      {photo && !enCours && (
        <button
          type="button"
          onClick={onRetirer}
          aria-label={`Retirer la photo de ${item.name}`}
          className="absolute -top-1.5 -end-1.5 w-5 h-5 rounded-full bg-white text-neutral-500 ring-1 ring-[var(--line)] text-xs leading-none opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
        >
          ×
        </button>
      )}

      <input
        ref={input}
        type="file"
        accept={FORMATS_ACCEPTES.join(",")}
        className="hidden"
        onChange={(e) => {
          const fichier = e.target.files?.[0];
          if (fichier) onFichier(fichier);
          // Remis à zéro : sans ça, redéposer le même fichier après l'avoir
          // retiré ne déclencherait aucun événement.
          e.target.value = "";
        }}
      />
    </div>
  );
}
