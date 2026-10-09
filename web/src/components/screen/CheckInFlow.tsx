/**
 * Opening check-in for the screening workspace.
 *
 * Four short prompts, one screen each, assembled into a single plain-text
 * check-in and handed to the workspace as prefill. Nothing is analysed here and
 * nothing is transmitted: the answers only reach this browser's storage until
 * the user explicitly submits text to POST /predict.
 *
 * This is the entry point of the screening flow, so it runs behind
 * authentication. Asking someone to describe how they feel is the first real
 * task of the product, and it belongs after sign-in rather than in front of it.
 *
 * Copy and structure are carried over unchanged from the flow that used to sit
 * inside the sign-in page; only its home and its completion callback changed.
 */
import { useEffect, useRef, useState, type FormEvent } from "react";
import { checkInToText, saveCheckIn } from "../../lib/checkin";
import { generateWelcomeGreeting, clearRememberedThemes, type WelcomeGreeting } from "../../lib/personalization";

type StepId = "greeting" | "feeling" | "weighing" | "today";

const STEPS: StepId[] = ["greeting", "feeling", "weighing", "today"];

interface Step {
  label: string;
  /** Compact form, used to label each answer in the recap. */
  short: string;
  prompt: string;
  placeholder: string;
  optional?: boolean;
}

const STEP_COPY: Record<StepId, Step> = {
  greeting: {
    label: "Before anything else",
    short: "Opening",
    prompt: "How are you today?",
    placeholder: "in your own words, however much or little",
  },
  feeling: {
    label: "Right now",
    short: "Feeling",
    prompt: "What is the strongest thing you feel?",
    placeholder: "e.g. exhausted, anxious, numb, hopeful",
  },
  weighing: {
    label: "Lately",
    short: "On my mind",
    prompt: "What has been taking up the most room in your head?",
    placeholder: "e.g. work, family, the future, nothing in particular",
  },
  today: {
    label: "Today",
    short: "Today",
    prompt: "What happened today, or what would you like to happen?",
    placeholder: "anything at all, including nothing",
    optional: true,
  },
};

interface Props {
  /** Called with the flattened check-in text once the last step is submitted. */
  onComplete: (text: string, answers: Record<string, string>) => void;
  /** Answers recovered from a previous visit, used to prefill the fields. */
  initial?: Record<string, string> | null;
  /** Optional user name for personalization */
  userName?: string;
}

export function CheckInFlow({ onComplete, initial, userName }: Props) {
  const [stepIndex, setStepIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>(initial ?? {});
  const [greeting, setGreeting] = useState<WelcomeGreeting>(() => generateWelcomeGreeting(userName));
  const headingRef = useRef<HTMLParagraphElement>(null);

  const stepId = STEPS[stepIndex];
  const copy = STEP_COPY[stepId];
  const isLast = stepIndex === STEPS.length - 1;

  // Move focus to the new prompt so keyboard and screen reader users land on
  // the question that just changed rather than staying on a stale control.
  useEffect(() => {
    headingRef.current?.focus();
  }, [stepIndex]);

  const setAnswer = (value: string) =>
    setAnswers((prev) => ({ ...prev, [stepId]: value }));

  const goBack = () => setStepIndex((i) => Math.max(0, i - 1));

  const handleStartFresh = () => {
    clearRememberedThemes();
    setGreeting(generateWelcomeGreeting(userName));
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!isLast) {
      setStepIndex((i) => Math.min(STEPS.length - 1, i + 1));
      return;
    }
    saveCheckIn(answers);
    onComplete(checkInToText(answers), answers);
  };

  const entered = Object.values(answers).filter((v) => v.trim().length > 0).length;

  return (
    <section className="checkin" aria-label="Check-in">
      <div className="checkin__head">
        <p className="label label--accent">MENTAL.AI</p>
        <p className="label">
          Step {stepIndex + 1} of {STEPS.length}
        </p>
      </div>

      {stepIndex === 0 && (
        <aside
          style={{
            marginBottom: 28,
            padding: "18px 20px",
            background: "var(--bg-raise)",
            border: "1px solid var(--line-2)",
            borderRadius: 3,
            lineHeight: 1.6,
          }}
          aria-label="Welcome reflection"
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: 10 }}>
            <p className="label label--accent" style={{ margin: 0 }}>
              {greeting.headline}
            </p>
            {greeting.hasPastContext && (
              <button
                type="button"
                onClick={handleStartFresh}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--ink-3)",
                  fontSize: 11,
                  fontFamily: "var(--font-mono)",
                  cursor: "pointer",
                  textDecoration: "underline",
                  padding: 0,
                }}
                title="Clears remembered context from previous visits"
              >
                Start completely fresh today
              </button>
            )}
          </div>
          <p style={{ margin: "10px 0 0", color: "var(--ink-2)", fontSize: 14.5 }}>
            {greeting.subtext}
          </p>
        </aside>
      )}

      <form className="checkin__form" onSubmit={submit}>
        <div className="checkin__field">
          <span className="label">{copy.label}</span>
          <p className="checkin__prompt" ref={headingRef} tabIndex={-1}>
            {copy.prompt}
          </p>
          <textarea
            className="checkin__input"
            value={answers[stepId] ?? ""}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder={copy.placeholder}
            rows={3}
            autoFocus
            spellCheck
            aria-describedby="checkin-note"
          />
        </div>

        <div className="checkin__actions">
          <button
            type="button"
            className="checkin__back"
            onClick={goBack}
            disabled={stepIndex === 0}
          >
            Back
          </button>
          <button type="submit" className="cta cta--primary checkin__submit">
            {isLast ? "Open the workspace" : "Continue"}
            <span className="cta__arrow" aria-hidden="true">
              →
            </span>
          </button>
        </div>

        <p className="checkin__note" id="checkin-note">
          {entered > 0
            ? `${entered} of ${STEPS.length} notes written. `
            : ""}
          This stays in your browser. Nothing is analysed until you choose to
          send it on from the screening page.
        </p>
      </form>
    </section>
  );
}