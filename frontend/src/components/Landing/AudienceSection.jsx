import { useState } from "react";
import "./audienceSection.css";

const TABS = [
  {
    key: "women",
    label: "Women & Children",
    title: "Personal Safety, Quietly Protected",
    description:
      "Blackreach monitors context silently and becomes attentive only when the journey demands it. Designed for daily commutes, late travel, and vulnerable segments.",
    points: [
      "Low-light & low-density detection",
      "Gentle attentive check-ins",
      "Instant escalation if needed",
    ],
  },
  {
    key: "traveler",
    label: "Travelers",
    title: "Confidence Across Unknown Routes",
    description:
      "Context-aware journey protection for unfamiliar cities, remote stretches, and dynamic routing environments.",
    points: [
      "Deviation-aware monitoring",
      "Live route reasoning",
      "Adaptive journey intelligence",
    ],
  },
  {
    key: "elderly",
    label: "Elderly",
    title: "Support Without Complexity",
    description:
      "Designed for clarity and calm. Blackreach reduces friction and activates support only when risk thresholds are crossed.",
    points: [
      "Clear UI transitions",
      "Escalation-ready monitoring",
      "Human-backed reassurance",
    ],
  },
  {
    key: "security",
    label: "Security Personnel",
    title: "Operational Awareness in Real-Time",
    description:
      "Blackreach provides compact reasoning briefs and contextual risk signals to enable fast and informed response.",
    points: [
      "Structured alert summaries",
      "Segment-level risk scoring",
      "Center / Subcenter activation",
    ],
  },
];

export default function AudienceSection() {
  const [active, setActive] = useState("women");

  const current = TABS.find((tab) => tab.key === active);

  return (
    <section className="audience">
      <div className="audience-inner">
        <h2 className="audience-title">
          Built for Real-World Journeys
        </h2>

        {/* Tabs */}
        <div className="audience-tabs">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              className={`audience-tab ${
                active === tab.key ? "active" : ""
              }`}
              onClick={() => setActive(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="audience-content">
          <h3>{current.title}</h3>
          <p>{current.description}</p>

          <ul>
            {current.points.map((point, i) => (
              <li key={i}>{point}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
