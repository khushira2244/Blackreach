// src/components/Gemini/GeminiPanel.jsx
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

function TitleChip({ children, danger }) {
  return (
    <span className={`gp-chip ${danger ? "gp-chip--danger" : ""}`}>{children}</span>
  );
}

export default function GeminiPanel() {
  const { state } = useApp();

  const phase = state?.ui?.phase;
  const geminiLoading = !!state?.ui?.loading?.gemini;

  const lookahead = state?.data?.lookahead?.latest ?? null;

  // ✅ Zone-entry reasoning (text gemini)
  const aiLatest = state?.data?.ai?.latest ?? null;

  // ✅ LiveEye / Gemini Video emergency result
  const geminiVideo = state?.data?.geminiVideo?.latest ?? null;

  const isEmergency = phase === PHASE.EMERGENCY;

  // Input should come from aiLatest (ZONE_ENTRY)
  const geminiInput =
    aiLatest?.geminiInput ?? state?.data?.ai?.lastInput ?? null;

  // Output for aiLatest: hide geminiInput/raw
  const aiOutput = useMemo(() => {
    if (!aiLatest || typeof aiLatest !== "object") return aiLatest;
    const { geminiInput: _gi, raw: _raw, ...rest } = aiLatest;
    return rest;
  }, [aiLatest]);

  const phaseMessage = useMemo(() => {
    if (isEmergency) return "Emergency mode: LiveEye result displayed (from state).";
    if (geminiLoading) return "Gemini is building security context…";
    if (!aiLatest) return "Context will appear once Gemini runs.";
    return "Gemini context is ready.";
  }, [isEmergency, geminiLoading, aiLatest]);

  // show full panels in-zone OR emergency (same behavior as before)
  const showFullPanels = phase === PHASE.IN_ZONE || isEmergency;

  // ✅ decoded chips for ai output (zone reasoning)
  const decodedZone = useMemo(() => {
    if (!aiOutput || typeof aiOutput !== "object") return null;
    return {
      riskColor: aiOutput.riskColor || aiOutput.risk,
      fpsProfile: aiOutput.fpsProfile,
      confidence: aiOutput.confidence,
      recommendedAction: aiOutput.recommendedAction,
      brief: aiOutput.brief,
      reasons: Array.isArray(aiOutput.reasons) ? aiOutput.reasons : [],
    };
  }, [aiOutput]);

  // ✅ decoded LiveEye / video emergency
  const decodedVideo = useMemo(() => {
    if (!geminiVideo || typeof geminiVideo !== "object") return null;
    return {
      isEmergency: geminiVideo.isEmergency,
      confidence: geminiVideo.confidence,
      recommendedAction: geminiVideo.recommendedAction,
      signals: Array.isArray(geminiVideo.signals) ? geminiVideo.signals : [],
      summary: geminiVideo.summary,
      at: geminiVideo.at,
    };
  }, [geminiVideo]);

  return (
    <section className="gp">
      {/* Header */}
      <div className="gp-header">
        <div className="gp-title">Gemini Reasoning</div>
        <div className="gp-sub">{phaseMessage}</div>

        <div style={{ marginTop: 8, fontSize: 12, opacity: 0.75 }}>
          Phase: <b>{String(phase || "—")}</b>
          {" • Gemini: "}
          <b>{geminiLoading ? "running" : "idle"}</b>
          {" • LiveEye: "}
          <b>{decodedVideo ? "ready" : "—"}</b>
        </div>
      </div>

      {/* Not in-zone and not emergency */}
      {!showFullPanels && (
        <div className="gp-body">
          <div className="gp-card" style={{ width: "100%" }}>
            <div className="gp-label">Security context</div>
            <div style={{ fontSize: 13, opacity: 0.9, lineHeight: 1.5 }}>
              We will generate Gemini reasoning once the user enters the security area.
              <br />
              Current phase: <b>{String(phase || "—")}</b>
            </div>

            {aiLatest && (
              <>
                <div style={{ height: 10 }} />
                <div className="gp-label">Last Gemini snapshot</div>
                <pre className="gp-pre">{pretty(aiOutput)}</pre>
              </>
            )}
          </div>
        </div>
      )}

      {/* In-zone or Emergency */}
      {showFullPanels && (
        <div className="gp-body">
          {/* LEFT — Input */}
          <div className="gp-col gp-input">
            <div className="gp-col-title">Input</div>

            <div className="gp-card" style={{ marginBottom: 12 }}>
              <div className="gp-label">Gemini Input (from backend)</div>
              <pre className="gp-pre">
                {geminiInput ? pretty(geminiInput) : "No geminiInput received yet"}
              </pre>
            </div>

            <div className="gp-card">
              <div className="gp-label">Lookahead</div>
              <pre className="gp-pre">
                {lookahead ? pretty(lookahead) : "No lookahead data yet"}
              </pre>
            </div>
          </div>

          {/* RIGHT — Output */}
          <div className="gp-col gp-output">
            <div className="gp-col-title">Output</div>

            {/* ✅ LiveEye / Video Emergency card (if exists) */}
            {decodedVideo && (
              <div className="gp-card" style={{ marginBottom: 12 }}>
                <div className="gp-label">LiveEye Emergency (Gemini Video)</div>

                <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 8 }}>
                  <TitleChip danger={decodedVideo.isEmergency === true}>
                    Emergency: {String(decodedVideo.isEmergency)}
                  </TitleChip>

                  {typeof decodedVideo.confidence === "number" && (
                    <TitleChip>
                      Confidence: {(decodedVideo.confidence * 100).toFixed(0)}%
                    </TitleChip>
                  )}

                  {decodedVideo.recommendedAction && (
                    <TitleChip danger>
                      Action: {String(decodedVideo.recommendedAction)}
                    </TitleChip>
                  )}
                </div>

                {decodedVideo.summary && (
                  <div style={{ marginTop: 10, fontSize: 13, opacity: 0.9, lineHeight: 1.5 }}>
                    <b>Summary:</b> {decodedVideo.summary}
                  </div>
                )}

                {decodedVideo.signals?.length > 0 && (
                  <div style={{ marginTop: 10 }}>
                    <div style={{ fontSize: 12, opacity: 0.75, marginBottom: 6 }}>
                      Signals
                    </div>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      {decodedVideo.signals.map((s) => (
                        <span key={s} className="gp-chip gp-chip--danger">
                          {String(s).replaceAll("_", " ")}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Keep raw for debug */}
                <div style={{ height: 10 }} />
                <div className="gp-label">Raw</div>
                <pre className="gp-pre">{pretty(geminiVideo)}</pre>
              </div>
            )}

            {/* ✅ Zone reasoning (AI_UPDATED) */}
            <div className="gp-card">
              <div className="gp-label">Gemini Zone Reasoning</div>

              {/* Decoded UI */}
              {decodedZone && (
                <div style={{ marginTop: 8 }}>
                  <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                    {decodedZone.riskColor && (
                      <TitleChip danger={String(decodedZone.riskColor).toUpperCase() === "RED"}>
                        Risk: {String(decodedZone.riskColor)}
                      </TitleChip>
                    )}
                    {decodedZone.fpsProfile && (
                      <TitleChip>FPS: {String(decodedZone.fpsProfile)}</TitleChip>
                    )}
                    {typeof decodedZone.confidence === "number" && (
                      <TitleChip>
                        Confidence: {(decodedZone.confidence * 100).toFixed(0)}%
                      </TitleChip>
                    )}
                    {decodedZone.recommendedAction && (
                      <TitleChip danger={String(decodedZone.recommendedAction).includes("ESCALATE")}>
                        Action: {String(decodedZone.recommendedAction)}
                      </TitleChip>
                    )}
                  </div>

                  {decodedZone.brief && (
                    <div
                      style={{
                        marginTop: 10,
                        fontSize: 13,
                        opacity: 0.9,
                        lineHeight: 1.5,
                      }}
                    >
                      <b>Brief:</b> {decodedZone.brief}
                    </div>
                  )}

                  {decodedZone.reasons?.length > 0 && (
                    <div style={{ marginTop: 10 }}>
                      <div style={{ fontSize: 12, opacity: 0.75, marginBottom: 6 }}>
                        Reasons
                      </div>
                      <ul
                        style={{
                          margin: 0,
                          paddingLeft: 18,
                          fontSize: 13,
                          opacity: 0.9,
                          lineHeight: 1.5,
                        }}
                      >
                        {decodedZone.reasons.map((r, idx) => (
                          <li key={`${idx}-${r}`}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Raw output */}
              <div style={{ height: 10 }} />
              <div className="gp-label">Raw</div>
              <pre className="gp-pre">
                {aiLatest ? pretty(aiOutput) : "Waiting for Gemini reasoning…"}
              </pre>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
