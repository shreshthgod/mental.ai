/**
 * Credentials panel for the entry composition.
 *
 * Sits on the right over the environment rather than inside a card: a barely
 * tinted, blurred plane with a hairline edge. The panel has to be readable over
 * a live WebGL scene, so the falloff behind it is doing real work - without it
 * the sculpture's highlights would land inside the text.
 *
 * The form itself is the same component the app already uses, so validation,
 * the reveal control and the loading state have a single implementation.
 *
 * Sign-in methods offered here: email + password, and Google through Supabase
 * Auth. Both are inside the existing panel and reuse the panel's own type and
 * controls, so the surface is the same one that was already there.
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { LoginForm, type Credentials } from "../login/LoginForm";
import { useAccountActions } from "../chrome/AccountMenu";
import { authError, register, signInWithGoogle, socialSignInAvailable } from "../../lib/auth";

interface Props {
  /** Incremented by the hero call to action to pull focus into the form. */
  focusSignal: number;
  busy: boolean;
  error: string | null;
  hidden: boolean;
  onSubmit: (credentials: Credentials) => void;
  returnTo: string;
}

/** Already-signed-in variant: an offer to continue rather than a form. */
export function WelcomePanel() {
  const { restartScreening, logOut } = useAccountActions();
  return (
    <div className="entry__panel-inner">
      <p className="label label--accent">MENTAL.AI / SESSION</p>
      <h2 className="entry__heading">You are signed in.</h2>
      <p className="entry__sub">Your screening session is ready.</p>
      <Link to="/screen" className="signin__submit entry__submit-link">
        Continue screening
        <span className="signin__arrow" aria-hidden="true">
          →
        </span>
      </Link>
      <div className="entry__panel-links">
        <button type="button" className="entry__quiet" onClick={restartScreening}>
          Restart check-in
        </button>
        <button type="button" className="entry__quiet" onClick={logOut}>
          Sign out
        </button>
      </div>
      <p className="entry__micro">Session held in this browser.</p>
    </div>
  );
}

/** Wording for the two modes, so the heading tracks what the fields ask for. */
const COPY = {
  signIn: {
    label: "MENTAL.AI / ACCESS",
    heading: "Welcome back.",
    sub: "Sign in to continue your screening.",
    switchTo: "Create an account",
    switchPrompt: "New to MENTAL.AI?",
  },
  register: {
    label: "MENTAL.AI / ACCOUNT",
    heading: "Create your account.",
    sub: "Set a password to start a screening session.",
    switchTo: "I already have an account",
    switchPrompt: "Already registered?",
  },
} as const;

type Mode = keyof typeof COPY;

export function LoginPanel({ focusSignal, busy, error, hidden, onSubmit, returnTo }: Props) {
  const [mode, setMode] = useState<Mode>("signIn");
  const [socialBusy, setSocialBusy] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [remember, setRemember] = useState(true);

  const copy = COPY[mode];
  const googleAvailable = socialSignInAvailable();

  /** One error line for both entry points, with no internal detail leaking. */
  const fail = (err: unknown): void => {
    const message = err instanceof Error && err.message ? err.message : "";
    setLocalError(
      /invalid login credentials/i.test(message)
        ? "We couldn't sign you in with those details."
        : message || "Something went wrong. Please try again."
    );
  };

  /**
   * Registration is handled here; sign-in is still delegated to the page.
   *
   * The page owns the sign-in request, its loading phase and the error it maps
   * to screen copy, so that path is untouched. Creating an account is a new
   * operation, so it lives beside the button that starts it.
   */
  const submit = async (credentials: Credentials): Promise<void> => {
    setLocalError(null);
    setNotice(null);
    if (mode === "signIn") {
      onSubmit(credentials);
      return;
    }
    try {
      const { session } = await register(
        credentials.userId,
        credentials.password,
        credentials.remember
      );
      if (!session) {
        // The project requires email confirmation: tell the visitor what to
        // expect instead of leaving the form looking like it failed.
        setNotice("Check your inbox to confirm your email address, then sign in.");
        setMode("signIn");
      }
    } catch (err) {
      fail(err);
    }
  };

  const google = async (): Promise<void> => {
    setLocalError(null);
    setSocialBusy(true);
    try {
      // Leaves the page on success. If it fails the visitor is still here and
      // gets the existing error line rather than a blank screen.
      await signInWithGoogle({ remember, returnTo });
    } catch (err) {
      setSocialBusy(false);
      fail(err);
    }
  };

  return (
    <div className="entry__panel">
      <div className={`entry__panel-inner ${hidden ? "entry__panel-inner--out" : ""}`}>
        <p className="label label--accent">{copy.label}</p>
        <h2 className="entry__heading">{copy.heading}</h2>
        <p className="entry__sub">{copy.sub}</p>

        <LoginForm
          mode={mode}
          busy={busy || socialBusy}
          error={error ?? localError ?? authError()}
          notice={notice}
          hidden={hidden}
          focusSignal={focusSignal}
          onSubmit={submit}
          onRememberChange={setRemember}
        />

        {googleAvailable && (
          <>
            {/* Same measure as the divider already used above the research
                link, so the panel keeps one vertical rhythm. */}
            <div className="signin__or" role="separator">
              <span>or</span>
            </div>
            <button
              type="button"
              className="signin__social"
              onClick={() => void google()}
              disabled={busy || socialBusy || hidden}
            >
              <GoogleGlyph aria-hidden="true" />
              {socialBusy ? "Opening Google…" : "Continue with Google"}
            </button>
          </>
        )}

        <p className="signin__switch">
          <span className="signin__switch-prompt">{copy.switchPrompt}</span>{" "}
          <button
            type="button"
            className="signin__linkish"
            onClick={() => {
              setMode(mode === "signIn" ? "register" : "signIn");
              setLocalError(null);
              setNotice(null);
            }}
            disabled={busy || hidden}
          >
            {copy.switchTo}
          </button>
        </p>

        <Link to="/research" className="entry__link">
          Read the research first
        </Link>
      </div>
    </div>
  );
}

/** Google's mark, drawn inline: the project ships no icon library. */
function GoogleGlyph({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 18 18" width="16" height="16" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.91c1.7-1.57 2.69-3.88 2.69-6.62Z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.91-2.26c-.81.54-1.85.86-3.05.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.34A9 9 0 0 0 9 18Z"
      />
      <path
        fill="#FBBC05"
        d="M3.97 10.72a5.4 5.4 0 0 1 0-3.44V4.94H.96a9 9 0 0 0 0 8.12l3.01-2.34Z"
      />
      <path
        fill="#EA4335"
        d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.59C13.46.9 11.43 0 9 0A9 9 0 0 0 .96 4.94l3.01 2.34C4.68 5.16 6.66 3.58 9 3.58Z"
      />
    </svg>
  );
}
