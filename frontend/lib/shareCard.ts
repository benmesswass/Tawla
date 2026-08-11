// Génère une carte visuelle de la commande (format story 1080×1920) pour
// partage Instagram/WhatsApp Status — entièrement dessinée sur <canvas>,
// aucune image externe à héberger. Rendu pixel uniquement : les libellés
// fixes ci-dessous restent volontairement en dehors du dictionnaire i18n
// principal (portée limitée à cette carte, jamais affichés autrement).
const CANVAS_LABELS: Record<"fr" | "ar", { tagline: string; footer: string }> = {
  fr: { tagline: "Mon repas sur Tawla", footer: "tawla.tn" },
  ar: { tagline: "الماكلة تاعي عبر Tawla", footer: "tawla.tn" },
};

type ShareCardParams = {
  restaurantName: string;
  items: { name: string; quantity: number }[];
  locale: "fr" | "ar";
};

export async function generateShareCardBlob(params: ShareCardParams): Promise<Blob | null> {
  const canvas = document.createElement("canvas");
  canvas.width = 1080;
  canvas.height = 1920;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;

  const labels = CANVAS_LABELS[params.locale];
  ctx.direction = params.locale === "ar" ? "rtl" : "ltr";
  ctx.textAlign = "center";

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
  ctx.font = "600 40px sans-serif";
  ctx.fillText(labels.tagline, canvas.width / 2, 480);

  ctx.font = "bold 72px sans-serif";
  wrapText(ctx, params.restaurantName, canvas.width / 2, 580, 900, 84);

  ctx.strokeStyle = "rgba(255,255,255,0.4)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(canvas.width / 2 - 120, 720);
  ctx.lineTo(canvas.width / 2 + 120, 720);
  ctx.stroke();

  ctx.font = "48px sans-serif";
  let y = 840;
  const visibleItems = params.items.slice(0, 8);
  for (const item of visibleItems) {
    ctx.fillText(`${item.quantity}× ${item.name}`, canvas.width / 2, y);
    y += 90;
  }
  if (params.items.length > visibleItems.length) {
    ctx.font = "36px sans-serif";
    ctx.fillText(`+${params.items.length - visibleItems.length}`, canvas.width / 2, y + 20);
  }

  ctx.font = "36px sans-serif";
  ctx.fillStyle = "rgba(255,255,255,0.85)";
  ctx.fillText(labels.footer, canvas.width / 2, canvas.height - 120);

  return new Promise((resolve) => canvas.toBlob((blob) => resolve(blob), "image/png"));
}

function wrapText(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  maxWidth: number,
  lineHeight: number
) {
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
}
