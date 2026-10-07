/**
 * Credential form for the sign-in gate.
 *
 * Owns field state and per-field validation; the page owns the request, the
 * loading phase and the error it receives back. Keeping them apart means the
 * form never has to know what ApiError means, and the page never has to know
 * about field-level detail.
 *
 * Validation runs on submit and then live per field once a field has been
 * flagged, so a first attempt reports every problem at once but subsequent
 * typing is not scolded while the user is still mid-word.
 */
import { useEffect, useId, useRef, useState, type FormEvent } from "react";

export interface Credentials {
  userId: string;
  password: string;
  remember: boolean;
}

interface Props {
  /** True from the moment the request starts until it settles. */
  busy: boolean;
  /** Request-level failure, already reduced to a sentence fit for the screen. */
  error: string | null;
  /** True while the page is showing the greeting instead of the form. */
  hidden: boolean;
  /**
   * Increment to move focus to the user field. The hero's call to action uses
   * this; going through the form rather than querying the DOM keeps ownership
   * of the field with the component that renders it. Zero is the initial value
   * and is ignored.
   */
  focusSignal?: number;
  onSubmit: (credentials: Credentials) => void;
}

/**
 * Accept a username, or an email that has to look like one.
 *
 * The service is configured with a single account whose id may be either, so
 * only reject an address that is clearly malformed, and never reject a bare
 * username for failing to be an address.
 */
function validateUserId(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return "Enter your email or username.";
  if (!trimmed.includes("@")) return null;
  const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(trimmed);
  return emailOk ? null : "That does not look like an email address.";
}

/** Eye glyphs, drawn inline: the project ships no icon library. */
function EyeIcon({ off }: { off: boolean }) {
  return (
    <svg viewBox="0 0 20 20" width="17" height="17" fill="none" aria-hidden="true">
      <path
        d="M1.8 10S4.7 4.6 10 4.6 18.2 10 18.2 10 15.3 15.4 10 15.4 1.8 10 1.8 10Z"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinejoin="round"
      />
      <circle cx="10" cy="10" r="2.5" stroke="currentColor" strokeWidth="1.3" />
      {off && (
        <path
          d="M3.2 16.8 16.8 3.2"
          stroke="currentColor"
          strokeWidth="1.3"
          strokeLinecap="round"
        />
      )}
    </svg>
  );
}

