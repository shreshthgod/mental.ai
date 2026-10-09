import { lazy, Suspense, useEffect, useState, type ReactNode } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { Navigation } from "./components/chrome/Navigation";
import { GridOverlay } from "./components/chrome/GridOverlay";
import GradientWaves from "./components/GradientWaves/GradientWaves";
import { Landing } from "./pages/Landing";
import { Start } from "./pages/Start";
import { consumeOAuthReturnPath, validateSession } from "./lib/auth";
import { useAuth } from "./lib/authContext";

// Route-level code splitting (design spec 14). The two heaviest routes load on
// demand: Landing and Login stay eager because they are the entry points, while
// /screen and /research are only reachable after the gate and should not weigh
// down the first paint.
const Screen = lazy(() => import("./pages/Screen").then((m) => ({ default: m.Screen })));
const Research = lazy(() => import("./pages/Research").then((m) => ({ default: m.Research })));

const reducedMotion =
  typeof window !== "undefined" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const narrowViewport = typeof window !== "undefined" && window.innerWidth < 768;

/**
 * Neutral holding state while the stored token is re-validated.
 *
 * Deliberately quiet so there is no flash of the landing page or the sign-in
 * panel before the session check resolves, but it does say what it is waiting
 * for: a silent spinner reads as a stalled app rather than a deliberate check.
 */
function AuthSplash() {
  return (
    <div className="auth-splash" role="status" aria-live="polite">
      <p className="label">MENTAL.AI</p>
      <span className="auth-splash__dot" aria-hidden="true" />
      <span className="label">Restoring session</span>
    </div>
  );
}

/**
 * Placeholder while a lazily loaded route chunk arrives.
 *
 * Matches AuthSplash visually so moving between split routes does not flash a
 * different-looking surface mid-navigation.
 */
function RouteFallback() {
  return (
    <div className="auth-splash" role="status" aria-live="polite">
      <span className="auth-splash__dot" aria-hidden="true" />
      <span className="sr-only">Loading</span>
    </div>
  );
}

function RequireAuth({ children }: { children: ReactNode }) {
  const state = useAuth();
  const location = useLocation();
  if (state === "restoring") return <AuthSplash />;
  // `from` carries the whole location, so the sign-in page can return the user
  // to the exact path they asked for, query and hash included.
  if (state !== "authed") return <Navigate to="/login" state={{ from: location }} replace />;
  return <>{children}</>;
}

export default function App() {
  const location = useLocation();
  const [introSettled, setIntroSettled] = useState(false);
  const navigate = useNavigate();
  const state = useAuth();
  const onSettled = (s: boolean) => setIntroSettled(s);

  // Rehydrate and validate the stored token before any route decision, so a
  // stale token cannot flash protected content and then bounce to sign-in.
  // The store publishes the outcome; no local copy of the state is needed.
  useEffect(() => {
    void validateSession();
  }, []);

  useEffect(() => {
    if (state !== "authed") return;
    const destination = consumeOAuthReturnPath();
    if (destination) navigate(destination, { replace: true });
  }, [state, navigate]);

  // The About page has a long intro the grid should stay out of until the
  // hero has settled; the entry is a single screen and wants it immediately.
  const gridOn = location.pathname !== "/about" || introSettled;
  // The entry draws its own rules from its own grid, so the site-wide column
  // overlay would only compete with the lines the composition is built on.
  const isEntry = location.pathname === "/" || location.pathname === "/login";
  const gated = state === "authed";

  return (
    <>
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <div className="site-waves" aria-hidden="true">
        <GradientWaves
          horizonColor="#0b0920"
          waveColor="#4f46e5"
          crestColor="#b7a6ff"
          speed={reducedMotion ? 0 : 0.28}
          amplitude={2.5}
          waveScale={0.6}
          waveRatio={0.9}
          swell={35}
          turbulence={20}
          tilt={1.11}
          zoom={1.0}
          height={5.5}
          fogDepth={15}
          detail={narrowViewport ? "low" : "medium"}
          brightness={0.9}
          opacity={1.0}
          mouseInteraction={!reducedMotion}
          parallaxStrength={0.5}
          grain={true}
          grainIntensity={0.05}
        />
      </div>
      <GridOverlay on={gridOn && !isEntry} />
      <Navigation
        introSettled={location.pathname !== "/about" || introSettled}
        signedIn={gated}
      />
      <div className="route" key={location.pathname}>
        {state === "restoring" ? (
          <AuthSplash />
        ) : (
          <Suspense fallback={<RouteFallback />}>
            <Routes location={location}>
              {/*
                The entry composition is the sign-in experience, so it serves
                both paths: "/" for a first visit, "/login" for a deep link or a
                bookmark. One component means there is no second, plainer login
                page to drift out of step with this one.
              */}
              <Route path="/" element={<Start />} />
              <Route path="/login" element={<Start />} />
              {/* The long-form product page moved here when "/" became the
                  entry, so its content and anchors stay reachable. */}
              <Route path="/about" element={<Landing onSettled={onSettled} />} />
              <Route
                path="/screen"
                element={
                  <RequireAuth>
                    <Screen />
                  </RequireAuth>
                }
              />
              <Route path="/research" element={<Research />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        )}
      </div>
    </>
  );
}
