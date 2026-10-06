import { useCallback, useState, type ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Navigation } from "./components/chrome/Navigation";
import { GridOverlay } from "./components/chrome/GridOverlay";
import GradientWaves from "./components/GradientWaves/GradientWaves";
import { Landing } from "./pages/Landing";
import { Screen } from "./pages/Screen";
import { Research } from "./pages/Research";
import { Login } from "./pages/Login";
import { isAuthed } from "./lib/auth";

const reducedMotion =
  typeof window !== "undefined" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const narrowViewport =
  typeof window !== "undefined" && window.innerWidth < 768;

function RequireAuth({ children }: { children: ReactNode }) {
  const location = useLocation();
  if (isAuthed()) return <>{children}</>;
  return <Navigate to="/login" state={{ from: location }} replace />;
}

export default function App() {
  const location = useLocation();
  const [introSettled, setIntroSettled] = useState(false);
  const onSettled = useCallback((s: boolean) => setIntroSettled(s), []);

  const gridOn = location.pathname !== "/" || introSettled;

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
      <GridOverlay on={gridOn} />
      <Navigation introSettled={location.pathname !== "/" || introSettled} />
      <div className="route" key={location.pathname}>
        <Routes location={location}>
          <Route path="/" element={<Landing onSettled={onSettled} />} />
          <Route path="/login" element={<Login />} />
          <Route
            path="/screen"
            element={
              <RequireAuth>
                <Screen />
              </RequireAuth>
            }
          />
          <Route path="/research" element={<Research />} />
        </Routes>
      </div>
    </>
  );
}