export function LoginForm({ busy, error, hidden, focusSignal = 0, onSubmit }: Props) {
  const [userId, setUserId] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [revealed, setRevealed] = useState(false);
  const [userError, setUserError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [recoveryNote, setRecoveryNote] = useState(false);
  const [shake, setShake] = useState(false);

  const uid = useId();
  const pid = useId();
  const uidErrId = `${uid}-err`;
  const pidErrId = `${pid}-err`;
  const firstFieldRef = useRef<HTMLInputElement>(null);
  const previousError = useRef<string | null>(null);

  // A rejected attempt gets a brief 4px nudge. Restrained on purpose: the
  // interface should acknowledge the failure, not punish the person for it.
  useEffect(() => {
    if (!error) {
      previousError.current = null;
      return;
    }
    if (error === previousError.current) return;
    previousError.current = error;
    setShake(true);
    const timer = window.setTimeout(() => setShake(false), 420);
    return () => window.clearTimeout(timer);
  }, [error]);

  // Pulled here by the hero's call to action.
  useEffect(() => {
    if (focusSignal > 0) firstFieldRef.current?.focus();
  }, [focusSignal]);

  /**
   * Focus the first field as soon as the form is on screen, but without
   * scrolling to it.
   *
   * This replaces an `autoFocus` attribute. That attribute focuses during the
   * browser's own load sequence, which on a stacked layout scrolls the page
   * down to the form and takes the hero off screen before anyone has read it -
   * and `scroll-behavior: smooth` makes that impossible to correct afterwards.
   */
  useEffect(() => {
    if (hidden) return;
    firstFieldRef.current?.focus({ preventScroll: true });
  }, [hidden]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (busy) return;
    const nextUserError = validateUserId(userId);
    const nextPasswordError = password ? null : "Enter your password.";
    setUserError(nextUserError);
    setPasswordError(nextPasswordError);
    if (nextUserError || nextPasswordError) {
      // Send focus to the first field that needs attention.
      (nextUserError ? firstFieldRef.current : null)?.focus();
      return;
    }
    onSubmit({ userId: userId.trim(), password, remember });
  };

  return (
    <form className="signin" onSubmit={submit} noValidate aria-hidden={hidden}>
      <div className="signin__field">
        <label htmlFor={uid} className="label">
          Email / username
        </label>
        <input
          id={uid}
          ref={firstFieldRef}
          className={`signin__input ${userError ? "signin__input--invalid" : ""}`}
          type="text"
          name="username"
          autoComplete="username"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          placeholder="you@example.com"
          value={userId}
          onChange={(e) => {
            setUserId(e.target.value);
            if (userError) setUserError(validateUserId(e.target.value));
          }}
          aria-invalid={userError ? true : undefined}
          aria-describedby={userError ? uidErrId : undefined}
          disabled={busy || hidden}
        />
        {userError && (
          <p className="signin__msg signin__msg--error" id={uidErrId}>
            {userError}
          </p>
        )}
      </div>

      <div className="signin__field">
        <label htmlFor={pid} className="label">
          Password
        </label>
        <div className="signin__wrap">
          <input
            id={pid}
            className={`signin__input ${passwordError ? "signin__input--invalid" : ""}`}
            type={revealed ? "text" : "password"}
            name="password"
            autoComplete="current-password"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              if (passwordError) setPasswordError(e.target.value ? null : "Enter your password.");
            }}
            aria-invalid={passwordError ? true : undefined}
            aria-describedby={passwordError ? pidErrId : undefined}
            disabled={busy || hidden}
          />
          <button
            type="button"
            className="signin__reveal"
            onClick={() => setRevealed((v) => !v)}
            aria-label={revealed ? "Hide password" : "Show password"}
            aria-pressed={revealed}
            disabled={busy || hidden}
          >
            <EyeIcon off={revealed} />
          </button>
        </div>
        {passwordError && (
          <p className="signin__msg signin__msg--error" id={pidErrId}>
            {passwordError}
          </p>
        )}
      </div>

      <div className="signin__row">
        <label className="signin__check">
          <input
            type="checkbox"
            checked={remember}
            onChange={(e) => setRemember(e.target.checked)}
            disabled={busy || hidden}
          />
          <span>Remember me</span>
        </label>
        {/* Placed after the fields rather than beside the password label: in the
            label row it would be the next tab stop after the user id, so tabbing
            from the username field would skip the password entirely. */}
        <button
          type="button"
          className="signin__linkish"
          onClick={() => setRecoveryNote((v) => !v)}
          aria-expanded={recoveryNote}
          aria-controls="recovery-note"
          disabled={busy || hidden}
        >
          Forgot password?
        </button>
      </div>

      {recoveryNote && (
        <p className="signin__note signin__note--inline" id="recovery-note">
          This deployment has no self-service password reset. Accounts are issued
          by the project operator, who can reset the configured credential.
        </p>
      )}

      {error && (
        <p
          className={`signin__msg signin__msg--error signin__msg--request ${
            shake ? "signin__msg--shake" : ""
          }`}
          role="alert"
        >
          {error}
        </p>
      )}

      <button
        type="submit"
        className="signin__submit"
        disabled={busy || hidden}
        aria-busy={busy}
      >
        {busy ? (
          <>
            Authenticating
            <span className="signin__dots" aria-hidden="true">
              <i />
              <i />
              <i />
            </span>
          </>
        ) : (
          <>
            Login
            <span className="signin__arrow" aria-hidden="true">
              →
            </span>
          </>
        )}
      </button>

      {busy && (
        <span className="sr-only" role="status">
          Authenticating
        </span>
      )}

      <p className="signin__micro">
        Your session is held in this browser and validated by the screening
        service. Nothing here is a diagnosis.
      </p>
    </form>
  );
}