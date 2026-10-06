import { useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError, MAX_TEXT_LENGTH, type PredictResponse } from "../lib/api";
import { SystemStatus } from "../components/chrome/SystemStatus";
import { Footer } from "../components/chrome/Footer";

type Phase = "idle" | "analyzing" | "success" | "error";

const STAGE_LABELS = ["Language", "Features", "Condition model", "Urgency model", "Review preparation"];
const STAGE_INTERVAL_MS = 520;

interface ErrorState {
  title: string;
  body: string;
  meta?: string;
}

function errorState(err: unknown): ErrorState {
  if (err instanceof ApiError) {
    if (err.kind === "unavailable")
      return {
        title: "Analysis unavailable",
        body: "The screening service could not be reached. Start the API server and try again.",
        meta: err.requestId ? `request ${err.requestId}` : "no response",
      };
    if (err.kind === "timeout")
      return { title: "Analysis timed out", body: "The request exceeded the time limit. The service may be under load.", meta: err.requestId ? `request ${err.requestId}` : undefined };
    if (err.kind === "validation")
      return { title: "Rejected by the service", body: err.message, meta: err.requestId ? `request ${err.requestId}` : undefined };
    return { title: "Analysis failed", body: err.message, meta: err.requestId ? `request ${err.requestId}` : undefined };
  }
  if (err instanceof DOMException && err.name === "AbortError")
    return { title: "Analysis cancelled", body: "The request was cancelled before a result was returned." };
  return { title: "Analysis failed", body: "An unexpected error occurred." };
}

