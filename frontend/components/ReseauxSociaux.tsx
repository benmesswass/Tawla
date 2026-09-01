import FacebookIcon from "@/components/icons/FacebookIcon";
import InstagramIcon from "@/components/icons/InstagramIcon";
import TikTokIcon from "@/components/icons/TikTokIcon";
import WhatsAppIcon from "@/components/icons/WhatsAppIcon";
import type { RestaurantPublic } from "@/lib/api";

const RESEAUX = [
  { url: "facebook_url", Icon: FacebookIcon, label: "Facebook" },
  { url: "instagram_url", Icon: InstagramIcon, label: "Instagram" },
  { url: "tiktok_url", Icon: TikTokIcon, label: "TikTok" },
  { url: "whatsapp_url", Icon: WhatsAppIcon, label: "WhatsApp" },
] as const;

/**
 * Icônes réseaux sociaux du menu client (Phase D1 de ROADMAP_DESIGN.md,
 * point 3) — rien du tout si le restaurant n'a renseigné aucun lien.
 */
export default function ReseauxSociaux({
  restaurant,
  className,
}: {
  restaurant: RestaurantPublic;
  className?: string;
}) {
  const liens = RESEAUX.filter(({ url }) => restaurant[url]);
  if (liens.length === 0) return null;
  return (
    <div className={`flex items-center gap-2 ${className ?? ""}`}>
      {liens.map(({ url, Icon, label }) => (
        <a
          key={url}
          href={restaurant[url]!}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={label}
          className="text-[rgba(246,239,221,.85)]"
        >
          <Icon className="w-[15px] h-[15px]" />
        </a>
      ))}
    </div>
  );
}
