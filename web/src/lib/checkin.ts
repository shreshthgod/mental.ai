/**
 * Check-in notes captured by the sign-in flow.
 *
 * Browser-local only. The sign-in page collects them so the user starts the
 * screening workspace with their own words already in the box; nothing is
 * transmitted until the user explicitly submits text to POST /predict.
 */
const KEY = "mental.ai.checkin";

export interface CheckIn {
  /** key: greeting | feeling | weighing | today */
  answers: Record<string, string>;
  at: number;
}

export function saveCheckIn(answers: Record<string, string>): void {
  const clean = Object.fromEntries(
    Object.entries(answers).filter(([, v]) => typeof v === "string" && v.trim().length > 0)
  );
  if (Object.keys(clean).length === 0) {
    clearCheckIn();
    return;
  }
  try {
    localStorage.setItem(KEY, JSON.stringify({ answers: clean, at: Date.now() }));
  } catch {
    /* storage unavailable: prefill is simply skipped */
  }
}

export function loadCheckIn(): Record<string, string> | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<CheckIn>;
    if (!parsed?.answers || typeof parsed.answers !== "object") return null;
    const entries = Object.entries(parsed.answers).filter(
      ([, v]) => typeof v === "string" && v.trim().length > 0
    );
    return entries.length > 0 ? Object.fromEntries(entries) : null;
  } catch {
    return null;
  }
}

export function clearCheckIn(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}

/** Flatten the check-in into the plain text the screening model expects. */
export function checkInToText(answers: Record<string, string>): string {
  const ORDER: Array<[string, string]> = [
    ["feeling", "Today I feel"],
    ["weighing", "What has been on my mind"],
    ["today", "Today"],
  ];
  const lines: string[] = [];
  const opening = answers.greeting?.trim();
  if (opening) lines.push(opening);
  for (const [key, prefix] of ORDER) {
    const value = answers[key]?.trim();
    if (value) lines.push(`${prefix}: ${value}`);
  }
  return lines.join("\n");
}