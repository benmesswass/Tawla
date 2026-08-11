import TawlaMark from "./TawlaMark";
import { lalezar } from "@/lib/fonts";

type Props = {
  size?: number;
  className?: string;
};

export default function TawlaLogo({ size = 40, className }: Props) {
  return (
    <div className={`flex items-center gap-2 ${className ?? ""}`}>
      <TawlaMark size={size} />
      <span className={`${lalezar.className} text-2xl text-[var(--encre)]`}>tawla</span>
    </div>
  );
}
