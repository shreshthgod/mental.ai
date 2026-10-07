import { useInView, useCountUp } from "../../lib/motion";
import { Reveal } from "../motion/Reveal";

interface MetricDef {
  value: number;
  decimals: number;
  label: string;
  note: string;
  format?: (v: string) => string;
}

const METRICS: MetricDef[] = [
  { value: 53043, decimals: 0, label: "Primary records", note: "Combined Data.csv - 7-class condition dataset" },
  { value: 232074, decimals: 0, label: "Urgency records", note: "Suicide_Detection.csv - binary safety-net dataset" },
  { value: 0.6926, decimals: 4, label: "Primary macro-F1", note: "XGBoost, held-out test split" },
  { value: 0.987, decimals: 3, label: "Suicide recall", note: "At the deployed 0.15 urgency threshold" },
];

function Metric({ m, active, delay }: { m: MetricDef; active: boolean; delay: number }) {
  const raw = useCountUp(m.value, active, 1500 + delay, m.decimals);
  const display = m.decimals === 0 ? Number(raw).toLocaleString("en-US") : raw;
  return (
    <div className="metric">
      <p className="metric__value num">{display}</p>
      <p className="metric__label">{m.label}</p>
      <p className="metric__note">{m.note}</p>
    </div>
  );
}

export function Metrics() {
  const [ref, inView] = useInView<HTMLDivElement>(0.3);
  return (
    <section className="section" aria-labelledby="metrics-h">
      <div className="section__inner">
        <div className="section__head">
          <div>
            <Reveal>
              <p className="label label--accent">Verified results</p>
            </Reveal>
            <Reveal delayMs={80}>
              <h2 id="metrics-h" className="section__title">
                Numbers from the repository. Nothing invented.
              </h2>
            </Reveal>
          </div>
          <Reveal delayMs={160}>
            <p className="label">Held-out test evaluation</p>
          </Reveal>
        </div>

        <div ref={ref} className="metrics__grid">
          {METRICS.map((m, i) => (
            <Metric key={m.label} m={m} active={inView} delay={i * 120} />
          ))}
        </div>

        <div className="metrics__explain">
          <Reveal>
            <span className="label label--accent">The 0.15 threshold, honestly</span>
            <p>
              The urgency model scores <strong>0.9431 macro-F1</strong> at the default
              0.5 threshold. MENTAL.AI deploys it at <strong>0.15</strong> - macro-F1
              drops to <strong>0.8981</strong> and precision falls from 0.952 to
              0.840 - because a safety net exists to catch: suicide-class recall
              rises from 0.934 to <strong>0.987</strong>. The trade is deliberate and
              documented; a human absorbs the false positives.
            </p>
          </Reveal>
          <Reveal delayMs={120}>
            <span className="label">Reading the metrics</span>
            <p>
              Macro-F1 averages per-class F1 scores, weighting all seven classes
              equally despite a 13.6:1 class imbalance. All figures are point
              estimates from a single experiment - no confidence intervals or
              significance tests were performed, and the repository says so.
            </p>
          </Reveal>
        </div>
        <Reveal delayMs={160}>
          <p className="metrics__src label">Source: artifacts/config.json · docs/MODEL_CARD.md · Step 10 evaluation outputs</p>
        </Reveal>
      </div>
    </section>
  );
}
