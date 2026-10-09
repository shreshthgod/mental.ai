import { useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError, type ConfigurationResponse, type PredictResponse } from "../lib/api";
import { analysisView, analysisErrorView, formatProbability } from "../lib/analysisView";
import { clearHistory, historyTitle, loadHistory, mergeAccountHistory, saveScreening, type ScreeningRecord } from "../lib/history";
import { clearCheckIn, loadCheckIn } from "../lib/checkin";
import { currentUserId, onSessionChange, invalidateIfRejected } from "../lib/auth";
import { CheckInFlow } from "../components/screen/CheckInFlow";
import { SystemStatus } from "../components/chrome/SystemStatus";
import { Footer } from "../components/chrome/Footer";
import { runOnDeviceInference, type OnDevicePredictResponse } from "../lib/onDeviceInference";
import { recordSessionVisit } from "../lib/personalization";

type Phase = "idle" | "analyzing" | "success" | "error";
type InferenceMode = "on_device" | "server";
const STAGE_LABELS = ["Language", "Features", "Condition model", "Urgency model", "Review preparation"];
const STAGE_INTERVAL_MS = 520;

export function Screen() {
  const [text, setText] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [stageIdx, setStageIdx] = useState(0);
  const [inferenceMode, setInferenceMode] = useState<InferenceMode>("on_device");
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [error, setError] = useState<ReturnType<typeof analysisErrorView> | null>(null);
  const [validationMsg, setValidationMsg] = useState<string | null>(null);
  const [configuration, setConfiguration] = useState<ConfigurationResponse | null>(null);
  const [configurationError, setConfigurationError] = useState<string | null>(null);
  const [history, setHistory] = useState<ScreeningRecord[]>(() => loadHistory());
  const [historyMessage, setHistoryMessage] = useState<string | null>(null);
  const [deviceMessage, setDeviceMessage] = useState<string | null>(null);
  const [recordedAt, setRecordedAt] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const timersRef = useRef<number[]>([]);
  const [checkedIn, setCheckedIn] = useState(() => loadCheckIn() !== null);

  const clearTimers = () => {
    timersRef.current.forEach(t => clearTimeout(t));
    timersRef.current = [];
  };
  const stopRequest = () => {
    generation.current++;
    clearTimers();
    abortRef.current?.abort();
    abortRef.current = null;
  };
  useEffect(() => {
    const configCtrl = new AbortController();
    const historyCtrl = new AbortController();
    let owner = currentUserId();
    void api.configuration(configCtrl.signal).then(setConfiguration).catch(err => {
      if (!configCtrl.signal.aborted) setConfigurationError(analysisErrorView(err).body);
    });
    if (owner) {
      const requestedOwner = owner;
      void api.screenings(12, historyCtrl.signal).then(data => {
        if (!historyCtrl.signal.aborted && currentUserId() === requestedOwner) setHistory(mergeAccountHistory(data.screenings));
      }).catch(err => {
        if (historyCtrl.signal.aborted || currentUserId() !== requestedOwner) return;
        if (err instanceof ApiError && err.kind === "unauthorized") invalidateIfRejected(err);
        else setHistoryMessage("Account history could not be loaded. Device history is shown when available.");
      });
    }
    const unsubscribe = onSessionChange(() => {
      const next = currentUserId();
      if (next === owner) return;
      owner = next;
      generation.current++;
      timersRef.current.forEach(t => clearTimeout(t));
      timersRef.current = [];
      abortRef.current?.abort();
      historyCtrl.abort();
      setText(""); setResult(null); setError(null); setPhase("idle");
      setValidationMsg(null); setRecordedAt(null); setDeviceMessage(null); setHistoryMessage(null);
      setHistory(loadHistory()); setCheckedIn(loadCheckIn() !== null);
    });
    return () => {
      unsubscribe(); configCtrl.abort(); historyCtrl.abort();
      generation.current++;
      timersRef.current.forEach(t => clearTimeout(t));
      abortRef.current?.abort();
    };
  }, []);

  const startWorkspace = (checkInText: string) => {
    setText(checkInText); setCheckedIn(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const restart = () => {
    stopRequest(); clearCheckIn(); setCheckedIn(false); setText("");
    setResult(null); setError(null); setValidationMsg(null); setRecordedAt(null); setPhase("idle");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  // Python len() counts Unicode code points, unlike JavaScript UTF-16 length.
  const len = Array.from(text).length;
  const limit = configuration?.max_text_length ?? (inferenceMode === "on_device" ? 10000 : undefined);
  const overLimit = limit !== undefined && len > limit;
  const empty = text.trim().length === 0;

  const analyze = async () => {
    if (inferenceMode === "server" && !configuration) {
      setValidationMsg("The server configuration is unavailable. Switch to On-Device mode or try again later.");
      return;
    }
    if (empty) { setValidationMsg("Enter text before running the analysis."); return; }
    if (overLimit) { setValidationMsg(`Text exceeds the ${limit?.toLocaleString() ?? 10000}-character limit.`); return; }
    stopRequest();
    const requestGeneration = generation.current;
    const owner = currentUserId();
    const submittedText = text;
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    const active = () => generation.current === requestGeneration && !ctrl.signal.aborted && currentUserId() === owner;
    setValidationMsg(null); setError(null); setResult(null); setRecordedAt(null); setDeviceMessage(null);
    setPhase("analyzing"); setStageIdx(0);
    // Animated progress indication
    STAGE_LABELS.forEach((_, i) => timersRef.current.push(window.setTimeout(() => {
      if (active()) setStageIdx(i);
    }, i * STAGE_INTERVAL_MS)));
    try {
      let response: PredictResponse;
      if (inferenceMode === "on_device") {
        // Run 100% locally on-device with zero server egress
        response = await runOnDeviceInference(submittedText);
        recordSessionVisit(submittedText);
      } else {
        response = await api.predict(submittedText, ctrl.signal);
      }
      if (!active()) return;
      clearTimers();
      setStageIdx(STAGE_LABELS.length); setResult(response); setPhase("success");
      const saved = saveScreening(submittedText, response);
      setHistory(saved.records);
      setDeviceMessage(
        inferenceMode === "on_device"
          ? "Screening evaluated 100% on-device. Zero text was transmitted to any server."
          : saved.savedToDevice
          ? "Saved on this device for this account."
          : "Device saving failed. The result is available for this visit."
      );
    } catch (err) {
      if (!active()) return;
      clearTimers();
      if (err instanceof ApiError && err.kind === "unauthorized") { invalidateIfRejected(err); return; }
      setError(analysisErrorView(err)); setPhase("error");
    }
  };
  const cancel = () => { stopRequest(); setPhase("idle"); };
  const reset = () => { stopRequest(); setPhase("idle"); setResult(null); setRecordedAt(null); setError(null); };
  const showRecord = (record: ScreeningRecord) => {
    stopRequest();
    if (record.text !== null) setText(record.text);
    setValidationMsg(null); setRecordedAt(record.at); setDeviceMessage(null);
    setResult(record.response); setError(null); setPhase(record.response ? "success" : "idle");
    if (!record.response) setHistoryMessage(`${historyTitle(record)}. Submit text for a new assessment if you wish.`);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const exportHistory = () => {
    try {
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(history, null, 2));
      const downloadAnchor = document.createElement("a");
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", `mental-ai-history-${new Date().toISOString().slice(0, 10)}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    } catch {
      /* ignore */
    }
  };
  const sortedProbs = useMemo(() => result ? Object.entries(result.primary.class_probabilities).sort((a, b) => b[1] - a[1]) : [], [result]);
  const view = result ? analysisView(result) : null;
  const onKeyDown = (e: React.KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && phase !== "analyzing") { e.preventDefault(); void analyze(); }
  };

  return (
    <>
      <main id="main" className="workspace">
        <div className="workspace__inner">
          {!checkedIn ? (
            /* Stage one: the opening check-in. Reached only after signing in. */
            <>
              <div className="workspace__head">
                <div>
                  <h1 className="workspace__title">SCREEN</h1>
                  <p className="workspace__sub">
                    Four short questions, then the workspace. What you write here
                    stays in this browser and becomes the text you can review
                    before anything is analysed.
                  </p>
                </div>
                <SystemStatus />
              </div>
              <CheckInFlow initial={loadCheckIn()} onComplete={startWorkspace} />
            </>
          ) : (
            <>
          <div className="workspace__head">
            <div>
              <h1 className="workspace__title">SCREEN</h1>
              <p className="workspace__sub">
                Review your words, then run a limited support assessment. In
                On-Device Private Mode, your raw text stays 100% inside your browser
                and is never transmitted to any server.
              </p>
            </div>
            <div className="workspace__head-actions">
              <SystemStatus />
              {/* Back to step one of 4, discarding the prefilled text. */}
              <button type="button" className="workspace__restart" onClick={restart}>
                Restart check-in
              </button>
            </div>
          </div>

          <div style={{ display: "flex", gap: 12, marginTop: 28, marginBottom: 10, alignItems: "center", flexWrap: "wrap" }}>
            <span className="label label--accent">Privacy Mode:</span>
            <button
              type="button"
              onClick={() => setInferenceMode("on_device")}
              className={`status ${inferenceMode === "on_device" ? "status--ready" : ""}`}
              style={{ cursor: "pointer", background: inferenceMode === "on_device" ? "var(--bg-raise)" : "transparent" }}
              title="Runs 100% locally in this browser with zero server egress for raw text"
            >
              🔒 On-Device Private Mode (Offline-Ready)
            </button>
            <button
              type="button"
              onClick={() => setInferenceMode("server")}
              className={`status ${inferenceMode === "server" ? "status--ready" : ""}`}
              style={{ cursor: "pointer", background: inferenceMode === "server" ? "var(--bg-raise)" : "transparent" }}
              title="Runs inference via the authenticated server endpoint"
            >
              ☁️ Cloud-Assisted Mode
            </button>
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
                {len.toLocaleString()} / {limit?.toLocaleString() ?? "limit unavailable"}
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
              aria-describedby="screen-hint"
            />
            <div className="screen-form__foot">
              <p id="screen-hint" className="label">
                Ctrl + Enter to analyze
              </p>
              <div style={{ display: "flex", gap: 18, alignItems: "center" }}>
                {(validationMsg || configurationError) && <p className="screen-form__error" role="alert">{validationMsg || configurationError}</p>}
                <button type="submit" className="cta cta--primary" disabled={phase === "analyzing" || empty || overLimit || (inferenceMode === "server" && !configuration)}>
                  Analyze <span className="cta__arrow" aria-hidden="true">→</span>
                </button>
              </div>
            </div>
          </form>

          {history.length > 0 && (
            <section className="history" aria-label="Previous screenings">
              <div className="history__head">
                <p className="label label--accent">Previous screenings</p>
                <div style={{ display: "flex", gap: 12 }}>
                  <button
                    type="button"
                    className="history__clear"
                    onClick={exportHistory}
                    title="Export local screening records as a JSON file"
                  >
                    Export JSON
                  </button>
                  <button
                    type="button"
                    className="history__clear"
                    onClick={() => {
                      const cleared = clearHistory();
                      setHistory(cleared ? [] : loadHistory());
                      setHistoryMessage(cleared ? "Device history cleared. Account history remains available after reload." : "Device history could not be cleared.");
                    }}
                  >
                    Clear device history
                  </button>
                </div>
              </div>
              <ul className="history__list">
                {history.map((r) => (
                  <li key={r.id}>
                    <button
                      type="button"
                      className="history__row"
                      onClick={() => showRecord(r)}
                      title="View the recorded support result; available original text is restored"
                    >
                      <span className="history__date num">
                        {new Date(r.at).toLocaleString(undefined, {
                          day: "2-digit",
                          month: "short",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                      <span className="history__cond">{historyTitle(r)}</span>
                      <span
                        className={`history__urg ${
                          r.response && analysisView(r.response).urgent ? "history__urg--flag" : ""
                        }`}
                      >
                        {r.response ? analysisView(r.response).capabilityTitle : "Unassessed"}
                      </span>
                      <span className="history__preview">
                        {r.text?.slice(0, 96) ?? "Original text is not returned by account history"}
                        {r.text !== null && r.text.length > 96 ? "…" : ""}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {historyMessage && <p className="history__date" role="status">{historyMessage}</p>}

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
                Your text is being assessed. These animated stages show that
                the request is in progress; they do not confirm component availability.
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
                  Clear device history
                </button>
              </div>
            </div>
          )}

          {phase === "success" && result && view && (
            <section className="results" aria-live="polite" aria-label="Analysis result">
              <div className="results__head">
                <h2 className="results__title">{recordedAt === null ? "Support result" : "Recorded support result"}</h2>
                <p className="results__meta">
                  request {result.request_id} · {recordedAt !== null ? new Date(recordedAt).toLocaleString() : view.savingMessage}
                </p>
              </div>

              <div className="results__grid">
                <div className="results__cell">
                  <p className="label label--accent">Support state</p>
                  <p className="results__class">{view.title}</p>
                  <p className="results__class-sub">
                    {result.safety.summary} Subject: {view.subject.replace(/_/g, " ")};
                    context: {view.temporalContext}; immediacy: {view.immediacy.replace(/_/g, " ")}.
                    Raw research prediction: {view.primaryLabel}. These classifier
                    probabilities are not a clinical risk estimate.
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
                  <p className="label label--accent">Assessment capability</p>
                  <p className="results__class">{view.capabilityTitle}</p>
                  <p className="results__class-sub">
                    {view.capabilityMessage} Raw urgency model: {view.urgencyLabel}.
                    Threshold: {formatProbability(view.urgencyThreshold)}.
                  </p>
                  {view.urgencyProbability !== null ? (
                    <div className="urgency-meter" role="img" aria-label={`Raw urgency model probability ${formatProbability(view.urgencyProbability)}, threshold ${formatProbability(view.urgencyThreshold)}`}>
                      <div className="urgency-meter__track">
                        <span className={`urgency-meter__fill ${result.urgency.flagged ? "urgency-meter__fill--flag" : ""}`} style={{ width: `${view.urgencyProbability * 100}%` }} />
                        <span className="urgency-meter__thresh" style={{ left: `${view.urgencyThreshold * 100}%` }} title={`decision threshold ${view.urgencyThreshold}`} />
                      </div>
                      <div className="urgency-meter__legend">
                        <span className="num">p = {view.urgencyProbability.toFixed(3)}</span>
                        <span className="num">threshold = {view.urgencyThreshold}</span>
                      </div>
                    </div>
                  ) : <p className="urgency-meter__legend">Raw urgency probability: Unavailable</p>}

                </div>

                {(result as OnDevicePredictResponse).emotion?.emotions?.length > 0 && (
                  <div className="results__cell" style={{ gridColumn: "1 / -1", marginTop: 12 }}>
                    <p className="label label--accent">Multi-Label Emotional Cues</p>
                    <p className="results__class-sub">
                      {(result as OnDevicePredictResponse).emotion.clinical_distinction_advisory}
                    </p>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 10, margin: "14px 0" }}>
                      {(result as OnDevicePredictResponse).emotion.emotions.map((em) => (
                        <span
                          key={em.name}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 6,
                            background: "var(--bg-raise)",
                            border: "1px solid var(--line-2)",
                            borderRadius: 3,
                            padding: "6px 12px",
                            fontSize: 13,
                            fontFamily: "var(--font-mono)",
                          }}
                        >
                          <strong style={{ textTransform: "capitalize", color: "var(--ink)" }}>{em.name}</strong>
                          <span style={{ color: "var(--ink-3)" }}>{(em.confidence * 100).toFixed(0)}%</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {(result as OnDevicePredictResponse).privacy_guarantee && (
                <div className="results__caveat" style={{ borderColor: "rgba(77, 159, 255, 0.4)" }}>
                  <p className="label label--accent">On-Device Privacy Guarantee</p>
                  <p>{(result as OnDevicePredictResponse).privacy_guarantee}</p>
                </div>
              )}

              {result.provenance_caveat && (
                <div className="results__caveat">
                  <p className="label">Provenance</p>
                  <p>{result.provenance_caveat}</p>
                </div>
              )}

              <aside className="support" aria-label="Support guidance">
                <p className="label label--accent">Support guidance</p>
                <p className="support__lead">{view.supportAction}</p>
                <p className="support__note">
                  {view.capabilityMessage} {view.savingMessage} {deviceMessage}
                  {result.safety.review_recommended ? " Human review is recommended; nobody has been notified by this screening." : ""}
                </p>
              </aside>

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
            </>
          )}
        </div>
      </main>
      <Footer />
    </>
  );
}
