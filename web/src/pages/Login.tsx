import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { login } from "../lib/auth";
import { Footer } from "../components/chrome/Footer";

export function Login() {
  const [userId, setUserId] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const navigate = useNavigate();
  const location = useLocation();
  const from =
    (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "/screen";

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (login(userId, password)) {
      setErr(null);
      navigate(from, { replace: true });
    } else {
      setErr("Invalid credentials. Demo access: admin / password");
    }
  };

  return (
    <>
      <main id="main" className="login">
        <div className="login__card">
          <p className="label label--accent">Access</p>
          <h1 className="login__title">Sign in</h1>
          <p className="login__sub">
            Screening runs behind a signed-in session. This build ships with demo
            credentials, shown below.
          </p>

          <form className="login__form" onSubmit={onSubmit}>
            <div className="login__field">
              <label htmlFor="login-id" className="label">
                User ID
              </label>
              <input
                id="login-id"
                className="login__input"
                type="text"
                autoComplete="username"
                spellCheck={false}
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                required
              />
            </div>
            <div className="login__field">
              <label htmlFor="login-pass" className="label">
                Password
              </label>
              <input
                id="login-pass"
                className="login__input"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            {err && (
              <p className="login__err" role="alert">
                {err}
              </p>
            )}

            <button type="submit" className="cta cta--primary login__submit">
              Enter <span className="cta__arrow" aria-hidden="true">→</span>
            </button>
          </form>

          <p className="login__demo label">Demo: admin / password</p>
          <Link to="/" className="login__back">
            ← Back to home
          </Link>
        </div>
      </main>
      <Footer />
    </>
  );
}
