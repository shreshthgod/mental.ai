import { useCallback, useState } from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import { Navigation } from "./components/chrome/Navigation";
import { GridOverlay } from "./components/chrome/GridOverlay";
import { Landing } from "./pages/Landing";
import { Screen } from "./pages/Screen";
import { Research } from "./pages/Research";

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
      <GridOverlay on={gridOn} />
      <Navigation introSettled={location.pathname !== "/" || introSettled} />
      <div className="route" key={location.pathname}>
        <Routes location={location}>
          <Route path="/" element={<Landing onSettled={onSettled} />} />
          <Route path="/screen" element={<Screen />} />
          <Route path="/research" element={<Research />} />
        </Routes>
      </div>
    </>
  );
}
