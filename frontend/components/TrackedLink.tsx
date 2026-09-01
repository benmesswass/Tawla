"use client";

import type { ComponentProps } from "react";
import Link from "next/link";
import { trackEvent } from "@/lib/analytics";

type Props = ComponentProps<typeof Link> & {
  event: string;
  eventProperties?: Record<string, unknown>;
};

export default function TrackedLink({ event, eventProperties, onClick, ...linkProps }: Props) {
  return (
    <Link
      {...linkProps}
      onClick={(e) => {
        trackEvent(event, eventProperties);
        onClick?.(e);
      }}
    />
  );
}
