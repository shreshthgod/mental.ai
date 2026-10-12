import { privateStorageKey } from "./privateStore";

const STORAGE_KEY = "mental.ai.personalization";

export interface PersonalizationPreferences {
  enabled: boolean;
  consentVersion?: 1;
  preferredName?: string;
  lastVisitAt?: number;
  rememberedThemes: string[];
}

const DEFAULT_PREFS: PersonalizationPreferences = {
  enabled: false,
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
      enabled: parsed.enabled === true && parsed.consentVersion === 1,
      preferredName: typeof parsed.preferredName === "string" ? parsed.preferredName : undefined,
      lastVisitAt: typeof parsed.lastVisitAt === "number" ? parsed.lastVisitAt : undefined,
      rememberedThemes: parsed.enabled === true && parsed.consentVersion === 1 && Array.isArray(parsed.rememberedThemes)
        ? parsed.rememberedThemes.filter((v: unknown): v is string => typeof v === "string").slice(0, 3) : [],
      consentVersion: parsed.consentVersion === 1 ? 1 : undefined,
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
    consentVersion: prefs.enabled === true ? 1 : current.consentVersion,
  };
  if (!updated.enabled) {
    updated.rememberedThemes = [];
    delete updated.preferredName;
    delete updated.lastVisitAt;
  }
  try {
    localStorage.setItem(key, JSON.stringify(updated));
    if (typeof window !== "undefined") window.dispatchEvent(new Event("mental-personalization-change"));
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
    if (typeof window !== "undefined") window.dispatchEvent(new Event("mental-personalization-change"));
  } catch {
    /* ignore */
  }
}

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

export function generateWelcomeGreeting(name?: string): WelcomeGreeting {
  const prefs = loadPersonalizationPrefs();
  const greetingName = name || (prefs.enabled ? prefs.preferredName : undefined);
  const nameSalutation = greetingName ? `, ${greetingName}` : "";

  if (!prefs.enabled || prefs.rememberedThemes.length === 0) {
    return {
      headline: `Welcome${nameSalutation}`,
      subtext:
        "Write as much or as little as you like.",
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
    subtext: `Your saved themes include ${themesList}. What would you like to reflect on today?`,
    hasPastContext: true,
    themes: prefs.rememberedThemes,
  };
}
