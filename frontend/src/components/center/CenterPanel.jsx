// src/components/center/CenterPanel.jsx
import { useEffect, useMemo } from "react";
import { useApp } from "../../state_imp/AppContext";
import TrackingCommonMap from "../Map/TrackingCommonMap";
import { PHASE } from "../../state_imp/constants";

export const SECURITY_HEAD = {
  name: "Kavya Singh",
  role: "Monitoring Supervisor",
  experienceYears: 7,
  guarantee: "Continuous monitoring + guided check-ins",
};

const ROUTE = {
  travellerName: "Adele",
  startLabel: "IIT Campus",
  endLabel: "Seth Sarai",
  securityStart: "Adchini",
  securityEnd: "Seth Sarai",
};

const SUBCENTERS = [
  {
    id: "SC-MMTC",
    name: "MMTC Community Centre (Subcenter)",
    lat: 28.5349036,
    lng: 77.2002596,
    radius_m: 300,
  },
  {
    id: "SC-MANGAL",
    name: "Mangal Sadan Community Centre (Subcenter)",
    lat: 28.5323702,
    lng: 77.1978258,
    radius_m: 300,
  },
];

// Demo target checkpoint
const TARGET_AREA = "Qila Rai Pithora";
const DEPLOY_SUBCENTER = SUBCENTERS[1]; // ✅ deploy 2nd subcenter for emergency