export function Screen() {
  const [text, setText] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [stageIdx, setStageIdx] = useState(0);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [error, setError] = useState<ErrorState | null>(null);
  const [validationMsg, setValidationMsg] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const timersRef = useRef<number[]>([]);

  const len = text.length;
  const overLimit = len > MAX_TEXT_LENGTH;
  const empty = text.trim().length === 0;

  const clearTimers = () => {
    timersRef.current.forEach((t) => clearTimeout(t));
    timersRef.current = [];
  };

  useEffect(() => () => {
    clearTimers();
    abortRef.current?.abort();
  }, []);

  const analyze = async () => {
    if (empty) {
      setValidationMsg("Enter text before running the analysis.");
      return;
    }
    if (overLimit) {
      setValidationMsg(`Text exceeds the ${MAX_TEXT_LENGTH.toLocaleString()}-character service limit.`);
      return;
    }
    setValidationMsg(null);
    setError(null);
    setResult(null);
    setPhase("analyzing");
    setStageIdx(0);

    // Visual staged sequence - cosmetic only; the backend exposes a single
    // synchronous /predict and does not report per-stage progress.
    STAGE_LABELS.forEach((_, i) => {
      timersRef.current.push(window.setTimeout(() => setStageIdx(i), i * STAGE_INTERVAL_MS));
    });

    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      const res = await api.predict(text, ctrl.signal);
      // Let the sequence finish its visible run for coherence, then reveal.
      const elapsed = stageIdxRef.current * STAGE_INTERVAL_MS;
      const remaining = Math.max(0, STAGE_LABELS.length * STAGE_INTERVAL_MS - elapsed);
      timersRef.current.push(
        window.setTimeout(() => {
          setStageIdx(STAGE_LABELS.length);
          setResult(res);
          setPhase("success");
        }, Math.min(remaining, 700))
      );
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        setPhase("idle");
        return;
      }
      clearTimers();
      setError(errorState(err));
      setPhase("error");
    }
  };

  // Track the stage for elapsed computation inside the async path.
  const stageIdxRef = useRef(0);
  useEffect(() => {
    stageIdxRef.current = stageIdx;
  }, [stageIdx]);

  const cancel = () => {
    clearTimers();
    abortRef.current?.abort();
    setPhase("idle");
  };

  const reset = () => {
    clearTimers();
    abortRef.current?.abort();
    setPhase("idle");
    setResult(null);
    setError(null);
  };

  const sortedProbs = useMemo(() => {
    if (!result) return [];
    return Object.entries(result.primary.class_probabilities).sort((a, b) => b[1] - a[1]);
  }, [result]);

  const onKeyDown = (e: React.KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && phase !== "analyzing") {
      e.preventDefault();
      void analyze();
    }
  };

  return (
    <>
      <main id="main" className="workspace">
        <div className="workspace__inner">
          <div className="workspace__head">
            <div>
              <h1 className="workspace__title">SCREEN</h1>
              <p className="workspace__sub">
                Submit language for signal analysis. The text is sent to the
                Vantage inference service and answered by the deployed research
                models - nothing is stored by this interface.
              </p>
            </div>
            <SystemStatus />
          </div>

          <form
            className="screen-form"
            onSubmit={(e) => {
              e.preventDefault();
              if (phase !== "analyzing") void analyze();
            }}
          >
            <div className="screen-form__label">
              <label htmlFor="screen-input" className="label label--accent">
                Text sample
              </label>
              <span className={`screen-form__count ${overLimit ? "screen-form__count--over" : ""}`}>
                {len.toLocaleString()} / {MAX_TEXT_LENGTH.toLocaleString()}
              </span>
            </div>
            <textarea
              id="screen-input"
              className="screen-form__area"
              placeholder="Paste or enter text…"
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={onKeyDown}
              disabled={phase === "analyzing"}
              maxLength={MAX_TEXT_LENGTH + 1000}
              aria-describedby="screen-hint"
            />
            <div className="screen-form__foot">
              <p id="screen-hint" className="label">
                Ctrl + Enter to analyze
              </p>
              <div style={{ display: "flex", gap: 18, alignItems: "center" }}>
                {validationMsg && <p className="screen-form__error" role="alert">{validationMsg}</p>}
                <button type="submit" className="cta cta--primary" disabled={phase === "analyzing" || empty || overLimit}>
                  Analyze <span className="cta__arrow" aria-hidden="true">→</span>
                </button>
              </div>
            </div>
          </form>

          {phase === "analyzing" && (
            <div className="analysis" aria-live="polite">
              <div className="analysis__title">
                <span className="analysis__spinner" aria-hidden="true" />
                <p className="label label--accent">Analyzing</p>
              </div>
              <ol className="analysis__stages">
                {STAGE_LABELS.map((s, i) => {
                  const state = i < stageIdx ? "done" : i === stageIdx ? "active" : "pending";
                  return (
                    <li key={s} className={`analysis__stage analysis__stage--${state}`}>
                      <span className="analysis__stage-num">{String(i + 1).padStart(2, "0")}</span>
                      {s}
                      <span className="analysis__stage-state">
                        {state === "done" ? "done" : state === "active" ? "running" : ""}
                      </span>
                    </li>
                  );
                })}
              </ol>
              <p className="analysis__note">
                The staged view above is a visual representation while the single
                inference request is in flight - the service does not stream
                per-stage progress.
              </p>
              <button type="button" className="analysis__cancel" onClick={cancel}>
                Cancel
              </button>
            </div>
          )}

          {phase === "error" && error && (
            <div className="error-panel" role="alert">
              <p className="error-panel__title">{error.title}</p>
              <p className="error-panel__body">{error.body}</p>
              {error.meta && <p className="error-panel__meta">{error.meta}</p>}
              <div className="error-panel__actions">
                <button type="button" className="cta" onClick={() => void analyze()}>
                  Retry
                </button>
                <button type="button" className="cta cta--ghost" onClick={reset}>
                  Clear
                </button>
              </div>
            </div>
          )}

          {phase === "success" && result && (
            <section className="results" aria-live="polite" aria-label="Analysis result">
              <div className="results__head">
                <h2 className="results__title">Analysis complete</h2>
                <p className="results__meta">
                  request {result.request_id} · service v{result.service_version}
                </p>
              </div>

              <div className="results__grid">
                <div className="results__cell">
                  <p className="label label--accent">Condition signal</p>
                  <p className="results__class">{result.primary.predicted_class}</p>
                  <p className="results__class-sub">
                    Predicted class from the 7-class condition model. Distribution
                    below is the model's own class probabilities.
                  </p>
                  <div className="probs" role="img" aria-label={`Class probabilities: ${sortedProbs.map(([k, v]) => `${k} ${(v * 100).toFixed(1)}%`).join(", ")}`}>
                    {sortedProbs.map(([name, p], i) => (
                      <div key={name} className={`probs__row ${i === 0 ? "probs__row--top" : ""}`}>
                        <span className="probs__name">{name}</span>
                        <span className="probs__track">
                          <span className="probs__fill" style={{ width: `${(p * 100).toFixed(1)}%` }} />
                        </span>
                        <span className="probs__val num">{(p * 100).toFixed(1)}%</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="results__cell">
                  <p className="label label--accent">Urgency signal</p>
                  <p className={`results__class ${result.urgency.flagged ? "results__class--warn" : "results__class--ok"}`}>
                    {result.urgency.flagged ? "Elevated" : "Not elevated"}
                  </p>
                  <p className="results__class-sub">
                    {result.urgency.flagged
                      ? "Human review recommended. The independent urgency safety net flagged this text at the deployed 0.15 recall-first threshold."
                      : "No elevated urgency signal detected at the deployed 0.15 threshold."}
                  </p>
                  <div className="urgency-meter" role="img" aria-label={`Urgency probability ${(result.urgency.suicide_probability * 100).toFixed(1)} percent, threshold ${(result.urgency.decision_threshold_used * 100).toFixed(0)} percent`}>
                    <div className="urgency-meter__track">
                      <span
                        className={`urgency-meter__fill ${result.urgency.flagged ? "urgency-meter__fill--flag" : ""}`}
                        style={{ width: `${(result.urgency.suicide_probability * 100).toFixed(1)}%` }}
                      />
                      <span
                        className="urgency-meter__thresh"
                        style={{ left: `${(result.urgency.decision_threshold_used * 100).toFixed(1)}%` }}
                        title={`decision threshold ${result.urgency.decision_threshold_used}`}
                      />
                    </div>
                    <div className="urgency-meter__legend">
                      <span className="num">p = {result.urgency.suicide_probability.toFixed(3)}</span>
                      <span className="num">threshold = {result.urgency.decision_threshold_used}</span>
                    </div>
                  </div>
                </div>
              </div>

              {result.provenance_caveat && (
                <div className="results__caveat">
                  <p className="label">Provenance</p>
                  <p>{result.provenance_caveat}</p>
                </div>
              )}

              <div className="results__actions">
                <button type="button" className="cta" onClick={reset}>
                  New analysis
                </button>
              </div>

              <div className="results__disclaimer">
                <strong>Research screening result.</strong> These predictions are
                generated by machine-learning models trained on public datasets
                with proxy labels. They are not clinical diagnoses and should not
                replace professional assessment.
              </div>
            </section>
          )}
        </div>
      </main>
      <Footer />
    </>
  );
}
