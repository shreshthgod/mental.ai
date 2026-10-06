import { useSystemStatus } from "../../lib/status";

const STATUS_TEXT = {
  checking: "Checking",
  ready: "Ready",
  degraded: "Degraded",
  unavailable: "Offline",
} as const;

export function SystemStatus({ compact = false }: { compact?: boolean }) {
  const state = useSystemStatus();
  const cls =
    state === "ready" ? "status--ready" : state === "checking" ? "status--checking" : "status--down";
  return (
    <span className={`status ${cls}`} role="status" aria-live="polite">
      <span className="status__dot" aria-hidden="true" />
      {compact ? STATUS_TEXT[state] : `Vantage engine · ${STATUS_TEXT[state]}`}
    </span>
  );
}
