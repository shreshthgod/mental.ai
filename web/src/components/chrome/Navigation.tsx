import { useEffect, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";

const LINKS = [
  { to: "/screen", label: "Screen" },
  { to: "/research", label: "Research" },
  { to: "/research#method", label: "Methodology", hash: "method" },
  { to: "/#limits", label: "About", hash: "limits" },
];

export function Navigation({ introSettled = true }: { introSettled?: boolean }) {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => setOpen(false), [location.pathname]);

  const go = (to: string, hash?: string) => (e: React.MouseEvent) => {
    e.preventDefault();
    setOpen(false);
    const [path] = to.split("#");
    if (hash && location.pathname === (path || "/")) {
      document.getElementById(hash)?.scrollIntoView({ behavior: "smooth" });
    } else {
      navigate(path || "/");
      if (hash) setTimeout(() => document.getElementById(hash)?.scrollIntoView({ behavior: "smooth" }), 350);
    }
  };

  return (
    <>
      <header className={`nav ${scrolled ? "nav--scrolled" : ""} ${introSettled ? "" : "nav--hidden-intro"}`}>
        <Link to="/" className="nav__wordmark" aria-label="Vantage home">
          Vantage
        </Link>
        <nav className="nav__links" aria-label="Primary">
          {LINKS.map((l) =>
            l.hash ? (
              <a key={l.label} href={l.to} className="nav__link" onClick={go(l.to, l.hash)}>
                {l.label}
              </a>
            ) : (
              <NavLink key={l.label} to={l.to} className={({ isActive }) => `nav__link ${isActive ? "nav__link--active" : ""}`}>
                {l.label}
              </NavLink>
            )
          )}
          <Link to="/screen" className="nav__cta">
            Start
          </Link>
        </nav>
        <button className="nav__burger" onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-controls="nav-overlay">
          {open ? "Close" : "Menu"}
        </button>
      </header>
      <div id="nav-overlay" className={`nav__overlay ${open ? "nav__overlay--open" : ""}`} aria-hidden={!open}>
        <Link to="/" onClick={() => setOpen(false)}>Home</Link>
        <Link to="/screen" onClick={() => setOpen(false)}>Screen</Link>
        <Link to="/research" onClick={() => setOpen(false)}>Research</Link>
        <a href="/research#method" onClick={go("/research", "method")}>Methodology</a>
        <a href="/#limits" onClick={go("/", "limits")}>About</a>
      </div>
    </>
  );
}
