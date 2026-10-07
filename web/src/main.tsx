import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "@fontsource-variable/inter";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/grid.css";
import "./styles/nav.css";
import "./styles/hero.css";
import "./styles/sections.css";
import "./styles/screen.css";
import "./styles/research.css";
import "./styles/login.css";
import "./styles/entry.css";
import "./styles/footer.css";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
);
