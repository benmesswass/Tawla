"use client";

import { Suspense, useEffect } from "react";
import { initAnalytics } from "@/lib/analytics";
import PageviewTracker from "./PageviewTracker";

/**
 * `useSearchParams` (dans PageviewTracker) exige une frontière Suspense en
 * App Router, sinon le build échoue — voir doc PostHog/Next.js.
 */
export default function Analytics() {
  useEffect(() => {
    initAnalytics();
  }, []);

  return (
    <Suspense fallback={null}>
      <PageviewTracker />
    </Suspense>
  );
}
