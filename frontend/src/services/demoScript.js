// src/services/demoScript.js

import { ACTIONS } from "../state_imp/reducer";
import { CHAT_MODE, CASE_STATE } from "../state_imp/constants";

/**
 * demoScript
 * - Deterministic "judge movie director" for WATCH_DEMO
 * - Emits the SAME reducer actions used in LIVE mode
 * - No backend calls, no UI logic
 */
export const demoScript = (() => {
  let timers = [];
  let running = false;

  function clearAll() {
    timers.forEach((t) => clearTimeout(t));
    timers = [];
  }

  function schedule(ms, fn) {
    const id = setTimeout(() => {
      if (!running) return;
      fn();
    }, ms);
    timers.push(id);
  }

  function start({ dispatch, getState }) {
    stop(); // reset if already running
    running = true;

    const nowIso = () => new Date().toISOString();
    const bookingId = `demo_${Math.random().toString(16).slice(2)}_${Date.now()}`;

    // ─────────────────────────────
    // Scene 1: BOOKED
    // ─────────────────────────────
    schedule(0, () => {
      dispatch({
        type: ACTIONS.BOOKING_CONFIRMED,
        payload: {
          bookingId,
          case: {
            bookingId, // ✅ fix #1
            state: CASE_STATE.ACTIVE,
            createdAt: nowIso(),
            subcenter: {
              activated: false,
              subcenter_id: null,
              activatedAt: null,
              note: null,
            },
          },
          chat: {
            bookingId, // ✅ fix #4 (baseline)
            mode: CHAT_MODE.LOCKED,
            messages: [
              {
                at: nowIso(),
                sender: "system", // ✅ fix #2
                text: "Demo started. Tracking will begin shortly.",
              },
            ],
          },
        },
      });

      dispatch({ type: ACTIONS.DERIVE_PHASE_FROM_DATA });
    });

    // ─────────────────────────────
    // Scene 2: TRACKING ticks (dot moves)
    // ─────────────────────────────
    const base = { lat: 23.3441, lng: 85.3096 };
    let step = 0;

    function emitTrackingTick() {
      const liveLatest = {
        at: nowIso(),
        lat: base.lat + step * 0.00015,
        lng: base.lng + step * 0.00018,
        speed_kmh: 18 + (step % 4),
        eta_s: Math.max(0, 900 - step * 18),
      };

      dispatch({ type: ACTIONS.LIVE_UPDATED, payload: liveLatest });
      dispatch({ type: ACTIONS.DERIVE_PHASE_FROM_DATA });

      step += 1;

      if (running && step < 40) {
        schedule(1500, emitTrackingTick);
      }
    }

    schedule(1200, emitTrackingTick);

    // ─────────────────────────────
    // Scene 3: ZONE ENTRY (unlock chat + mark IN_ZONE)
    // ─────────────────────────────
    schedule(9000, () => {
      const prevCase = getState()?.data?.case || {};

      dispatch({
        type: ACTIONS.CASE_UPDATED,
        payload: {
          ...prevCase,
          bookingId, // keep stable
          state: CASE_STATE.IN_ZONE,
          zoneEnteredAt: nowIso(),
        },
      });

      const prevMsgs = getState()?.data?.chat?.messages || [];

      dispatch({
        type: ACTIONS.CHAT_UPDATED,
        payload: {
          bookingId, // ✅ fix #4
          mode: CHAT_MODE.AI_ACTIVE,
          messages: [
            ...prevMsgs,
            {
              at: nowIso(),
              sender: "system", // ✅ fix #2
              text: "Zone entered. AI guidance is now active.",
            },
            {
              at: nowIso(),
              sender: "ai", // ✅ fix #2
              text: "I’m watching ahead. If you feel uneasy, tap UNEASY.",
            },
          ],
        },
      });

      dispatch({
        type: ACTIONS.AI_UPDATED,
        payload: {
          at: nowIso(),
          bookingId,
          checkpoint: "ZONE_ENTRY",
          riskColor: "GREEN",
          fpsProfile: "LOW",
          subcenterAdvice: "NONE",
          reasons: ["Entered monitored zone", "No anomalies detected yet"],
        },
      });

      dispatch({ type: ACTIONS.DERIVE_PHASE_FROM_DATA });
    });

    // ─────────────────────────────
    // Scene 4: IN_ZONE loop (lookahead → gemini tick)
    // ─────────────────────────────
    function emitInZoneTick(tick) {
      const riskCycle = tick < 2 ? "GREEN" : tick < 4 ? "ORANGE" : "RED";
      const fpsCycle = tick < 2 ? "LOW" : tick < 4 ? "MEDIUM" : "HIGH"; // ✅ fix #3
      const advice = tick < 4 ? "NONE" : "ACTIVATE";

      const live = getState()?.data?.live?.latest;
      const endPoint = live
        ? { lat: live.lat + 0.0006, lng: live.lng + 0.0006 }
        : { lat: base.lat + 0.001, lng: base.lng + 0.001 };

      dispatch({
        type: ACTIONS.LOOKAHEAD_UPDATED,
        payload: {
          at: nowIso(),
          bookingId,
          distance_m: 500,
          end_point: endPoint, // ✅ fix #6
          places_summary:
            tick < 2
              ? "Normal street, low crowd"
              : tick < 4
              ? "Crowd increasing near junction"
              : "Unusual clustering detected ahead",
          samples: [{}, {}, {}],
        },
      });

      dispatch({
        type: ACTIONS.AI_UPDATED,
        payload: {
          at: nowIso(),
          bookingId,
          checkpoint: "TRACK_TICK",
          riskColor: riskCycle,
          fpsProfile: fpsCycle,
          subcenterAdvice: advice,
          reasons:
            riskCycle === "GREEN"
              ? ["Routine conditions"]
              : riskCycle === "ORANGE"
              ? ["Crowd density rising", "Reduced visibility ahead"]
              : ["High anomaly score", "Recommend human readiness"],
        },
      });

      // ✅ fix #5: full subcenter object on activate
      if (advice === "ACTIVATE") {
        const prevCase = getState()?.data?.case || {};
        dispatch({
          type: ACTIONS.CASE_UPDATED,
          payload: {
            ...prevCase,
            bookingId,
            subcenter: {
              activated: true,
              subcenter_id: "SC-01",
              activatedAt: nowIso(),
              note: "Activated by demo",
            },
          },
        });
      }

      dispatch({ type: ACTIONS.DERIVE_PHASE_FROM_DATA });

      if (running && tick < 6) {
        schedule(6000, () => emitInZoneTick(tick + 1));
      }
    }

    schedule(11000, () => emitInZoneTick(0));

    // ─────────────────────────────
    // Scene 5: EMERGENCY escalation (human takeover)
    // ─────────────────────────────
    schedule(42000, () => {
      const prevCase = getState()?.data?.case || {};
      const prevMsgs = getState()?.data?.chat?.messages || [];

      dispatch({
        type: ACTIONS.CASE_UPDATED,
        payload: {
          ...prevCase,
          bookingId,
          state: CASE_STATE.EMERGENCY,
          emergencyAt: nowIso(),
          subcenter: {
            activated: true,
            subcenter_id: "SC-01",
            activatedAt: nowIso(),
            note: "Activated by demo emergency",
          },
        },
      });

      dispatch({
        type: ACTIONS.CHAT_UPDATED,
        payload: {
          bookingId, // ✅ fix #4
          mode: CHAT_MODE.HUMAN_ACTIVE,
          messages: [
            ...prevMsgs,
            {
              at: nowIso(),
              sender: "system", // ✅ fix #2
              text: "Emergency detected. Human team is taking over.",
            },
          ],
        },
      });

      dispatch({
        type: ACTIONS.AI_UPDATED,
        payload: {
          at: nowIso(),
          bookingId,
          checkpoint: "EMERGENCY_CHECK",
          riskColor: "RED",
          fpsProfile: "HIGH",
          subcenterAdvice: "ACTIVATE",
          reasons: ["User emergency signal", "High anomaly score persists"],
        },
      });

      dispatch({ type: ACTIONS.DERIVE_PHASE_FROM_DATA });
    });

    // ─────────────────────────────
    // Scene 6: RESOLVED
    // ─────────────────────────────
    schedule(56000, () => {
      const prevCase = getState()?.data?.case || {};
      const prevMsgs = getState()?.data?.chat?.messages || [];

      dispatch({
        type: ACTIONS.CASE_UPDATED,
        payload: {
          ...prevCase,
          bookingId,
          state: CASE_STATE.RESOLVED,
          resolvedAt: nowIso(),
        },
      });

      dispatch({
        type: ACTIONS.CHAT_UPDATED,
        payload: {
          bookingId, // ✅ fix #4
          mode: CHAT_MODE.LOCKED,
          messages: [
            ...prevMsgs,
            {
              at: nowIso(),
              sender: "system", // ✅ fix #2
              text: "Case resolved. Demo complete.",
            },
          ],
        },
      });

      dispatch({
        type: ACTIONS.AI_UPDATED,
        payload: {
          at: nowIso(),
          bookingId,
          checkpoint: "FINAL",
          riskColor: "GREEN",
          fpsProfile: "LOW",
          subcenterAdvice: "NONE",
          reasons: ["Situation stabilized", "Case closed successfully"],
        },
      });

      dispatch({ type: ACTIONS.DERIVE_PHASE_FROM_DATA });
    });
  }

  function stop() {
    running = false;
    clearAll();
  }

  return { start, stop };
})();
