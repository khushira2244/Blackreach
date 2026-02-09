// src/state_imp/AppContext.js
import React, {
  createContext,
  useContext,
  useReducer,
  useRef,
  useMemo,
} from "react";

import { initialState } from "./initialState";
import { reducer, ACTIONS } from "./reducer";
import { DEMO_MODE, VIEW, PHASE, BOOKING_STEP } from "./constants";
import { createOrchestrator } from "../services/orchestrators";

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  // Keep latest state available to actions (avoid stale closures)
  const stateRef = useRef(state);
  stateRef.current = state;
  const getState = () => stateRef.current;

  // Create orchestrator once
  const orchestrator = useMemo(() => {
    return createOrchestrator({ getState, dispatch });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const actions = useMemo(
    () => ({
      // ---------------------------
      // UI / State actions
      // ---------------------------
      setActor: (actor) =>
        dispatch({ type: ACTIONS.SET_ACTOR, payload: actor }),

      setView: (view) =>
        dispatch({ type: ACTIONS.SET_VIEW, payload: view }),

      setDemoMode: (mode) =>
        dispatch({ type: ACTIONS.SET_DEMO_MODE, payload: mode }),

      setPhase: (phase) =>
        dispatch({ type: ACTIONS.SET_PHASE, payload: phase }),

      setBookingStep: (step) =>
        dispatch({ type: ACTIONS.SET_BOOKING_STEP, payload: step }),

      // Global journey plan
      setPlan: (plan) =>
        dispatch({ type: ACTIONS.SET_PLAN, payload: plan }),

      // Controls
      setActiveSliceIndex: (idx) =>
        dispatch({ type: ACTIONS.SET_ACTIVE_SLICE_INDEX, payload: idx }),

      // Sim controls (needed by TrackingPanel + useTrackingSim)
      setLiveIndex: (idx) =>
        dispatch({ type: ACTIONS.SET_LIVE_INDEX, payload: idx }),

      setTrackingPaused: (paused) =>
        dispatch({ type: ACTIONS.SET_TRACKING_PAUSED, payload: paused }),

      setRunFlag: (key, value) =>
        dispatch({ type: ACTIONS.SET_RUN_FLAG, payload: { key, value } }),

      /**
       * Start tracking:
       * - moves phase to TRACKING
       * - unpauses sim
       * ✅ does NOT touch chat (reducer decides chat lock/unlock)
       */
      startTracking: () => {
        dispatch({ type: ACTIONS.SET_PHASE, payload: PHASE.TRACKING });
        dispatch({ type: ACTIONS.SET_TRACKING_PAUSED, payload: false });
      },

      /**
       * Enter Security Zone:
       * - moves phase to IN_ZONE
       * - reducer can unlock chat here (only here)
       * - optionally open chat UI
       */
      enterZone: () => {
        dispatch({ type: ACTIONS.SET_PHASE, payload: PHASE.IN_ZONE });

        // optionally open chat UI (only if your reducer supports it)
        // dispatch({ type: ACTIONS.SET_CHAT_OPEN, payload: true });
      },

      /**
       * Watch Demo:
       * - prepares state only
       * - no loops, no APIs
       */
      watchDemo: () => {
        const s = getState();
        if (s?.ui?.run?.demoStarted) return;

        dispatch({ type: ACTIONS.SET_DEMO_MODE, payload: DEMO_MODE.WATCH_DEMO });
        dispatch({ type: ACTIONS.SET_VIEW, payload: VIEW.SCREEN_HOME });
        dispatch({ type: ACTIONS.SET_PHASE, payload: PHASE.BOOKED });
        dispatch({ type: ACTIONS.SET_BOOKING_STEP, payload: BOOKING_STEP.FORM });

        dispatch({
          type: ACTIONS.SET_RUN_FLAG,
          payload: { key: "demoStarted", value: true },
        });
      },

      // ---------------------------
      // Orchestrator API calls
      // ---------------------------
      bookingConfirm: (payload) => orchestrator.bookingConfirm(payload),
      hydrateCase: (bookingId) => orchestrator.hydrateCase(bookingId),
      hydrateChat: (bookingId) => orchestrator.hydrateChat(bookingId),

      trackingUpdateOnce: (bookingId, payload) =>
        orchestrator.trackingUpdateOnce(bookingId, payload),

      lookaheadOnce: (bookingId, payload) =>
        orchestrator.lookaheadOnce(bookingId, payload),

      geminiOnce: (bookingId, payload, opts) =>
        orchestrator.geminiOnce(bookingId, payload, opts),

      resolveCaseApi: (bookingId) => orchestrator.resolveCase(bookingId),
    }),
    [orchestrator]
  );

  return (
    <AppContext.Provider value={{ state, dispatch, actions }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used inside AppProvider");
  return ctx;
}
