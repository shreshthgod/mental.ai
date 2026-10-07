export interface ScreeningRecord {
  id: string;
  at: number;
  text: string;
  condition: string;
  conditionProb: number;
  urgencyFlagged: boolean;
  urgencyProb: number;
}

const KEY = "mental.ai.history";
const MAX_ENTRIES = 12;

export function loadHistory(): ScreeningRecord[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (e): e is ScreeningRecord =>
        !!e &&
        typeof e === "object" &&
        typeof (e as ScreeningRecord).id === "string" &&
        typeof (e as ScreeningRecord).text === "string"
    );
  } catch {
    return [];
  }
}

export function saveScreening(record: Omit<ScreeningRecord, "at">): ScreeningRecord[] {
  const entry: ScreeningRecord = { ...record, at: Date.now() };
  const next = [entry, ...loadHistory().filter((r) => r.id !== entry.id)].slice(0, MAX_ENTRIES);
  persist(next);
  return next;
}

export function clearHistory(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}

function persist(records: ScreeningRecord[]): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(records));
  } catch {
    /* storage full or unavailable - history stays in memory for this visit */
  }
}
