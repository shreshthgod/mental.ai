import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "../lib/api";
import { firstName, login } from "../lib/auth";
import { useAuth } from "../lib/authContext";
import type { Credentials } from "../components/login/LoginForm";
import { WordPlane } from "../components/entry/Wordmark";
import { LoginPanel, WelcomePanel } from "../components/entry/LoginPanel";
import { useReducedMotion } from "../lib/motion";

const NeuralStage = lazy(() => import("../components/entry/NeuralStage"));
const Grainient = lazy(() =>
  import("../components/Grainient/Grainient").then((m) => ({ default: m.Grainient }))
);

const WELCOME_MS = 1150;

const INTRO_KEY = "mental.ai_intro_played";

const HERO_APPEAR_MS = 2000;
const HANDOVER_MS = 4250;
const HANDOVER_INSTANT_MS = 260;

type Phase = "form" | "authenticating" | "welcome";

function readableError(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.kind) {
      case "unauthorized":
        return "We couldn't sign you in with those details.";
      case "throttled":
        return error.message;
      case "timeout":
        return "The sign-in service took too long to respond. Please try again.";
      case "validation":
        return "Those details were not accepted. Please check and try again.";
      default:
        return "Unable to reach the server. Please try again.";
    }
  }
  return "Sign-in failed unexpectedly. Please try again.";
}

const FIELD_LABELS = ["Input / language", "Signal / active", "Pattern / analysis"];

