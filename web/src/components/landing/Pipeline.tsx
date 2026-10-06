import { useInView } from "../../lib/motion";
import { Reveal } from "../motion/Reveal";

const STAGES = [
  { num: "01", name: "Input", desc: "Raw language - unstructured text exactly as written." },
  { num: "02", name: "Clean", desc: "Encoding fixes, deduplication, garbage-row filtering." },
  { num: "03", name: "Preprocess", desc: "Tokenization and lemmatization with failure-safe handling." },
  { num: "04", name: "Features", desc: "38 handcrafted signals + 30k TF-IDF terms, chi²-selected." },
  { num: "05", name: "Models", desc: "Two independent classifiers - condition and urgency." },
  { num: "06", name: "Review", desc: "Signals surfaced for human interpretation. Never autonomous." },
];

export function Pipeline() {
  const [ref, inView] = useInView<HTMLDivElement>(0.25);
  return (
    <section className="section" aria-labelledby="pipeline-h">
      <div className="section__inner">
        <div className="section__head">
          <div>
            <Reveal>
              <p className="label label--accent">How it works</p>
            </Reveal>
            <Reveal delayMs={80}>
              <h2 id="pipeline-h" className="section__title">
                From language to a reviewable signal.
              </h2>
            </Reveal>
          </div>
          <Reveal delayMs={160}>
            <p className="label">12-stage research pipeline</p>
          </Reveal>
        </div>

        <div ref={ref} className={`pipeline ${inView ? "pipeline--in" : ""}`}>
          <div className="pipeline__track">
            <span className="pipeline__spine" aria-hidden="true" />
            {STAGES.map((s, i) => (
              <div key={s.num} className="pipeline__stage" style={{ ["--pd" as string]: `${200 + i * 130}ms` }}>
                <p className="pipeline__num">{s.num}</p>
                <p className="pipeline__name">{s.name}</p>
                <p className="pipeline__desc">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
