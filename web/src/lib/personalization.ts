/**
 * Personalized therapist-like welcome experience.
 *
 * All state is strictly client-side and scoped to the active browser account.
 * Themes are abstracted into high-level reflective categories; raw text is
 * NEVER mirrored back verbatim, and clinical labels are NEVER assumed.
 */
import { privateStorageKey } from "./privateStore";

const STORAGE_KEY = "mental.ai.personalization";

export interface PersonalizationPreferences {
  enabled: boolean;
  preferredName?: string;
  lastVisitAt?: number;
  rememberedThemes: string[];
}

const DEFAULT_PREFS: PersonalizationPreferences = {
  enabled: true,
  rememberedThemes: [],
};

export function loadPersonalizationPrefs(): PersonalizationPreferences {
  const key = privateStorageKey(STORAGE_KEY);
  if (!key) return { ...DEFAULT_PREFS };
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return { ...DEFAULT_PREFS };
    const parsed = JSON.parse(raw);
    return {
      enabled: typeof parsed.enabled === "boolean" ? parsed.enabled : true,
      preferredName: typeof parsed.preferredName === "string" ? parsed.preferredName : undefined,
      lastVisitAt: typeof parsed.lastVisitAt === "number" ? parsed.lastVisitAt : undefined,
      rememberedThemes: Array.isArray(parsed.rememberedThemes) ? parsed.rememberedThemes : [],
    };
  } catch {
    return { ...DEFAULT_PREFS };
  }
}

export function savePersonalizationPrefs(prefs: Partial<PersonalizationPreferences>): void {
  const key = privateStorageKey(STORAGE_KEY);
  if (!key) return;
  const current = loadPersonalizationPrefs();
  const updated: PersonalizationPreferences = {
    ...current,
    ...prefs,
  };
  try {
    localStorage.setItem(key, JSON.stringify(updated));
  } catch {
    /* ignore local storage quota / unavailability */
  }
}

export function clearRememberedThemes(): void {
  const current = loadPersonalizationPrefs();
  savePersonalizationPrefs({ ...current, rememberedThemes: [] });
}

export function clearAllPersonalization(): void {
  const key = privateStorageKey(STORAGE_KEY);
  if (!key) return;
  try {
    localStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}

/**
 * Distill high-level conversational themes safely without saving raw quotes.
 */
export function extractSafeThemes(text: string): string[] {
  const lower = text.toLowerCase();
  const themes: string[] = [];

  if (/\b(work|job|boss|project|deadline|exam|school|college|office|career)\b/.test(lower)) {
    themes.push("work and responsibilities");
  }
  if (/\b(sleep|insomnia|tired|exhausted|waking up|nightmare|restless)\b/.test(lower)) {
    themes.push("sleep and rest");
  }
  if (/\b(alone|lonely|isolated|nobody|friend|friends|family|partner|relationship)\b/.test(lower)) {
    themes.push("connection and relationships");
  }
  if (/\b(anxious|panic|racing|breath|worried|overwhelmed|stressed)\b/.test(lower)) {
    themes.push("feeling overwhelmed");
  }
  if (/\b(future|uncertain|direction|decision|stuck|lost)\b/.test(lower)) {
    themes.push("decisions and future directions");
  }

  return themes.slice(0, 2);
}

/**
 * Record a visit and update safe high-level themes.
 */
export function recordSessionVisit(text?: string, name?: string): void {
  const prefs = loadPersonalizationPrefs();
  if (!prefs.enabled) return;

  const newThemes = text ? extractSafeThemes(text) : [];
  const mergedThemes = Array.from(new Set([...newThemes, ...prefs.rememberedThemes])).slice(0, 3);

  savePersonalizationPrefs({
    preferredName: name || prefs.preferredName,
    lastVisitAt: Date.now(),
    rememberedThemes: mergedThemes,
  });
}

export interface WelcomeGreeting {
  headline: string;
  subtext: string;
  hasPastContext: boolean;
  themes: string[];
}

/**
 * Construct a gentle, non-prescriptive welcome reflection.
 */
export function generateWelcomeGreeting(name?: string): WelcomeGreeting {
  const prefs = loadPersonalizationPrefs();
  const greetingName = name || prefs.preferredName;
  const nameSalutation = greetingName ? `, ${greetingName}` : "";

  if (!prefs.enabled || prefs.rememberedThemes.length === 0) {
    return {
      headline: `Welcome${nameSalutation}`,
      subtext:
        "Take a quiet breath. Whatever is on your mind today, you're welcome to write as much or as little as you need.",
      hasPastContext: false,
      themes: [],
    };
  }

  const themesList =
    prefs.rememberedThemes.length === 1
      ? prefs.rememberedThemes[0]
      : `${prefs.rememberedThemes[0]} and ${prefs.rememberedThemes[1]}`;

  return {
    headline: `Welcome back${nameSalutation}`,
    subtext: `Last time we checked in, things were centering around ${themesList}. How have things been moving since then, or is there something completely different on your mind today?`,
    hasPastContext: true,
    themes: prefs.rememberedThemes,
  };
}
