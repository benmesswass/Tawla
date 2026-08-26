// Génère une carte visuelle de la commande (format story 1080×1920) pour
// partage Instagram/WhatsApp Status — entièrement dessinée sur <canvas>,
// aucune image externe à héberger. Rendu pixel uniquement : les libellés
// fixes ci-dessous restent volontairement en dehors du dictionnaire i18n
// principal (portée limitée à cette carte, jamais affichés autrement).
import { formatMoney } from "./currency";
const CANVAS_LABELS: Record<
  "fr" | "ar",
  { tagline: string; footer: string; total: string; tip: string; table: (label: string, id: number) => string }
> = {
  fr: {
    tagline: "Mon repas sur Tawla",
    footer: "tawla.tn",
    total: "TOTAL",
    tip: "Pourboire",
    table: (label, id) => `${label} · Commande #${id}`,
  },
  ar: {
    tagline: "الماكلة تاعي عبر Tawla",
    footer: "tawla.tn",
    total: "المجموع",
    tip: "بقشيش",
    table: (label, id) => `${label} · طلبية #${id}`,
  },
};

type ShareCardParams = {
  restaurantName: string;
  /** Prix unitaire et total de ligne : la carte tient lieu de note, pas de
   *  simple souvenir — c'est ce que le client relit pour vérifier l'addition. */
  items: { name: string; quantity: number; unitPrice: number; lineTotal: number }[];
  total: number;
  tip: number;
  tableLabel: string;
  orderId: number;
  locale: "fr" | "ar";
};

const MARGE = 110;

export async function generateShareCardBlob(params: ShareCardParams): Promise<Blob | null> {
  const canvas = document.createElement("canvas");
  canvas.width = 1080;
  canvas.height = 1920;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;

  const labels = CANVAS_LABELS[params.locale];
  const rtl = params.locale === "ar";
  ctx.direction = rtl ? "rtl" : "ltr";

  // Les montants se lisent alignés à droite en français, à gauche en arabe :
  // dans les deux cas du côté opposé au libellé, sinon les chiffres se
  // perdent au milieu de la ligne.
  const xLibelle = rtl ? canvas.width - MARGE : MARGE;
  const xMontant = rtl ? MARGE : canvas.width - MARGE;
  const alignLibelle: CanvasTextAlign = rtl ? "right" : "left";
  const alignMontant: CanvasTextAlign = rtl ? "left" : "right";

  const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
  gradient.addColorStop(0, "#d6401e");
  gradient.addColorStop(1, "#7a2812");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.fillStyle = "rgba(255,255,255,0.08)";
  ctx.beginPath();
  ctx.arc(120, 160, 220, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.arc(canvas.width - 100, canvas.height - 220, 260, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = "#ffffff";
  ctx.textAlign = "center";
  ctx.font = "600 40px sans-serif";
  ctx.fillText(labels.tagline, canvas.width / 2, 420);

  ctx.font = "bold 72px sans-serif";
  const apresNom = wrapText(ctx, params.restaurantName, canvas.width / 2, 520, 900, 84);

  ctx.font = "36px sans-serif";
  ctx.fillStyle = "rgba(255,255,255,0.8)";
  ctx.fillText(labels.table(params.tableLabel, params.orderId), canvas.width / 2, apresNom + 62);

  let y = apresNom + 160;
  ligne(ctx, y, canvas.width);

  // Les lignes de la note. Au-delà de neuf plats la carte déborderait : le
  // reste est résumé par son montant, jamais escamoté — une addition dont il
  // manque une ligne ne vaut rien.
  y += 78;
  ctx.fillStyle = "#ffffff";
  const visibles = params.items.slice(0, 9);
  for (const item of visibles) {
    ctx.font = "44px sans-serif";
    ctx.textAlign = alignLibelle;
    ctx.fillText(`${item.quantity}× ${item.name}`, xLibelle, y, 660);
    ctx.textAlign = alignMontant;
    ctx.fillText(montant(item.lineTotal), xMontant, y);
    y += 78;
  }

  const restants = params.items.slice(visibles.length);
  if (restants.length > 0) {
    const resteMontant = restants.reduce((s, i) => s + i.lineTotal, 0);
    ctx.font = "40px sans-serif";
    ctx.fillStyle = "rgba(255,255,255,0.85)";
    ctx.textAlign = alignLibelle;
    ctx.fillText(`+ ${restants.length}`, xLibelle, y);
    ctx.textAlign = alignMontant;
    ctx.fillText(montant(resteMontant), xMontant, y);
    y += 78;
  }

  if (params.tip > 0) {
    ctx.font = "40px sans-serif";
    ctx.fillStyle = "rgba(255,255,255,0.85)";
    ctx.textAlign = alignLibelle;
    ctx.fillText(labels.tip, xLibelle, y);
    ctx.textAlign = alignMontant;
    ctx.fillText(montant(params.tip), xMontant, y);
    y += 78;
  }

  y += 14;
  ligne(ctx, y, canvas.width);
  y += 86;

  ctx.fillStyle = "#ffffff";
  ctx.font = "bold 56px sans-serif";
  ctx.textAlign = alignLibelle;
  ctx.fillText(labels.total, xLibelle, y);
  ctx.textAlign = alignMontant;
  ctx.fillText(montant(params.total + params.tip), xMontant, y);

  ctx.font = "36px sans-serif";
  ctx.fillStyle = "rgba(255,255,255,0.85)";
  ctx.textAlign = "center";
  ctx.fillText(labels.footer, canvas.width / 2, canvas.height - 120);

  return new Promise((resolve) => canvas.toBlob((blob) => resolve(blob), "image/png"));
}

const montant = formatMoney;

function ligne(ctx: CanvasRenderingContext2D, y: number, largeur: number) {
  ctx.strokeStyle = "rgba(255,255,255,0.4)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(MARGE, y);
  ctx.lineTo(largeur - MARGE, y);
  ctx.stroke();
}

/** Renvoie l'ordonnée de la dernière ligne écrite, pour que l'appelant
 *  enchaîne sans deviner combien de lignes le nom a pris. */
function wrapText(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  maxWidth: number,
  lineHeight: number
): number {
  const words = text.split(" ");
  let line = "";
  let lineY = y;
  for (const word of words) {
    const testLine = line ? `${line} ${word}` : word;
    if (ctx.measureText(testLine).width > maxWidth && line) {
      ctx.fillText(line, x, lineY);
      line = word;
      lineY += lineHeight;
    } else {
      line = testLine;
    }
  }
  ctx.fillText(line, x, lineY);
  return lineY;
}
