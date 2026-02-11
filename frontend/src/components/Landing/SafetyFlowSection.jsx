import "./safetyFlowSection.css";

const FLOW = [
  {
    k: "passive",
    step: "01",
    title: "Passive Vigilance",
    desc:
      "Runs silently in the background. Tracks journey intent and progress without interrupting the traveler.",
    bullets: ["Low monitoring frequency", "No unnecessary alerts", "Invisible in normal zones"],
    icon: "🟢",
  },
  {
    k: "attentive",
    step: "02",
    title: "Attentive Mode",
    desc:
      "Activates in flagged segments (low light, low transit, remote stretches) and checks in calmly—no panic UX.",
    bullets: ["Sensitive-area entry", "Gentle check-ins", "Traveler stays in control"],
    icon: "🟡",
  },
  {
    k: "reasoning",
    step: "03",
    title: "Gemini Reasoning Layer",
    desc:
      "Real-time context building + lookahead. Evaluates the next segment and produces explainable safety decisions.",
    bullets: ["500m lookahead", "Topology + place density", "Deviation-aware risk scoring"],
    icon: "🟣",
  },
  {
    k: "escalation",
    step: "04",
    title: "Escalation & Human Support",
    desc:
      "When risk crosses threshold, Blackreach switches to emergency mode and routes a compact brief to responders.",
    bullets: ["Deterministic UI switch", "Center/Subcenter activation", "Human-in-the-loop action"],
    icon: "🔴",
  },
];

export default function SafetyFlowSection() {
  return (
    <section className="sf">
      <div className="sf-inner">
        <div className="sf-head">
          <h2 className="sf-title">Intelligent Safety That Adapts to Every Journey</h2>
          <p className="sf-sub">
            Blackreach stays quiet when everything is normal  and becomes attentive only when context
            demands it.
          </p>
        </div>

        <div className="sf-grid">
          {FLOW.map((x) => (
            <article key={x.k} className="sf-card">
              <div className="sf-cardTop">
                <div className="sf-icon" aria-hidden="true">
                  {x.icon}
                </div>

                <div className="sf-step">{x.step}</div>
              </div>

              <h3 className="sf-cardTitle">{x.title}</h3>
              <p className="sf-cardDesc">{x.desc}</p>

              <ul className="sf-list">
                {x.bullets.map((b) => (
                  <li key={b} className="sf-li">
                    <span className="sf-dot" aria-hidden="true" />
                    <span>{b}</span>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
