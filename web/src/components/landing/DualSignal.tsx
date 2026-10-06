import { Reveal } from "../motion/Reveal";

/**
 * Dual-signal architecture - one language input branching into the condition
 * model and the independent urgency safety net, converging on human review.
 * SVG with CSS-driven signal flow (offset-path); disabled under reduced motion.
 */
export function DualSignal() {
  return (
    <section className="section" aria-labelledby="dual-h">
      <div className="section__inner">
        <div className="section__head">
          <div>
            <Reveal>
              <p className="label label--accent">Analysis engine</p>
            </Reveal>
            <Reveal delayMs={80}>
              <h2 id="dual-h" className="section__title">
                Two signals. One decision - made by a human.
              </h2>
            </Reveal>
          </div>
          <Reveal delayMs={160}>
            <p className="label">Fig. 01 · Dual-signal architecture</p>
          </Reveal>
        </div>

        <Reveal delayMs={120}>
          <svg className="dual__figure" viewBox="0 0 1200 440" role="img"
            aria-label="Diagram: language flows into two independent models - a seven-class condition classifier and a binary urgency safety net - both converging to human review.">
            <defs>
              <radialGradient id="nodeGlow">
                <stop offset="0%" stopColor="#7b5cff" stopOpacity="0.9" />
                <stop offset="100%" stopColor="#7b5cff" stopOpacity="0" />
              </radialGradient>
              <radialGradient id="nodeGlowBlue">
                <stop offset="0%" stopColor="#4d9fff" stopOpacity="0.9" />
                <stop offset="100%" stopColor="#4d9fff" stopOpacity="0" />
              </radialGradient>
            </defs>

            {/* paths */}
            <path id="p-in-cond" d="M 170 220 C 300 220, 340 110, 520 110" fill="none" stroke="rgba(123,92,255,0.4)" strokeWidth="1" />
            <path id="p-in-urg" d="M 170 220 C 300 220, 340 330, 520 330" fill="none" stroke="rgba(77,159,255,0.4)" strokeWidth="1" />
            <path id="p-cond-rev" d="M 700 110 C 860 110, 890 220, 1010 220" fill="none" stroke="rgba(123,92,255,0.4)" strokeWidth="1" />
            <path id="p-urg-rev" d="M 700 330 C 860 330, 890 220, 1010 220" fill="none" stroke="rgba(77,159,255,0.4)" strokeWidth="1" />

            {/* traveling signals */}
            <circle r="2.6" fill="#b7a6ff" className="dual__signal" style={{ offsetPath: "path('M 170 220 C 300 220, 340 110, 520 110')" }} />
            <circle r="2.6" fill="#8fc2ff" className="dual__signal dual__signal--b" style={{ offsetPath: "path('M 170 220 C 300 220, 340 330, 520 330')" }} />
            <circle r="2.2" fill="#b7a6ff" className="dual__signal dual__signal--c" style={{ offsetPath: "path('M 700 110 C 860 110, 890 220, 1010 220')" }} />
            <circle r="2.2" fill="#8fc2ff" className="dual__signal dual__signal--d" style={{ offsetPath: "path('M 700 330 C 860 330, 890 220, 1010 220')" }} />

            {/* nodes */}
            <g>
              <circle cx="120" cy="220" r="26" fill="url(#nodeGlow)" opacity="0.35" className="dual__pulse" />
              <circle cx="120" cy="220" r="4" fill="#f4f4f6" />
              <text x="120" y="262" textAnchor="middle" className="dual__svg-label">LANGUAGE</text>
            </g>
            <g>
              <circle cx="610" cy="110" r="34" fill="url(#nodeGlow)" opacity="0.4" className="dual__pulse dual__pulse--b" />
              <circle cx="610" cy="110" r="5" fill="#b7a6ff" />
              <text x="610" y="70" textAnchor="middle" className="dual__svg-label">CONDITION SIGNAL</text>
              <text x="610" y="146" textAnchor="middle" className="dual__svg-sub">7-class classifier</text>
            </g>
            <g>
              <circle cx="610" cy="330" r="34" fill="url(#nodeGlowBlue)" opacity="0.4" className="dual__pulse dual__pulse--c" />
              <circle cx="610" cy="330" r="5" fill="#8fc2ff" />
              <text x="610" y="296" textAnchor="middle" className="dual__svg-label">URGENCY SIGNAL</text>
              <text x="610" y="368" textAnchor="middle" className="dual__svg-sub">independent safety net</text>
            </g>
            <g>
              <circle cx="1060" cy="220" r="30" fill="url(#nodeGlow)" opacity="0.35" className="dual__pulse dual__pulse--d" />
              <circle cx="1060" cy="220" r="4.5" fill="#f4f4f6" />
              <text x="1060" y="262" textAnchor="middle" className="dual__svg-label">HUMAN REVIEW</text>
            </g>
          </svg>
        </Reveal>

        <div className="dual__legend">
          <Reveal className="dual__cell" delayMs={100}>
            <h3><span className="label label--accent">Track 01</span> Condition signal</h3>
            <p>
              A 7-class XGBoost classifier over a 1,538-dimension feature space -
              38 handcrafted linguistic signals plus chi²-selected TF-IDF terms -
              assigning the text to one of seven condition patterns.
            </p>
          </Reveal>
          <Reveal className="dual__cell" delayMs={200}>
            <h3><span className="label label--accent">Track 02</span> Urgency signal</h3>
            <p>
              An independent logistic-regression safety net over the full 30,000-term
              TF-IDF space, deployed at a 0.15 decision threshold that deliberately
              favors recall. Urgency is not one of the seven classes - it is a
              separate routing signal for human review.
            </p>
          </Reveal>
        </div>
        <Reveal delayMs={240}>
          <p className="dual__note">Both tracks are trained on public proxy-label data · outputs are screening signals, not diagnoses</p>
        </Reveal>
      </div>
    </section>
  );
}
