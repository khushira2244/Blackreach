// src/state/initialState.js

import {
  APP_MODE,
  DEMO_MODE,
  PHASE,
  CHAT_MODE,
  ACTOR,
  VIEW,
  BOOKING_STEP,
} from "./constants";

export const initialState = {
  // ─────────────────────────────
  // App-level configuration
  // ─────────────────────────────
  app: {
    actor: ACTOR.ADELE,
    appMode: APP_MODE.SECURITY,
    demoMode: DEMO_MODE.NONE, // demo starts only after explicit click
  },

  // ─────────────────────────────
  // UI state
  // ─────────────────────────────
  ui: {
    view: VIEW.JOURNEY,
    phase: PHASE.IDLE,
    bookingStep: BOOKING_STEP.FORM,

    run: {
      demoStarted: false,
      trackingTickOn: false,
      lookaheadOn: false,
    },

    loading: {
      planning: false,
      pricing: false,
      confirming: false,
      tracking: false,
      lookahead: false,
      gemini: false,
    },

    lockedReason: null,
    error: null,
  },

  // ─────────────────────────────
  // Data from backend / live feeds
  // ─────────────────────────────
  data: {
    bookingId: null,

    // ✅ NEW: single source of truth for the journey plan JSON
    // /public/demo/journey_plan_iit_sethsarai.json
    plan: null,

    case: null,

    chat: {
      mode: CHAT_MODE.LOCKED,
      messages: [],
    },

    live: {
      latest: null,
      history: [],
    },

    lookahead: {
      latest: null,
    },

    ai: {
      latest: null,
          // ✅ NEW: Gemini Video Emergency output (LiveEye)
    geminiVideo: {
      latest: null, // backend response from POST /video/emergency-demo
    },

    },

    subcenter: {
      activated: false,
    },
  },

  // ─────────────────────────────
  // UI-only controls (never backend-driven)
  // ─────────────────────────────
  controls: {
    activeSliceIndex: 0,
    sliceMeters: 0, // slider value in meters (pricing + zone logic)
    centerTab: "MAP",
    geminiTab: "DECISION",
    isChatOpen: false,
  },

  sim: {
    liveIdx: 0, // current point index on route
    paused: false, // pause/resume simulation
  },
};
