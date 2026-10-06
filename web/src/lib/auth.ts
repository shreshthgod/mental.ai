const KEY = "vantage.auth";

interface Session {
  user: string;
  at: number;
}

export function isAuthed(): boolean {
  try {
    return localStorage.getItem(KEY) !== null;
  } catch {
    return false;
  }
}

export function currentUser(): string | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<Session>;
    return typeof parsed.user === "string" ? parsed.user : null;
  } catch {
    return null;
  }
}

/** Demo credentials: admin / password. Replace with a real auth provider. */
export function login(userId: string, password: string): boolean {
  const ok = userId.trim().toLowerCase() === "admin" && password === "password";
  if (ok) {
    try {
      const session: Session = { user: "admin", at: Date.now() };
      localStorage.setItem(KEY, JSON.stringify(session));
    } catch {
      /* storage unavailable - session stays in-memory for this visit */
    }
  }
  return ok;
}

export function logout(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
