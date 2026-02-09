// src/components/Traveller/InZonePanel.jsx
import { useEffect, useMemo, useRef, useState } from "react";
import "./inZonePanel.css";
import { useApp } from "../../state_imp/AppContext";
import { PHASE } from "../../state_imp/constants";

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

  // ✅ Hard-coded note + store (still shown in UI)
  const liveEyeNote = "BLACKREACH_LIVEEYE_DEMO_CLIP";
  const liveEyeStore = true;

  // ✅ Hard-coded YouTube WATCH URL (more reliable than shorts)
  const LIVE_EYE_VIDEO_URL = "https://www.youtube.com/watch?v=FYt1Dqn9Lx0";

  // Green: 15, Orange: 24, Red: 30, default: 30
  const fpsRate = useMemo(() => {
    if (riskColor === "GREEN") return 15;
    if (riskColor === "ORANGE") return 24;
    if (riskColor === "RED") return 30;
    return 30;
  }, [riskColor]);

  // LiveEye demo upload (kept but optional)
  const fileInputRef = useRef(null);
  const [liveEyeFile, setLiveEyeFile] = useState(null);
  const [liveEyeUrl, setLiveEyeUrl] = useState("");

  // Local status for LiveEye "analysis" (NO BACKEND CALL)
  const [videoStatus, setVideoStatus] = useState("IDLE"); // IDLE | UPLOADING | DONE | ERROR
  const [videoResult, setVideoResult] = useState(null);
  const [videoError, setVideoError] = useState("");

  // ✅ Change LiveEye click behavior:
  // Instead of opening file picker, simulate a "virtual selection" from YouTube
  const openLiveEyePicker = () => {
    setVideoStatus("IDLE");
    setVideoResult(null);
    setVideoError("");

    // Trigger flow
    setLiveEyeFile({ name: "YouTube Demo Clip", __kind: "URL" });
    setLiveEyeUrl(LIVE_EYE_VIDEO_URL); // used for preview (iframe)
  };

  // (kept but unused now — you can remove later)
  const onPickLiveEyeFile = (e) => {
    const f = e.target.files && e.target.files[0];
    if (!f) return;

    if (!f.type || !f.type.startsWith("video/")) {
      alert("Please select a video file (mp4/mov/webm).");
      e.target.value = "";
      return;
    }

    setVideoStatus("IDLE");
    setVideoResult(null);
    setVideoError("");

    setLiveEyeFile(f);
  };

  // Create preview URL for local file ONLY
  useEffect(() => {
    if (!liveEyeFile) return;

    // ✅ If our "virtual selection" is URL-based, do nothing here.
    if (liveEyeFile.__kind === "URL") return;

    const url = URL.createObjectURL(liveEyeFile);
    setLiveEyeUrl(url);

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [liveEyeFile]);

  // ✅ NO BACKEND CALL:
  // When LiveEye triggers, we simulate a decision and (optionally) flip to EMERGENCY.
  useEffect(() => {
    if (!liveEyeFile) return;

    if (!bookingId) {
      setVideoStatus("ERROR");
      setVideoError("Missing bookingId. Confirm booking before using LiveEye.");
      return;
    }

    let cancelled = false;

    async function runLocalLiveEyeDecision() {
      try {
        setVideoStatus("UPLOADING");
        setVideoError("");
        setVideoResult(null);

        // ⏳ small delay so UI feels real
        await new Promise((r) => setTimeout(r, 1200));
        if (cancelled) return;

        // ✅ LOCAL MOCK RESULT (no API, no backend dependency)
        const mockResult = {
          recommendedAction: "TRIGGER_EMERGENCY",
          isEmergency: true,
          confidence: 0.87,
          summary: "LiveEye demo decision (local). Escalating to emergency mode.",
          note: liveEyeNote,
          store: liveEyeStore,
          source: "LOCAL_DEMO",
        };

        setVideoResult(mockResult);
        setVideoStatus("DONE");

        // ✅ This is the only global state effect we need
        const shouldTriggerEmergency =
          mockResult?.recommendedAction === "TRIGGER_EMERGENCY" ||
          mockResult?.isEmergency === true ||
          (typeof mockResult?.confidence === "number" && mockResult.confidence >= 0.6);

        if (shouldTriggerEmergency) {
          actions.setPhase(PHASE.EMERGENCY);
        }
      } catch (err) {
        if (cancelled) return;
        setVideoStatus("ERROR");
        setVideoError("LiveEye demo failed");
      }
    }

    runLocalLiveEyeDecision();

    return () => {
      cancelled = true;
    };
  }, [liveEyeFile, bookingId, actions, liveEyeNote, liveEyeStore]);

  const liveEyeHint = useMemo(() => {
    const parts = [];
    if (riskColor) parts.push(`Risk: ${riskColor}`);
    if (fpsProfile) parts.push(`FPS profile: ${fpsProfile}`);
    parts.push(`LiveEye FPS: ${fpsRate}`);
    return parts.join(" • ");
  }, [riskColor, fpsProfile, fpsRate]);

  const manualEmergency = () => {
    actions.setPhase(PHASE.EMERGENCY);
  };

  // ✅ YouTube embed url for preview
  const ytEmbedUrl = useMemo(() => {
    const m = LIVE_EYE_VIDEO_URL.match(/[?&]v=([^&]+)/);
    const id = m?.[1] || "";
    return id ? `https://www.youtube.com/embed/${id}` : "";
  }, [LIVE_EYE_VIDEO_URL]);

  // ✅ NEW: Emergency UI inside InZonePanel
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
        </div>

        <div className="izp-foot">Blackreach • Traveller</div>
      </aside>
    );
  }

  return (
    <aside className="izp">
      {/* (kept but hidden/unused now) */}
      <input
        ref={fileInputRef}
        type="file"
        accept="video/*"
        style={{ display: "none" }}
        onChange={onPickLiveEyeFile}
      />

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
            title="LiveEye (Local Demo — No Backend)"
          >
            <img src="/demo/icons/eye_icon.svg" alt="LiveEye" className="izp-eye" />
          </button>

          {/* Emergency */}
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
                If anything feels wrong, press <b>LiveEye</b>. If you can’t go LiveEye,
                press <b>Emergency</b>.
              </div>
            </div>
          </>
        )}

        {answer === "NO" && (
          <div className="izp-msg izp-ai">
            <div className="izp-bubble">
              Press <b>LiveEye</b> for recording. If you can’t press LiveEye, press{" "}
              <b>Emergency</b>.
            </div>
          </div>
        )}

        {/* LiveEye analysis feedback */}
        {liveEyeFile && (
          <>
            <div className="izp-msg izp-user">
              <div className="izp-bubble">
                LiveEye source: <b>YouTube Demo Clip</b>
                <div style={{ fontSize: 12, opacity: 0.75, marginTop: 6 }}>
                  bookingId: {bookingId || "—"} • note: {liveEyeNote}
                </div>
              </div>
            </div>

            <div className="izp-msg izp-ai">
              <div className="izp-bubble">
                LiveEye started ({fpsRate} FPS). Running local emergency decision…
              </div>
            </div>

            {videoStatus === "UPLOADING" && (
              <div className="izp-msg izp-ai">
                <div className="izp-bubble">Analyzing…</div>
              </div>
            )}

            {videoStatus === "ERROR" && (
              <div className="izp-msg izp-ai">
                <div className="izp-bubble">❌ Video analysis failed: {videoError}</div>
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

            {/* ✅ YouTube preview must be iframe, not <video> */}
            {ytEmbedUrl && (
              <div className="izp-videoWrap">
                <iframe
                  className="izp-video"
                  src={ytEmbedUrl}
                  title="LiveEye YouTube Preview"
                  frameBorder="0"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                  allowFullScreen
                />
              </div>
            )}
          </>
        )}
      </div>

      <div className="izp-foot">Blackreach • Traveller</div>
    </aside>
  );
}
