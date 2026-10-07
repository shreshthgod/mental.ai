import { useEffect, useState } from "react";
import { Hero } from "../components/hero/Hero";
import { Statement } from "../components/landing/Statement";
import { Pipeline } from "../components/landing/Pipeline";
import { DualSignal } from "../components/landing/DualSignal";
import { Metrics } from "../components/landing/Metrics";
import { Limitations, ClosingCta } from "../components/landing/Limitations";
import { Footer } from "../components/chrome/Footer";

const INTRO_KEY = "mental.ai_intro_played";

export function Landing({ onSettled }: { onSettled: (settled: boolean) => void }) {
  const [live, setLive] = useState(false);
  const [instant] = useState(() => {
    try {
      return sessionStorage.getItem(INTRO_KEY) === "1";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    const raf = requestAnimationFrame(() => setLive(true));
    // Nav settles right after the letter assembly (~0.95s), or immediately.
    const settleTimer = setTimeout(
      () => onSettled(true),
      instant ? 200 : 980
    );
    if (!instant) {
      try {
        sessionStorage.setItem(INTRO_KEY, "1");
      } catch {
        /* private mode */
      }
    }
    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(settleTimer);
    };
  }, [instant, onSettled]);

  return (
    <main id="main">
      <Hero live={live} instant={instant} />
      <Statement />
      <Pipeline />
      <DualSignal />
      <Metrics />
      <Limitations />
      <ClosingCta />
      <Footer />
    </main>
  );
}
