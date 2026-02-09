// src/components/Traveller/TrackingPanel.jsx
import { useEffect, useMemo, useCallback } from "react";
import TrackingCommonMap from "../Map/TrackingCommonMap";
import { useApp } from "../../state_imp/AppContext";
import { useTrackingSim } from "../../state_imp/sim/useTrackingSim";
import { PHASE } from "../../state_imp/constants";
import InZonePanel from "./InZonePanel";

const SECURITY_START_AREA = "Adchini";
const SECURITY_START_POINT_IDX = 4; // sample_points[4] is Adchini

function areaForIdx(idx, pointsLen, areas) {
  if (!areas?.length || !pointsLen || pointsLen < 2) return "—";
  const aIdx = Math.round((idx / (pointsLen - 1)) * (areas.length - 1));
  return areas[aIdx] || "—";
}

export default function TrackingPanel() {
  const { state, actions } = useApp();
  const plan = state.data.plan;

  // Load plan once
  useEffect(() => {
    if (plan) return;

    let alive = true;
    fetch("/demo/journey_plan_iit_sethsarai.json", { cache: "no-store" })
      .then((r) => r.json())
      .then((data) => {
        if (!alive) return;
        actions.setPlan(data);
        actions.setLiveIndex(0);
        actions.setTrackingPaused(false);
      })
      .catch((e) => console.error("Failed to load plan:", e));

    return () => {
      alive = false;
    };
  }, [plan, actions]);

  if (!plan) return <div>Loading journey…</div>;

  return <TrackingPanelLoaded plan={plan} />;
}

function TrackingPanelLoaded({ plan }) {
  const { state, actions } = useApp();

  const bookingId = state?.data?.bookingId || null;
  const phase = state?.ui?.phase;

  const points = plan.sample_points || [];
  const pointsLen = points.length || 0;
  const areas = plan.areas || [];

  // ✅ Slow down in-zone a bit (demo-friendly)
  const tickMs = phase === PHASE.IN_ZONE ? 7000 : 4000;

  const sim = useTrackingSim({
    state,
    actions,
    plan,
    securityStartIdx: SECURITY_START_POINT_IDX,
    tickMs,
  });

  const effectiveIdx = sim.liveIdx;
  const effectivePaused = sim.paused;

  const area = useMemo(
    () => areaForIdx(effectiveIdx, pointsLen, areas),
    [effectiveIdx, pointsLen, areas]
  );

  const atGate = sim.canEnterSecurity;

  const currentPoint = useMemo(() => {
    if (!pointsLen) return null;
    const safeIdx = Math.max(0, Math.min(effectiveIdx, pointsLen - 1));
    return points[safeIdx] || null;
  }, [points, pointsLen, effectiveIdx]);

  // Hard-coded gate point (as you asked)
  const BLOCK_C = { lat: 28.54433, lng: 77.19539 };

  // Polyline used for lookahead (shifted from confirm → accept)
  const polylineFinal =
    typeof plan?.polyline === "string" && plan.polyline.length > 10
      ? plan.polyline
      : "}hfmDsucvMHMROs@yDBOvCeAMe@BQLIJAp@a@N_@b@}A\\}@tAoFF[z@aDbA_Dx@kDk@Yl@wBDYsGoCqCaAH[zCjApQhHdDx@`E`A~Ar@jB`AzBr@tFzBd@TvAh@`@LdBp@xCx@zBj@ZNbCfB`@\\l@`@jD|ClAnAd@t@fEvHtGxLj@t@nDhDjA~ABJlBzA\\\\h@VrBnAb@f@e@RwCPMzKFbAJd@VVZJ|DQz@?";

  // Accept flow: trackingOnce -> lookaheadOnce -> geminiOnce (order unchanged)
  const onAcceptSecurity = useCallback(async () => {
    // 1) resume sim + enter zone
    sim.resume();
    actions.setPhase(PHASE.IN_ZONE);

    try {
      // 2) tracking update ONCE at gate (hard-coded coords)
      await actions.trackingUpdateOnce(bookingId, {
        lat: BLOCK_C.lat,
        lng: BLOCK_C.lng,
        phase: "IN_ZONE",
      });

      // 3) lookahead 500m (single shot) — shifted here
      await actions.lookaheadOnce(bookingId, {
        distance_m: 500,
        sample_fracs: [0.25, 0.6, 1],
        places_radius_m: 200,
        places_max_results: 20,
        osm_radius_m: 500,
        micro_distance_m: 100,
        store_segment_points_max: 60,
        polyline: polylineFinal,
      });

      // 4) gemini run ONCE at gate (single shot)
      await actions.geminiOnce(bookingId, {
  checkpoint: "ZONE_ENTRY",
  note: "Entered Adchini / Block C",
  max_recent_messages: 10,
});

    } catch (e) {
      console.warn("accept flow failed:", e);
    }
  }, [actions, bookingId, area, sim, polylineFinal]);

  const rightPane =
     phase === PHASE.IN_ZONE || phase === PHASE.EMERGENCY ? (
      <InZonePanel />
    ) : (
      <div
        style={{
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: 14,
          padding: 14,
          background: "rgba(255,255,255,0.03)",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 12,
            marginBottom: 10,
          }}
        >
          <div>
            <div style={{ fontSize: 12, opacity: 0.75 }}>Journey status</div>
            <div style={{ fontSize: 16, fontWeight: 600 }}>
              {atGate ? "Security gate ahead" : "Journey has started"}
            </div>
          </div>

          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 12, opacity: 0.75 }}>Current area</div>
            <div style={{ fontSize: 14, fontWeight: 600 }}>{area}</div>
          </div>
        </div>

        {!atGate && (
          <div style={{ fontSize: 13, lineHeight: 1.5, opacity: 0.9 }}>
            You have started the journey. We will stop you before entering the
            security zone.
          </div>
        )}

        {atGate && (
          <div>
            <div style={{ fontSize: 13, marginBottom: 10 }}>
              You are approaching <b>{SECURITY_START_AREA}</b>. Please accept to
              enter the security area.
            </div>

            <button
              type="button"
              disabled={!effectivePaused}
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: 12,
                border: "1px solid rgba(255,255,255,0.12)",
                background: effectivePaused
                  ? "rgba(0,0,0,0.35)"
                  : "rgba(0,0,0,0.18)",
                color: "white",
                cursor: effectivePaused ? "pointer" : "not-allowed",
                fontWeight: 600,
              }}
              onClick={onAcceptSecurity}
            >
              Accept & Enter Security Zone
            </button>
          </div>
        )}

        {phase !== PHASE.TRACKING && (
          <div style={{ fontSize: 12, opacity: 0.6, marginTop: 8 }}>
            Note: phase is <b>{phase}</b>
          </div>
        )}
      </div>
    );

  return (
    <div>
      <h3 style={{ marginTop: 0, marginBottom: 12 }}>User Screen</h3>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.6fr 1fr",
          gap: 16,
          alignItems: "start",
        }}
      >
        {/* LEFT: Map */}
        <TrackingCommonMap
          plan={plan}
          liveIdx={effectiveIdx}
          zoom={14}
          height={420}
          startLabel="Start"
          endLabel="End"
          currentLabel={phase === PHASE.IN_ZONE ? "In-Zone" : "Live"}
        />

        {/* RIGHT: status OR in-zone chat */}
        {rightPane}
      </div>
    </div>
  );
}
