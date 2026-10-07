import { Link } from "react-router-dom";
import { Reveal } from "../motion/Reveal";

const LIMITS = [
  {
    h: "Proxy labels, not clinical truth",
    p: "Both models are trained on subreddit-of-origin labels from public datasets (Kaggle / Pushshift). No label was verified by a clinician.",
  },
  {
    h: "Human review is the design, not a caveat",
    p: "The urgency layer routes text to people. It contacts no emergency service, triggers no automated intervention, and decides nothing alone.",
  },
  {
    h: "Text only, English-skewed",
    p: "Phase 1 analyzes written text only. No speech, no audio, no multilingual validation - and 51.6% of one source overlaps another.",
  },
  {
    h: "Point estimates",
    p: "Reported metrics come from a single run on a held-out split, without confidence intervals or significance testing.",
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
            language-derived signals and supporting human review.
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
