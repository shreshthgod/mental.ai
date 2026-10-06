import { Reveal } from "../motion/Reveal";

const LINES = [
  { text: "SEE THE SIGNAL.", cls: "statement__line--accent", cue: null },
  { text: "FROM LANGUAGE", cls: "", cue: "01 · Input" },
  { text: "TO PATTERN", cls: "", cue: "02 · Features" },
  { text: "TO REVIEW", cls: "", cue: "03 · Human" },
];

export function Statement() {
  return (
    <section className="statement" aria-label="Statement">
      <div className="statement__inner">
        {LINES.map((l, i) => (
          <Reveal key={l.text} delayMs={i * 90}>
            <div className={`statement__line ${l.cls}`}>
              <span>{l.text}</span>
              {l.cue && <span className="statement__cue">{l.cue}</span>}
            </div>
          </Reveal>
        ))}
        <Reveal delayMs={380}>
          <p className="statement__big">
            Language contains signals. <strong>Vantage makes them visible</strong> -
            a research pipeline that turns raw text into structured condition and
            urgency signals, always decided on by a human.
          </p>
        </Reveal>
      </div>
    </section>
  );
}
