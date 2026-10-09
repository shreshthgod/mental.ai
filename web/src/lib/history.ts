import type { PredictResponse } from "./contract";
import type { ScreeningSummary } from "./api";
import { analysisView, parseAnalysis, parsePrediction } from "./analysisView";
import { privateStorageKey } from "./privateStore";

export interface ScreeningRecord {
  id: string;
  at: number;
  /** The server history deliberately does not return the original disclosure. */
  text: string | null;
  response: PredictResponse | null;
  assessment: "authoritative" | "legacy_unassessed" | "unavailable";
}
const KEY = "mental.ai.history";
const MAX_ENTRIES = 12;
const memory = new Map<string, ScreeningRecord[]>();

function normalize(value: unknown): ScreeningRecord | null {
  if (!value || typeof value !== "object") return null;
  const row = value as Record<string, unknown>;
  if (typeof row.id !== "string" || typeof row.at !== "number" || !Number.isFinite(row.at)) return null;
  if (row.text !== null && typeof row.text !== "string") return null;
  if (row.response != null) {
    try {
      return { id: row.id, at: row.at, text: row.text as string | null, response: parsePrediction(row.response), assessment: "authoritative" };
    } catch {
      return { id: row.id, at: row.at, text: row.text as string | null, response: null, assessment: "unavailable" };
    }
  }
  return { id: row.id, at: row.at, text: row.text as string | null, response: null, assessment: row.assessment === "unavailable" ? "unavailable" : "legacy_unassessed" };
}

export function loadHistory(): ScreeningRecord[] {
  const key = privateStorageKey(KEY);
  if (key === null) return [];
  if (memory.has(key)) return memory.get(key)!;
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(key) ?? "[]");
    if (!Array.isArray(parsed)) return [];
    return parsed.map(normalize).filter((r): r is ScreeningRecord => r !== null).slice(0, MAX_ENTRIES);
  } catch { return []; }
}

function persist(records: ScreeningRecord[]): boolean {
  const key = privateStorageKey(KEY);
  if (key === null) return false;
  memory.set(key, records);
  try { localStorage.setItem(key, JSON.stringify(records)); return true; }
  catch { return false; }
}

export function saveScreening(text: string, response: PredictResponse): { records: ScreeningRecord[]; savedToDevice: boolean } {
  parsePrediction(response);
  const entry: ScreeningRecord = {
    id: response.persistence.record_id ?? crypto.randomUUID(), at: Date.now(), text,
    response, assessment: "authoritative",
  };
  const records = [entry, ...loadHistory().filter(r => r.id !== entry.id)].slice(0, MAX_ENTRIES);
  return { records, savedToDevice: persist(records) };
}

/** Merge only history returned for the current verified account, preserving exact local input. */
export function mergeAccountHistory(rows: ScreeningSummary[]): ScreeningRecord[] {
  const local = loadHistory();
  const byId = new Map(local.map(r => [r.id, r]));
  for (const row of rows) {
    if (typeof row.id !== "string" || !Number.isFinite(Date.parse(row.created_at))) throw new Error("Invalid history record");
    const original = byId.get(row.id);
    let response: PredictResponse | null = null;
    let assessment: ScreeningRecord["assessment"] = "legacy_unassessed";
    if (row.analysis_result !== null) {
      try {
        response = parsePrediction({ ...parseAnalysis(row.analysis_result), persistence: { status: "saved", record_id: row.id } });
        assessment = "authoritative";
      } catch { assessment = "unavailable"; }
    }
    byId.set(row.id, { id: row.id, at: Date.parse(row.created_at), text: original?.text ?? null, response, assessment });
  }
  const records = [...byId.values()].sort((a, b) => b.at - a.at).slice(0, MAX_ENTRIES);
  persist(records);
  return records;
}

export function historyTitle(record: ScreeningRecord): string {
  return record.response ? analysisView(record.response).title : record.assessment === "legacy_unassessed" ? "Legacy / unassessed" : "Recorded analysis unavailable";
}

/** Device-only clear; server deletion is a separate authenticated API operation. */
export function clearHistory(): boolean {
  const key = privateStorageKey(KEY);
  if (key === null) return true;
  memory.delete(key);
  try { localStorage.removeItem(key); return true; }
  catch { return false; }
}
