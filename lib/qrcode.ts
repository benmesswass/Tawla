import QRCode from "qrcode";

export function urlMenuTable(qrToken: string, baseUrl: string): string {
  return `${baseUrl}/menu/${qrToken}`;
}

export async function genererQrCodeDataUrl(url: string): Promise<string> {
  return QRCode.toDataURL(url, { margin: 1, width: 240 });
}
