"use client";

import type { AnchorHTMLAttributes } from "react";
import { trackEvent } from "@/lib/analytics";

type Props = AnchorHTMLAttributes<HTMLAnchorElement> & {
  event: string;
  eventProperties?: Record<string, unknown>;
};

export default function TrackedAnchor({ event, eventProperties, onClick, ...anchorProps }: Props) {
  return (
    <a
      {...anchorProps}
      onClick={(e) => {
        trackEvent(event, eventProperties);
        onClick?.(e);
      }}
    />
  );
}
