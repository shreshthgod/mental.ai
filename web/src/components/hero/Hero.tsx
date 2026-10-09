import { lazy, Suspense } from "react";
import { Link } from "react-router-dom";

const Grainient = lazy(() =>
  import("../Grainient/Grainient").then((m) => ({ default: m.Grainient }))
);
const Stage = lazy(() => import("./Stage"));

/**
 * Wordmark glyphs. The full stop is rendered as its own node rather than a
 * character so it can carry the brand accent colour and read as a deliberate
 * separator instead of a stray baseline dot.
 */
const GLYPHS = [
  { ch: "M" },
  { ch: "E" },
  { ch: "N" },
  { ch: "T" },
  { ch: "A" },
  { ch: "L" },
  { ch: ".", dot: true },
  { ch: "A" },
  { ch: "I" },
];

/** Per-glyph scattered start poses (staircase assembly → clean word). */
function letterPose(i: number) {
  const mid = (GLYPHS.length - 1) / 2;
  const dx = (i - mid) * -0.05;
  const dy = (i - mid) * 0.16 + 0.3;
  const rot = (i % 2 === 0 ? 1 : -1) * (3 + i);
  return { dx, dy, rot, delay: 160 + i * 95 };
}

interface Props {
  live: boolean;
  instant: boolean;
}

export function Hero({ live, instant }: Props) {
  const stateCls = live ? "hero--live" : "hero--boot";
  return (
    <section className={`hero ${stateCls} ${instant ? "hero--instant" : ""}`} aria-label="MENTAL.AI - AI-assisted mental health screening">
      <Suspense fallback={<div className="hero__grainient" style={{ background: "radial-gradient(ellipse at 50% 30%, #16102e 0%, #0a0718 50%, #050507 100%)" }} />}>
        <Grainient
          className="hero__grainient"
          color1="#100d24"
          color2="#1a1340"
          color3="#040409"
          timeSpeed={0.3}
          warpStrength={0.3}
          warpFrequency={1.8}
          warpSpeed={0.12}
          warpAmplitude={60}
          blendAngle={128}
          blendSoftness={0.85}
          rotationAmount={36}
          grainAmount={0.045}
          grainScale={1.3}
          contrast={1.02}
          gamma={1.1}
          saturation={0.88}
          centerY={-0.04}
          zoom={1.9}
        />
      </Suspense>

      <div className="hero__vignette" aria-hidden="true" />

      <Suspense fallback={null}>
        <Stage className="hero__stage" emergeDelayMs={instant ? 100 : 1000} />
      </Suspense>

      <div className="hero__wordmark">
        <h1 className="hero__word">
          {GLYPHS.map(({ ch, dot }, i) => {
            const p = letterPose(i);
            return (
              <span
                key={i}
                className={`hero__letter ${dot ? "hero__letter--dot" : ""}`}
                style={{
                  ["--lx" as string]: `${p.dx}em`,
                  ["--ly" as string]: `${p.dy}em`,
                  ["--lr" as string]: `${p.rot}deg`,
                  ["--ld" as string]: `${instant ? i * 30 : p.delay}ms`,
                }}
              >
                {ch}
              </span>
            );
          })}
        </h1>
        <span className="sr-only">MENTAL.AI</span>
      </div>

      <div className="hero__copy">
        <p className="label label--accent">AI-assisted mental health screening</p>
        <p className="hero__headline">Inside the pipeline.</p>
        <p className="hero__sub">
          MENTAL.AI analyses language with a dual-model NLP pipeline - showing
          raw research signals alongside a separate, limited support assessment.
        </p>
        <div className="hero__ctas">
          <Link to="/screen" className="cta cta--primary">
            Start screening <span className="cta__arrow" aria-hidden="true">→</span>
          </Link>
          <Link to="/research" className="cta cta--ghost">
            Explore the research
          </Link>
        </div>
      </div>

      <p className="hero__side label" aria-hidden="true">
        Dual-model inference · XGBoost + LogReg · Proxy labels · Research signals
      </p>

      <div className="hero__scroll" aria-hidden="true">
        <span className="label">Scroll</span>
        <span className="hero__scroll-line" />
      </div>
    </section>
  );
}
