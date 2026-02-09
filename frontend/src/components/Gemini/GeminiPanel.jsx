import { useMemo } from "react";
import { useApp } from "../../state_imp/AppContext";
import { PHASE } from "../../state_imp/constants";
import "./geminiPanel.css";

function pretty(x) {
  try {
    if (x === null || x === undefined) return "";
    if (typeof x === "string") return x;
    return JSON.stringify(x, null, 2);
  } catch {
    return String(x);
  }
}

/**
 * EMERGENCY DEMO SNAPSHOT (hardcoded)
 * - Used only when phase === PHASE.EMERGENCY
 * - No API calls required: panel renders from these objects
 */
const DEMO_AI_EMERGENCY = {
  riskColor: "RED",
  fpsProfile: "HIGH_ALERT",
  recommendedAction: "TRIGGER_EMERGENCY",
  confidence: 0.87,
  brief: "High-risk zone detected. Immediate intervention recommended.",
  reasons: [
    "Low visibility corridor",
    "Historical incident density high",
    "User entered forest-adjacent stretch",
  ],
  geminiInput: {
    checkpoint: "EMERGENCY_OVERRIDE",
    zone: "Block C → Qila Rai Pithora",
    source: "LiveEye / Manual trigger",
  },
};

const DEMO_LOOKAHEAD = {
  segment: "Block C",
  riskScore: 0.81,
  hotspots: ["Unlit road", "Low footfall"],
  recommendation: "Escalate to emergency",
};

export default function GeminiPanel() {
  const { state } = useApp();

  const phase = state?.ui?.phase;
  const geminiLoading = !!state?.ui?.loading?.gemini;

  const lookahead = state?.data?.lookahead?.latest ?? null;
  const aiLatest = state?.data?.ai?.latest ?? null;

  const isEmergency = phase === PHASE.EMERGENCY;

  // When in EMERGENCY: override everything with hardcoded demo context
  const effectiveAiLatest = isEmergency ? DEMO_AI_EMERGENCY : aiLatest;
  const effectiveLookahead = isEmergency ? DEMO_LOOKAHEAD : lookahead;

  // Backend-provided context (new key) OR demo geminiInput
  const geminiInput = isEmergency
    ? DEMO_AI_EMERGENCY.geminiInput
    : effectiveAiLatest?.geminiInput ?? null;

  // Cleaner output view: hide raw + geminiInput from the output box
  const aiOutput = useMemo(() => {
    if (!effectiveAiLatest || typeof effectiveAiLatest !== "object") return effectiveAiLatest;
    const { geminiInput: _gi, raw: _raw, ...rest } = effectiveAiLatest;
    return rest;
  }, [effectiveAiLatest]);

  // Simple phase-aligned messaging (safe even if you add more phases)
  const phaseMessage = useMemo(() => {
    if (isEmergency) return "Emergency mode: demo context loaded (no API calls).";
    if (geminiLoading) return "Gemini is building security context…";
    if (!effectiveAiLatest) return "Context will appear once Gemini runs.";
    return "Gemini context is ready.";
  }, [isEmergency, geminiLoading, effectiveAiLatest]);

  // In EMERGENCY we still want the full panels visible (like in-zone)
  const showFullPanels = phase === PHASE.IN_ZONE || isEmergency;

  return (
    <section className="gp">
      {/* Header (always visible) */}
      <div className="gp-header">
        <div className="gp-title">Gemini Reasoning</div>
        <div className="gp-sub">{phaseMessage}</div>

        <div style={{ marginTop: 8, fontSize: 12, opacity: 0.75 }}>
          Phase: <b>{String(phase || "—")}</b>
          {" • Gemini: "}
          <b>{isEmergency ? "disabled" : geminiLoading ? "running" : "idle"}</b>
        </div>
      </div>

      {/* If not in-zone (and not emergency), keep it calm and simple */}
      {!showFullPanels && (
        <div className="gp-body">
          <div className="gp-card" style={{ width: "100%" }}>
            <div className="gp-label">Security context</div>
            <div style={{ fontSize: 13, opacity: 0.9, lineHeight: 1.5 }}>
              We will generate Gemini reasoning once the user enters the security area.
              <br />
              Current phase: <b>{String(phase || "—")}</b>
            </div>

            {/* Optional: show last known output if exists (non-blocking) */}
            {effectiveAiLatest && (
              <>
                <div style={{ height: 10 }} />
                <div className="gp-label">Last Gemini snapshot</div>
                <pre className="gp-pre">{pretty(aiOutput)}</pre>
              </>
            )}
          </div>
        </div>
      )}

      {/* In-zone or Emergency: show Input left, Output right */}
      {showFullPanels && (
        <div className="gp-body">
          {/* LEFT — Input */}
          <div className="gp-col gp-input">
            <div className="gp-col-title">Input</div>

            <div className="gp-card" style={{ marginBottom: 12 }}>
              <div className="gp-label">
                Gemini Input {isEmergency ? "(demo / hardcoded)" : "(from backend)"}
              </div>
              <pre className="gp-pre">
                {geminiInput ? pretty(geminiInput) : "No geminiInput received yet"}
              </pre>
            </div>

            <div className="gp-card">
              <div className="gp-label">Lookahead {isEmergency ? "(demo)" : ""}</div>
              <pre className="gp-pre">
                {effectiveLookahead ? pretty(effectiveLookahead) : "No lookahead data yet"}
              </pre>
            </div>
          </div>

          {/* RIGHT — Output */}
          <div className="gp-col gp-output">
            <div className="gp-col-title">Output</div>

            <div className="gp-card">
              <div className="gp-label">Gemini Analysis {isEmergency ? "(demo)" : ""}</div>
              <pre className="gp-pre">
                {effectiveAiLatest ? pretty(aiOutput) : "Waiting for Gemini reasoning…"}
              </pre>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
