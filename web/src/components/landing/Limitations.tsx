import { Link } from "react-router-dom";
import { Reveal } from "../motion/Reveal";

const LIMITS = [
  {
    h: "Proxy labels, not clinical truth",
    p: "Both models are trained on subreddit-of-origin labels from public datasets (Kaggle / Pushshift). No label was verified by a clinician.",
  },
  {
    h: "Limited assessment and support",
    p: "The app returns support guidance and may recommend review. Nobody is notified; no reviewer or emergency service is contacted.",
  },
  {
    h: "Text only, English-skewed",
    p: "Phase 1 analyzes written text only. No speech, no audio, no multilingual validation - and 51.6% of one source overlaps another.",
  },
  {
    h: "Point estimates",
    p: "Historical metrics are point estimates without confidence intervals. The urgency threshold was selected using the test split; independent release validation is unavailable.",
  },
];

export function Limitations() {
  return (
    <section id="limits" className="section" aria-labelledby="limits-h">
      <div className="section__inner">
        <Reveal>
          <p className="label label--accent">Honesty discipline</p>
        </Reveal>
        <Reveal delayMs={90}>
          <h2 id="limits-h" className="limits__statement" style={{ marginTop: 18 }}>
            NOT A DIAGNOSIS. <span className="neg">NOT A CLINICAL DECISION.</span>{" "}
            NOT A REPLACEMENT FOR PROFESSIONAL CARE.
          </h2>
        </Reveal>
        <Reveal delayMs={160}>
          <p className="statement__big" style={{ marginTop: 26 }}>
            MENTAL.AI is a <strong>research system</strong> for screening
            language-derived signals and presenting limited support guidance.
          </p>
        </Reveal>

        <div className="limits__grid">
          {LIMITS.map((l, i) => (
            <Reveal key={l.h} className="limits__item" delayMs={i * 90}>
              <h3>{l.h}</h3>
              <p>{l.p}</p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

export function ClosingCta() {
  return (
    <section className="closing" aria-labelledby="closing-h">
      <div className="closing__inner">
        <Reveal>
          <p className="label label--accent">Run the instrument</p>
        </Reveal>
        <Reveal delayMs={90}>
          <h2 id="closing-h" className="closing__title">
            Submit language.
            <br />
            Read the signals.
          </h2>
        </Reveal>
        <Reveal delayMs={170}>
          <div className="closing__row">
            <Link to="/screen" className="cta cta--primary">
              Start screening <span className="cta__arrow" aria-hidden="true">→</span>
            </Link>
            <Link to="/research" className="cta cta--ghost">
              Read the methodology
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
