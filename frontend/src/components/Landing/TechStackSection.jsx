import "./techStackSection.css";

import geminiLogo from "../../assets/logo/gemini_logo.webp";
import vertexLogo from "../../assets/logo/vertex_ai.webp";
import firebaseLogo from "../../assets/logo/firebase.webp";
import mapsLogo from "../../assets/logo/google_maps.webp";

const STACK = [
  { title: "Gemini Pro", subtitle: "Reasoning + safety decisions", logo: geminiLogo },
  { title: "Vertex AI", subtitle: "LiveEye video analysis pipeline", logo: vertexLogo },
  { title: "Firebase", subtitle: "Auth + realtime sync foundation", logo: firebaseLogo },
  { title: "Google Maps", subtitle: "Route, topology, contextual mapping", logo: mapsLogo },
];

export default function TechStackSection() {
  return (
    <section className="ts">
      <div className="ts-inner">
        <h2 className="ts-title">Built on a Modern Safety Stack</h2>
        <p className="ts-sub">
          Blackreach combines real-time mapping, AI reasoning, and a human escalation layer—without turning safety into noise.
        </p>

        <div className="ts-grid">
          {STACK.map((s) => (
            <div key={s.title} className="ts-card">
              <div className="ts-logoWrap">
                <img className="ts-logo" src={s.logo} alt={`${s.title} logo`} />
              </div>
              <div className="ts-cardTitle">{s.title}</div>
              <div className="ts-cardSub">{s.subtitle}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
