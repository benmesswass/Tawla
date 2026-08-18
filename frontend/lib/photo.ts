"use client";

// Une photo prise au téléphone pèse 3 à 8 Mo pour 4000 px de large, alors que
// la carte l'affiche en 80 px sur mobile et 200 px au plus sur le dashboard.
// L'envoyer telle quelle immobiliserait la connexion du restaurant pendant que
// le service tourne — et gonflerait la base d'un facteur trente pour un
// résultat identique à l'œil.
const COTE_MAX = 1200;
const QUALITE = 0.82;

export const FORMATS_ACCEPTES = ["image/jpeg", "image/png", "image/webp"];

/**
 * Réduit la photo dans le navigateur avant l'envoi. Renvoie le fichier
 * d'origine si le redimensionnement échoue : mieux vaut un envoi lourd qu'un
 * manager bloqué devant une carte sans photos.
 */
export async function reduirePhoto(file: File): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(file);
    const facteur = Math.min(1, COTE_MAX / Math.max(bitmap.width, bitmap.height));
    if (facteur === 1 && file.size < 600_000) return file;

    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * facteur);
    canvas.height = Math.round(bitmap.height * facteur);
    const ctx = canvas.getContext("2d");
    if (!ctx) return file;
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", QUALITE)
    );
    return blob ?? file;
  } catch {
    return file;
  }
}
