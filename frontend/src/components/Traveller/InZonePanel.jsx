// src/components/Traveller/InZonePanel.jsx
import { useEffect, useMemo, useState } from "react";
import "./inZonePanel.css";
import { useApp } from "../../state_imp/AppContext";
import { PHASE } from "../../state_imp/constants";

async function loadDemoFrameBase64() {
  // file location: frontend/public/demo/demo_frame.txt
  const res = await fetch("/demo/demo_frame.txt");
  if (!res.ok) throw new Error("Failed to load demo frame (/demo/demo_frame.txt)");
  const txt = await res.text();
  return (txt || "").trim();
}

async function postVideoEmergencyDemo({ fpsRate, note, store, frames }) {
  const res = await fetch("http://localhost:8000/video/emergency-demo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fpsRate, note, store, frames }),
  });

  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`POST /video/emergency-demo failed (${res.status}) ${txt}`);
  }
  return await res.json();
}

export default function InZonePanel() {
  const { state, actions } = useApp();

  const [answer, setAnswer] = useState(null);

  // ✅ Phase (for emergency rendering)
  const phase = state?.ui?.phase;

  // bookingId is global (set on bookingConfirm)
  const bookingId = state?.data?.bookingId || null;

  // Gemini output (arrives later, must not block UI)
  const ai = state?.data?.ai?.latest || null;

  // Risk → fps mapping (fallback safe)
  const riskColor = (ai?.riskColor || ai?.risk || "").toUpperCase();
  const fpsProfile = (ai?.fpsProfile || "").toUpperCase();

  // (Still shown in UI)
  const liveEyeNote = "BLACKREACH_LIVEEYE_DEMO_FRAME";
  const liveEyeStore = false;

  // (For hint only — backend payload uses fpsRate: 1 in this demo)
  const fpsRateHint = useMemo(() => {
    if (riskColor === "GREEN") return 15;
    if (riskColor === "ORANGE") return 24;
    if (riskColor === "RED") return 30;
    return 30;
  }, [riskColor]);

  // Local status for LiveEye "analysis"
  const [videoStatus, setVideoStatus] = useState("IDLE"); // IDLE | UPLOADING | DONE | ERROR
  const [videoResult, setVideoResult] = useState(null);
  const [videoError, setVideoError] = useState("");

  // ✅ LiveEye click behavior:
  // Loads demo frame base64 from public folder and calls backend.
 const openLiveEyePicker = async () => {
  try {
    setVideoStatus("UPLOADING");
    setVideoError("");
    setVideoResult(null);

    if (!bookingId) {
      setVideoStatus("ERROR");
      setVideoError("Missing bookingId. Confirm booking before using LiveEye.");
      return;
    }

    const rawBase64 = await loadDemoFrameBase64();
    if (!rawBase64) throw new Error("demo_frame.txt is empty");

    const result = await postVideoEmergencyDemo({
      fpsRate: 1,
      note: "User pressed emergency check",
      store: false,
      frames: [{ data_b64: rawBase64 }],
    });

    // ✅ NEW: save to global state for GeminiPanel / other UI
    actions.setGeminiVideoLatest(result);

    setVideoResult(result);
    setVideoStatus("DONE");

    const shouldTriggerEmergency =
      result?.recommendedAction === "TRIGGER_EMERGENCY" ||
      result?.isEmergency === true ||
      (typeof result?.confidence === "number" && result.confidence >= 0.6);

    if (shouldTriggerEmergency) {
      actions.setPhase(PHASE.EMERGENCY);
    }
  } catch (err) {
    setVideoStatus("ERROR");
    setVideoError(err?.message || "LiveEye failed");
  }
};


  const liveEyeHint = useMemo(() => {
    const parts = [];
    if (riskColor) parts.push(`Risk: ${riskColor}`);
    if (fpsProfile) parts.push(`FPS profile: ${fpsProfile}`);
    parts.push(`LiveEye FPS: 1 (demo frame)`);
    parts.push(`(hint: ${fpsRateHint})`);
    return parts.join(" • ");
  }, [riskColor, fpsProfile, fpsRateHint]);

  const manualEmergency = () => {
    actions.setPhase(PHASE.EMERGENCY);
  };

  // ✅ Emergency UI inside InZonePanel
  if (phase === PHASE.EMERGENCY) {
    return (
      <aside className="izp">
        <div
          style={{
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 14,
            padding: 14,
            background: "rgba(255,255,255,0.03)",
          }}
        >
          <div style={{ fontSize: 12, opacity: 0.75 }}>Emergency</div>
          <div style={{ fontSize: 18, fontWeight: 800, marginTop: 6 }}>
            Emergency activated
          </div>
          <div style={{ fontSize: 13, opacity: 0.9, lineHeight: 1.5, marginTop: 10 }}>
            Don’t worry — help is on the way.
          </div>

          {videoResult && (
            <div style={{ marginTop: 12, fontSize: 12, opacity: 0.85, lineHeight: 1.5 }}>
              <div>
                Decision:{" "}
                <b>
                  {videoResult?.recommendedAction ||
                    (videoResult?.isEmergency ? "TRIGGER_EMERGENCY" : "NONE")}
                </b>
              </div>
              <div>
                confidence:{" "}
                {typeof videoResult?.confidence === "number"
                  ? videoResult.confidence.toFixed(2)
                  : "—"}
              </div>
              {videoResult?.summary && <div style={{ marginTop: 6 }}>{videoResult.summary}</div>}
            </div>
          )}
        </div>

        <div className="izp-foot">Blackreach • Traveller</div>
      </aside>
    );
  }

  return (
    <aside className="izp">
      {/* Header */}
      <div className="izp-header">
        <div className="izp-title">
          <div className="izp-badge" />
          <span>In-Zone</span>
        </div>

        <div className="izp-icons">
          {/* LiveEye */}
          <button
            className="izp-iconBtn"
            type="button"
            aria-label="LiveEye"
            onClick={openLiveEyePicker}
            title="LiveEye (Gemini-backed decision)"
          >
            <img src="/demo/icons/eye_icon.svg" alt="LiveEye" className="izp-eye" />
          </button>

          {/* Emergency (manual override) */}
          <button
            className="izp-iconBtn izp-iconBtn--danger"
            type="button"
            aria-label="Emergency"
            title="Emergency"
            onClick={manualEmergency}
          >
            <span className="izp-siren">!</span>
          </button>
        </div>
      </div>

      {/* Small status line */}
      <div style={{ fontSize: 12, opacity: 0.75, marginTop: 2, marginBottom: 6 }}>
        {liveEyeHint}
      </div>

      {/* Chat */}
      <div className="izp-chat">
        <div className="izp-msg izp-ai">
          <div className="izp-bubble">Are you ok?</div>
        </div>

        {answer === null && (
          <div className="izp-quickRow">
            <span
              className="izp-chip"
              role="button"
              tabIndex={0}
              onClick={() => setAnswer("YES")}
              onKeyDown={(e) => e.key === "Enter" && setAnswer("YES")}
            >
              Yes
            </span>

            <span
              className="izp-chip izp-chip--danger"
              role="button"
              tabIndex={0}
              onClick={() => setAnswer("NO")}
              onKeyDown={(e) => e.key === "Enter" && setAnswer("NO")}
            >
              No
            </span>
          </div>
        )}

        {answer && (
          <div className="izp-msg izp-user">
            <div className="izp-bubble">{answer === "YES" ? "Yes" : "No"}</div>
          </div>
        )}

        {answer === "YES" && (
          <>
            <div className="izp-msg izp-ai">
              <div className="izp-bubble">You are going to enter the security zone.</div>
            </div>

            <div className="izp-msg izp-ai">
              <div className="izp-bubble">
                If anything feels wrong, press <b>LiveEye</b>. If you can’t go LiveEye, press{" "}
                <b>Emergency</b>.
              </div>
            </div>
          </>
        )}

        {answer === "NO" && (
          <div className="izp-msg izp-ai">
            <div className="izp-bubble">
              Press <b>LiveEye</b> for verification. If you can’t press LiveEye, press{" "}
              <b>Emergency</b>.
            </div>
          </div>
        )}

        {/* LiveEye feedback */}
        {videoStatus !== "IDLE" && (
          <>
            <div className="izp-msg izp-user">
              <div className="izp-bubble">
                LiveEye started
                <div style={{ fontSize: 12, opacity: 0.75, marginTop: 6 }}>
                  bookingId: {bookingId || "—"} • note: {liveEyeNote}
                </div>
              </div>
            </div>

            {videoStatus === "UPLOADING" && (
              <div className="izp-msg izp-ai">
                <div className="izp-bubble">Analyzing…</div>
              </div>
            )}

            {videoStatus === "ERROR" && (
              <div className="izp-msg izp-ai">
                <div className="izp-bubble">❌ LiveEye failed: {videoError}</div>
              </div>
            )}

            {videoStatus === "DONE" && videoResult && (
              <div className="izp-msg izp-ai">
                <div className="izp-bubble">
                  ✅ Decision:{" "}
                  <b>
                    {videoResult?.recommendedAction ||
                      (videoResult?.isEmergency ? "TRIGGER_EMERGENCY" : "NONE")}
                  </b>
                  <div style={{ fontSize: 12, opacity: 0.8, marginTop: 6 }}>
                    emergency: {String(videoResult?.isEmergency ?? "unknown")} • confidence:{" "}
                    {typeof videoResult?.confidence === "number"
                      ? videoResult.confidence.toFixed(2)
                      : "—"}
                  </div>
                  {videoResult?.summary && (
                    <div style={{ fontSize: 12, opacity: 0.85, marginTop: 6 }}>
                      {videoResult.summary}
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <div className="izp-foot">Blackreach • Traveller</div>
    </aside>
  );
}
