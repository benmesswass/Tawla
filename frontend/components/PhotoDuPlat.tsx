"use client";

import { forwardRef, useEffect, useRef, useState } from "react";
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

      <ChampFichier ref={input} onFichier={onFichier} />
    </div>
  );
}

/**
 * La zone de dépôt du formulaire d'édition — celle qu'on cherche quand on
 * ouvre « Modifier ». La vignette de la liste est un raccourci pour garnir une
 * carte entière ; ici, on vient s'occuper d'un plat en particulier.
 */
export function ZonePhoto({
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

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setSurvol(true);
      }}
      onDragLeave={() => setSurvol(false)}
      onDrop={(e) => {
        e.preventDefault();
        setSurvol(false);
        const fichier = Array.from(e.dataTransfer.files).find((f) => FORMATS_ACCEPTES.includes(f.type));
        if (fichier) onFichier(fichier);
      }}
      className={`mt-2 rounded-lg border-2 border-dashed p-3 transition-colors ${
        survol ? "border-[var(--harissa)] bg-orange-50" : "border-[var(--line)]"
      }`}
    >
      <div className="flex items-center gap-3">
        {photo ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={photo} alt={item.name} className="w-16 h-16 rounded-lg object-cover shrink-0" />
        ) : (
          <div className="w-16 h-16 rounded-lg bg-neutral-100 flex items-center justify-center shrink-0 text-neutral-400">
            <UtensilsIcon className="w-6 h-6" />
          </div>
        )}
        <div className="min-w-0 flex-1">
          <p className="text-sm">
            {enCours ? "Envoi en cours…" : photo ? "Photo du plat" : "Glissez une photo ici"}
          </p>
          <p className="text-xs text-neutral-500 mt-0.5">
            JPEG, PNG ou WebP — redimensionnée automatiquement avant l&apos;envoi.
          </p>
          <div className="mt-1.5 flex gap-3 text-sm">
            <button
              type="button"
              onClick={() => input.current?.click()}
              className="underline text-[var(--harissa)]"
            >
              {photo ? "Remplacer" : "Choisir un fichier"}
            </button>
            {photo && (
              <button type="button" onClick={onRetirer} className="underline text-neutral-500">
                Retirer
              </button>
            )}
          </div>
        </div>
      </div>
      <ChampFichier ref={input} onFichier={onFichier} />
    </div>
  );
}

/**
 * Zone de dépôt du formulaire de création. Le plat n'a pas encore
 * d'identifiant, donc rien à envoyer : la photo est gardée de côté et part
 * juste après la création. L'aperçu vient d'une URL d'objet locale, révoquée
 * dès qu'une autre photo la remplace.
 */
export function ZonePhotoNouveau({
  fichier,
  onFichier,
}: {
  fichier: File | null;
  onFichier: (f: File | null) => void;
}) {
  const [survol, setSurvol] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const [apercu, setApercu] = useState<string | null>(null);

  useEffect(() => {
    if (!fichier) {
      setApercu(null);
      return;
    }
    const url = URL.createObjectURL(fichier);
    setApercu(url);
    return () => URL.revokeObjectURL(url);
  }, [fichier]);

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setSurvol(true);
      }}
      onDragLeave={() => setSurvol(false)}
      onDrop={(e) => {
        e.preventDefault();
        setSurvol(false);
        const trouve = Array.from(e.dataTransfer.files).find((f) => FORMATS_ACCEPTES.includes(f.type));
        if (trouve) onFichier(trouve);
      }}
      className={`mt-2 rounded-lg border-2 border-dashed p-3 transition-colors ${
        survol ? "border-[var(--harissa)] bg-orange-50" : "border-[var(--line)]"
      }`}
    >
      <div className="flex items-center gap-3">
        {apercu ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={apercu} alt="" className="w-16 h-16 rounded-lg object-cover shrink-0" />
        ) : (
          <div className="w-16 h-16 rounded-lg bg-neutral-100 flex items-center justify-center shrink-0 text-neutral-400">
            <UtensilsIcon className="w-6 h-6" />
          </div>
        )}
        <div className="min-w-0 flex-1">
          <p className="text-sm">{fichier ? fichier.name : "Glissez une photo ici (facultatif)"}</p>
          <p className="text-xs text-neutral-500 mt-0.5">
            Elle sera envoyée dès que le plat sera créé.
          </p>
          <div className="mt-1.5 flex gap-3 text-sm">
            <button
              type="button"
              onClick={() => input.current?.click()}
              className="underline text-[var(--harissa)]"
            >
              {fichier ? "Changer" : "Choisir un fichier"}
            </button>
            {fichier && (
              <button type="button" onClick={() => onFichier(null)} className="underline text-neutral-500">
                Retirer
              </button>
            )}
          </div>
        </div>
      </div>
      <ChampFichier ref={input} onFichier={onFichier} />
    </div>
  );
}

/** Le `<input type="file">` caché, identique aux trois zones de dépôt. */
const ChampFichier = forwardRef<HTMLInputElement, { onFichier: (f: File) => void }>(
  function ChampFichier({ onFichier }, ref) {
    return (
      <input
        ref={ref}
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
    );
  }
);