export function Start() {
  const navigate = useNavigate();
  const location = useLocation();
  const reduced = useReducedMotion();
  const authed = useAuth() === "authed";

  const [live, setLive] = useState(false);
  const [heroVisible, setHeroVisible] = useState(false);
  const [split, setSplit] = useState(false);
  const [phase, setPhase] = useState<Phase>("form");
  const [error, setError] = useState<string | null>(null);
  const [greeting, setGreeting] = useState("");
  const [focusSignal, setFocusSignal] = useState(0);
  const timerRef = useRef<number | null>(null);
  const heroTimerRef = useRef<number | null>(null);
  const handoverRef = useRef<number | null>(null);

  const [instant] = useState(() => {
    try {
      return sessionStorage.getItem(INTRO_KEY) === "1";
    } catch {
      return false;
    }
  });

  // Deep link: the guard records where an unauthenticated visitor was heading.
  const from = useRef<string>("/screen");
  const state = location.state as { from?: { pathname?: string; search?: string; hash?: string } } | null;
  if (state?.from?.pathname && state.from.pathname !== "/") {
    from.current = `${state.from.pathname}${state.from.search ?? ""}${state.from.hash ?? ""}`;
  }

  const busy = phase === "authenticating";
  const welcome = phase === "welcome";

  useEffect(() => {

    const raf = requestAnimationFrame(() => setLive(true));

    heroTimerRef.current = window.setTimeout(
      () => setHeroVisible(true),
      instant ? 0 : (reduced ? 0 : HERO_APPEAR_MS)
    );

    handoverRef.current = window.setTimeout(
      () => {
        setSplit(true);
        try {
          sessionStorage.setItem(INTRO_KEY, "1");
        } catch {
          /* private mode */
        }
      },
      instant ? HANDOVER_INSTANT_MS : (reduced ? 200 : HANDOVER_MS)
    );

    return () => {
      cancelAnimationFrame(raf);
      if (heroTimerRef.current !== null) window.clearTimeout(heroTimerRef.current);
      if (handoverRef.current !== null) window.clearTimeout(handoverRef.current);
    };
  }, [instant, reduced]);

  useEffect(
    () => () => {
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    },
    []
  );

  const signIn = useCallback(
    async ({ userId, password, remember }: Credentials) => {
      setPhase("authenticating");
      setError(null);
      try {
        const session = await login(userId, password, remember);
        setGreeting(firstName(session.name) || firstName(session.user));
        setPhase("welcome");
        // Reduced motion holds the greeting far shorter rather than showing a
        // static card for a second and a half.
        const delay = reduced ? 240 : WELCOME_MS;
        timerRef.current = window.setTimeout(() => navigate(from.current, { replace: true }), delay);
      } catch (err) {
        setError(readableError(err));
        setPhase("form");
      }
    },
    [navigate, reduced]
  );

  const beginLogin = () => setFocusSignal((n) => n + 1);

  return (
    <main
      id="main"
      className={`entry ${live ? "entry--live" : ""} ${heroVisible ? "entry--hero-live" : ""} ${
        split ? "entry--split" : ""
      } ${welcome ? "entry--welcome" : ""}`}
    >

      <div className="entry__atmosphere" aria-hidden="true" />


      <Suspense fallback={null}>
        <Grainient
          className="entry__grain"
          color1="#0e0b20"
          color2="#17123a"
          color3="#030306"
          timeSpeed={0.28}
          warpStrength={0.26}
          warpFrequency={1.8}
          warpSpeed={0.11}
          warpAmplitude={55}
          blendAngle={128}
          blendSoftness={0.85}
          rotationAmount={36}
          grainAmount={0.05}
          grainScale={1.3}
          contrast={1.02}
          gamma={1.1}
          saturation={0.86}
          centerY={-0.04}
          zoom={1.9}
        />
      </Suspense>


      <div className="entry__main">
        <section className="hero-stage" aria-label="MENTAL.AI">

          <div className="hero-stage__scene">

            <div className="entry__depth">
              <WordPlane live={live} plane="back" instant={instant} dimmed={welcome} />
              <Suspense fallback={null}>
                <NeuralStage
                  className="entry__stage"
                  emergeDelayMs={0}
                  focus={welcome ? 1 : 0}
                />
              </Suspense>
              <WordPlane live={live} plane="front" instant={instant} dimmed={welcome} />
            </div>


            <div className="entry__vignette" aria-hidden="true" />

            <div className="entry__rules" aria-hidden="true">
              <span className="entry__rule entry__rule--gutter" />
              <span className="entry__rule entry__rule--split" />
            </div>
            <ul className="entry__labels" aria-hidden="true">
              {FIELD_LABELS.map((label, i) => (
                <li key={label} className={`entry__label entry__label--${i + 1}`}>
                  {label}
                </li>
              ))}
            </ul>
          </div>


          <div className="entry__copy">
            <p className="label label--accent">AI-assisted mental wellness screening</p>
            <h1 className="entry__headline">Understand the signal.</h1>
            <p className="entry__sub">
              MENTAL.AI helps you reflect on your words and responses through a
              research-informed screening experience, designed to surface patterns
              while keeping the final interpretation human-centred.
            </p>
            {!authed && (
              <div className="entry__ctas">
                <button type="button" className="cta cta--primary" onClick={beginLogin}>
                  Login to begin <span className="cta__arrow" aria-hidden="true">→</span>
                </button>
                <Link to="/research" className="cta cta--ghost">
                  Explore the research
                </Link>
              </div>
            )}
          </div>
        </section>


        <section className="auth-stage" aria-label="Sign in">
          <div className={`entry__panel-slot ${welcome ? "entry__panel-slot--out" : ""}`}>
            {authed ? (
              <WelcomePanel />
            ) : (
              <LoginPanel
                focusSignal={focusSignal}
                busy={busy}
                error={error}
                hidden={welcome}
                onSubmit={signIn}
                returnTo={from.current}
              />
            )}
          </div>


          <p className="auth-stage__foot label" aria-hidden="true">
            Local safety rules · Trained browser classifiers unavailable
          </p>


          {welcome && (
            <div className="entry__greeting" role="status">
              <p className="label label--accent">MENTAL.AI / SESSION</p>
              <p className="label">Authentication complete</p>
              <p className="entry__greeting-hello">
                Hello,
                <br />
                <span className="entry__greeting-name">{greeting}.</span>
              </p>
              <p className="entry__greeting-sub">Ready when you are.</p>
              <span className="entry__greeting-pulse" aria-hidden="true" />
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
