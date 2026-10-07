import { Link } from "react-router-dom";
import { SystemStatus } from "./SystemStatus";

export function Footer() {
  return (
    <footer className="footer">
      <div className="footer__inner">
        <div className="footer__top">
          <div>
            <p className="footer__brand">MENTAL.AI</p>
            <p className="footer__desc">
              AI-assisted mental health screening research system. Dual-model NLP
              pipeline producing screening signals for human review - not a
              clinical diagnostic tool.
            </p>
          </div>
          <div className="footer__cols">
            <div className="footer__col">
              <span className="label">System</span>
              <ul>
                <li><Link to="/screen">Screen</Link></li>
                <li><Link to="/research">Research</Link></li>
              </ul>
            </div>
            <div className="footer__col">
              <span className="label">Project</span>
              <ul>
                <li><Link to="/research">Methodology</Link></li>
                <li><Link to="/research#limitations">Limitations</Link></li>
                <li><Link to="/research#repro">Reproducibility</Link></li>
              </ul>
            </div>
          </div>
        </div>
        <div className="footer__base">
          <p>Mental health screening research pipeline · Phase 1 · v0.1.0</p>
          <SystemStatus compact />
        </div>
      </div>
    </footer>
  );
}
