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
 */
import { Link } from "react-router-dom";
import { LoginForm, type Credentials } from "../login/LoginForm";
import { useAccountActions } from "../chrome/AccountMenu";

interface Props {
  /** Incremented by the hero call to action to pull focus into the form. */
  focusSignal: number;
  busy: boolean;
  error: string | null;
  hidden: boolean;
  onSubmit: (credentials: Credentials) => void;
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

export function LoginPanel({ focusSignal, busy, error, hidden, onSubmit }: Props) {
  return (
    <div className="entry__panel">
      <div className={`entry__panel-inner ${hidden ? "entry__panel-inner--out" : ""}`}>
        <p className="label label--accent">MENTAL.AI / ACCESS</p>
        <h2 className="entry__heading">Welcome back.</h2>
        <p className="entry__sub">Sign in to continue your screening.</p>

        <LoginForm
          busy={busy}
          error={error}
          hidden={hidden}
          focusSignal={focusSignal}
          onSubmit={onSubmit}
        />

        <Link to="/research" className="entry__link">
          Read the research first
        </Link>
      </div>
    </div>
  );
}