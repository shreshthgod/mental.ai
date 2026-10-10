/**
 * MENTAL.AI entry - the first thing anyone sees.
 *
 * One art-directed composition: the neural sculpture, the oversized wordmark
 * the sculpture passes through, the positioning copy low-left, the credentials
 * on the right. Depth is built from stacked layers rather than from panels, so
 * the type, the metal and the type behind the metal all occupy the same space.
 *
 * The composition is a real two-column grid, not four independently positioned
 * elements. `.entry__main` splits the space into a visual stage on the left and
 * a credentials stage on the right; both resolve their horizontal edges from
 * the same page gutter the navigation uses, so the logo, the hero copy, the
 * panel and the technical annotation line up by construction. Everything the
 * scene needs - canvas, both word planes, the falloff, the annotations - is
 * clipped to the visual stage, which is what keeps the wordmark clear of the
 * form instead of running underneath it.
 *
 * Authentication is unchanged from the sign-in gate this replaced - same
 * `login()` call, same session store, same route guard. What changed is that it
 * happens here, on "/", with the environment still visible behind it, and that
 * the success moment is staged inside the composition rather than on a
 * separate screen.
 *
 * Layer order, bottom to top, inside the visual stage:
 *   1 wordmark, back plane
 *   2 WebGL sculpture
 *   3 wordmark, front plane       <- the intersection
 *   4 vignette and field labels
 * Page-wide beneath the grid: the atmosphere and the grain.
 * Above the grid: hero copy, credentials, navigation (from App).
 */
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

/** How long the greeting holds before the screening takes over. */
const WELCOME_MS = 1150;

/**
 * Choreographed entry sequence:
 *   1. T = 0ms: "Mental.ai" animates for 1.0 second in metallic Marvel/Transformers movie credit style.
 *   2. T = 1000ms: Hero appears (rotating metallic DNA spiral spring emerges at the center).
 *   3. T = 3000ms (2 seconds after hero appears): The composition drifts smoothly to the left 70% of the screen.
 */
const HERO_APPEAR_MS = 1000;
const HANDOVER_MS = 3000;

type Phase = "form" | "authenticating" | "welcome";

/**
 * Reduce an ApiError to one sentence for the screen.
 *
 * The backend is deliberately vague about which half of the credential pair was
 * wrong and the user is told no more than that. Transport failures get their own
 * wording because the remedy is different: start the server.
 */
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

/**
 * Small technical annotations over the sculpture.
 *
 * Purely decorative and honest: they name stages of the real pipeline rather
 * than implying measurements of the visitor.
 */
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

  // Deep link: the guard records where an unauthenticated visitor was heading.
  const from = useRef<string>("/screen");
  const state = location.state as { from?: { pathname?: string; search?: string; hash?: string } } | null;
  if (state?.from?.pathname && state.from.pathname !== "/") {
    from.current = `${state.from.pathname}${state.from.search ?? ""}${state.from.hash ?? ""}`;
  }

  const busy = phase === "authenticating";
  const welcome = phase === "welcome";

  useEffect(() => {
    // T = 0ms: start 1-second metallic logo animation
    const raf = requestAnimationFrame(() => setLive(true));

    // T = 1000ms (1s): hero appears
    heroTimerRef.current = window.setTimeout(() => {
      setHeroVisible(true);
    }, reduced ? 0 : HERO_APPEAR_MS);

    // T = 3000ms (2s later): drifts to the left 70% of the screen
    handoverRef.current = window.setTimeout(() => {
      setSplit(true);
    }, reduced ? 200 : HANDOVER_MS);

    return () => {
      cancelAnimationFrame(raf);
      if (heroTimerRef.current !== null) window.clearTimeout(heroTimerRef.current);
      if (handoverRef.current !== null) window.clearTimeout(handoverRef.current);
    };
  }, [reduced]);

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
      {/* Atmosphere. Also the WebGL fallback surface: if both GL tiers fail,
          this gradient is what remains, so it has to stand on its own. */}
      <div className="entry__atmosphere" aria-hidden="true" />

      {/* Grain. */}
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

      {/* The composition. Two columns on the same page grid as the header.
          The presentation holds this full-bleed while the word and the
          sculpture assemble, then the tracks change to the 70/30 pair; nothing
          here is re-mounted, so the canvas keeps its GL context across the
          hand-over. */}
      <div className="entry__main">
        <section className="hero-stage" aria-label="MENTAL.AI">
          {/* The scene box. A stage of its own so the single-frame desktop
              composition can clip to it, and the stacked layout can turn it
              into a band above the copy without moving any markup. */}
          <div className="hero-stage__scene">
            {/* Back word plane, sculpture, front word plane. Siblings in one
                stacking context so the sculpture genuinely passes between
                them. */}
            <div className="entry__depth">
              <WordPlane live={live} plane="back" dimmed={welcome} />
              <Suspense fallback={null}>
                <NeuralStage
                  className="entry__stage"
                  emergeDelayMs={0}
                  focus={welcome ? 1 : 0}
                />
              </Suspense>
              <WordPlane live={live} plane="front" dimmed={welcome} />
            </div>

            {/* Falloff over the scene, so type and fields stay readable, plus
                the field annotations. */}
            <div className="entry__vignette" aria-hidden="true" />
            {/* Structural rules for this composition: the page gutter the
                logo, the copy and the word all sit on, and the visual stage's
                internal division. Below the copy, above the scene. */}
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

          {/* Positioning copy, on the gutter the logo sits on. */}
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

        {/* Credentials. The panel is optically centred in this stage; the stage
            reserves its own foot space so the annotation cannot sit under it. */}
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

          {/* Technical annotation. Names the deployed models rather than
              implying measurements of the visitor. */}
          <p className="auth-stage__foot label" aria-hidden="true">
            Dual-model inference · XGBoost + LogReg · Proxy labels · Research signals
          </p>

          {/* Success state, staged in the place the form occupied, so the
              composition acknowledges it without rearranging itself. */}
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
