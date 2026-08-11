import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Tawla — Commande au restaurant",
    short_name: "Tawla",
    description: "Commande via QR code sur table",
    start_url: "/",
    display: "standalone",
    background_color: "#F6EFDD",
    theme_color: "#D6401E",
    icons: [
      { src: "/pwa-icon-192", sizes: "192x192", type: "image/png" },
      { src: "/pwa-icon-512", sizes: "512x512", type: "image/png" },
    ],
  };
}