export default function CenterPanel() {
  const { state } = useApp();

  const plan = state?.data?.plan;

  const liveIdx = state?.sim?.liveIdx ?? 0;
  const paused = !!state?.sim?.paused;
  const phase = state?.ui?.phase;

  const geminiLoading = !!state?.ui?.loading?.gemini;
  const aiLatest = state?.data?.ai?.latest;

  const subcenterActive = !!state?.data?.subcenter?.activated;

  const booking = state?.data?.booking;
  const selectedPrice = booking?.selectedCost ?? booking?.pricing?.selected ?? "₹102";

  // Gemini risk (support a few shapes)
  const riskColor =
    aiLatest?.riskColor ||
    aiLatest?.raw?.riskColor ||
    aiLatest?.risk ||
    aiLatest?.raw?.risk ||
    null;

  const isEmergency = phase === PHASE.EMERGENCY || String(riskColor).toUpperCase() === "RED";

  // Find target point index approx from areas -> sample_points
  const targetPointIdx = useMemo(() => {
    if (!plan?.areas?.length || !plan?.sample_points?.length) return null;

    const aIdx = plan.areas.indexOf(TARGET_AREA);
    if (aIdx < 0) return null;

    const pointsLen = plan.sample_points.length;
    const areasLen = plan.areas.length;

    const approx = Math.round((aIdx / Math.max(areasLen - 1, 1)) * (pointsLen - 1));
    return Math.max(0, Math.min(approx, pointsLen - 1));
  }, [plan]);

  const reachedTarget = Boolean(isEmergency && targetPointIdx !== null && liveIdx >= targetPointIdx);

  const progress = useMemo(() => {
    if (!isEmergency || targetPointIdx === null) return 0;
    const denom = Math.max(targetPointIdx, 1);
    return Math.max(0, Math.min(100, Math.round((liveIdx / denom) * 100)));
  }, [isEmergency, liveIdx, targetPointIdx]);

  // ----------------------------
  // Center status (Ops narrative)
  // ----------------------------
  let headerText = "Live tracking in progress";
  let statusLine2 = "";

  if (!plan) {
    headerText = "Waiting for journey plan…";
    statusLine2 = "Plan will appear after traveller confirms booking.";
  } else if (isEmergency) {
    headerText = "EMERGENCY • Dispatch in motion";
    statusLine2 = `Deploying ${DEPLOY_SUBCENTER.name} toward ${TARGET_AREA}.`;
  } else if (subcenterActive) {
    headerText = "Subcenter ACTIVATED";
    statusLine2 = "Escalation running: guided check-ins + rapid response.";
  } else if (phase === PHASE.IN_ZONE) {
    headerText = "User entered Security Area";
    if (geminiLoading) statusLine2 = "Waiting for Gemini decision…";
    else if (aiLatest) statusLine2 = "Gemini response received. Monitoring continues.";
    else statusLine2 = "Gemini not triggered yet. Standing by.";
  } else if (paused) {
    headerText = "Stopped at Security Gate";
    statusLine2 = "Waiting for user acceptance to enter security area.";
  } else {
    headerText = "Live tracking in progress";
    statusLine2 = "User outside security area.";
  }

  // Optional debug snapshot
  useEffect(() => {
    console.group("🟦 CenterPanel snapshot");
    console.log("phase:", phase);
    console.log("paused:", paused);
    console.log("liveIdx:", liveIdx);
    console.log("geminiLoading:", geminiLoading);
    console.log("riskColor:", riskColor);
    console.log("isEmergency:", isEmergency);
    console.log("targetPointIdx:", targetPointIdx);
    console.log("reachedTarget:", reachedTarget);
    console.log("subcenterActive:", subcenterActive);
    console.groupEnd();
  }, [phase, paused, liveIdx, geminiLoading, riskColor, isEmergency, targetPointIdx, reachedTarget, subcenterActive]);

  return (
    <div>
      <h3 style={{ marginTop: 0, marginBottom: 12 }}>Center Room</h3>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.6fr 1fr",
          gap: 16,
          alignItems: "start",
        }}
      >
        {/* LEFT: Map */}
        <div style={{ borderRadius: 14, overflow: "hidden" }}>
          <TrackingCommonMap
            plan={plan}
            liveIdx={liveIdx}
            zoom={14}
            height={420}
            startLabel={ROUTE.startLabel}
            endLabel={ROUTE.endLabel}
            currentLabel={phase === PHASE.IN_ZONE ? "In-Zone" : "Live"}
            showSubcenters
            subcenters={SUBCENTERS}
          />
        </div>

        {/* RIGHT: Center info */}
        <div
          style={{
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 14,
            padding: 14,
            background: "rgba(255,255,255,0.03)",
          }}
        >
          {/* Emergency dispatch block */}
          {plan && isEmergency && (
            <div
              style={{
                marginBottom: 12,
                padding: 12,
                borderRadius: 12,
                border: "1px solid rgba(255,0,0,0.25)",
                background: "rgba(255,0,0,0.08)",
              }}
            >
              <div style={{ fontSize: 12, opacity: 0.9 }}>Emergency dispatch</div>
              <div style={{ fontSize: 14, fontWeight: 900, marginTop: 4 }}>
                Deploying: {DEPLOY_SUBCENTER.name}
              </div>

              <div style={{ marginTop: 6, fontSize: 12, opacity: 0.9, lineHeight: 1.45 }}>
                Gemini risk: <b>{String(riskColor || "UNKNOWN")}</b>
                {aiLatest?.brief ? <> — {aiLatest.brief}</> : null}
              </div>

              <div style={{ marginTop: 10 }}>
                <div style={{ fontSize: 12, opacity: 0.85, marginBottom: 6 }}>
                  Response moving to {TARGET_AREA} • {progress}%
                </div>
                <div style={{ height: 8, borderRadius: 999, background: "rgba(255,255,255,0.10)" }}>
                  <div
                    style={{
                      height: 8,
                      width: `${progress}%`,
                      borderRadius: 999,
                      background: "rgba(255,45,45,0.9)",
                      transition: "width 400ms ease",
                    }}
                  />
                </div>
              </div>

              {reachedTarget && (
                <div style={{ marginTop: 10, fontSize: 13, fontWeight: 900 }}>
                  ✅ User secured at {TARGET_AREA}
                </div>
              )}
            </div>
          )}

          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 12, opacity: 0.75 }}>Center status</div>
            <div style={{ fontSize: 16, fontWeight: 700 }}>{headerText}</div>

            {statusLine2 && (
              <div style={{ marginTop: 6, fontSize: 13, opacity: 0.9, lineHeight: 1.45 }}>
                {statusLine2}
              </div>
            )}

            {plan && (
              <div style={{ fontSize: 12, opacity: 0.6, marginTop: 6 }}>
                Phase: <b>{String(phase || "—")}</b> • Paused:{" "}
                <b>{paused ? "true" : "false"}</b> • liveIdx: <b>{liveIdx}</b>
              </div>
            )}
          </div>

          {!plan && (
            <div style={{ fontSize: 13, opacity: 0.9, lineHeight: 1.5 }}>
              Plan not loaded yet. Once the traveller confirms booking, the same plan will appear here automatically.
            </div>
          )}

          {plan && (
            <div style={{ marginTop: 8, fontSize: 13, lineHeight: 1.55, opacity: 0.95 }}>
              <div style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 12, opacity: 0.7 }}>Traveller</div>
                <div style={{ fontWeight: 700 }}>{ROUTE.travellerName}</div>
              </div>

              <div style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 12, opacity: 0.7 }}>Route</div>
                <div>
                  {ROUTE.startLabel} → {ROUTE.endLabel}
                </div>
              </div>

              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 12, opacity: 0.7 }}>Security coverage</div>
                <div style={{ fontWeight: 700 }}>
                  {ROUTE.securityStart} → {ROUTE.securityEnd}
                </div>
              </div>

              <div
                style={{
                  padding: 12,
                  borderRadius: 12,
                  border: "1px solid rgba(255,255,255,0.10)",
                  background: "rgba(0,0,0,0.25)",
                  marginBottom: 12,
                }}
              >
                <div style={{ fontSize: 12, opacity: 0.7 }}>Booked security price</div>
                <div style={{ fontSize: 18, fontWeight: 800 }}>{selectedPrice}</div>
                <div style={{ fontSize: 12, opacity: 0.65, marginTop: 4 }}>
                  Focused coverage from Adchini to Seth Sarai.
                </div>
              </div>

              <div
                style={{
                  padding: 12,
                  borderRadius: 12,
                  border: "1px solid rgba(255,255,255,0.10)",
                  background: "rgba(0,0,0,0.25)",
                }}
              >
                <div style={{ fontSize: 12, opacity: 0.7 }}>Monitoring lead</div>
                <div style={{ fontWeight: 800, marginTop: 2 }}>{SECURITY_HEAD.name}</div>
                <div style={{ fontSize: 12, opacity: 0.85 }}>{SECURITY_HEAD.role}</div>
                <div style={{ fontSize: 12, opacity: 0.65, marginTop: 6 }}>
                  Guarantee: {SECURITY_HEAD.guarantee}
                </div>
              </div>

              {subcenterActive && (
                <div style={{ fontSize: 12, opacity: 0.75, marginTop: 10 }}>
                  ✅ Subcenter: <b>active</b>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
