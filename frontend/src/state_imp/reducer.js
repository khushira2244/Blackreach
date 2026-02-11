// src/state/reducer.js

import {
  ACTOR,
  APP_MODE,
  DEMO_MODE,
  PHASE,
  CHAT_MODE,
  VIEW,
  BOOKING_STEP,
} from "./constants";

// Action type constants (kept inside reducer file for now)
export const ACTIONS = {
  // App actions
  SET_ACTOR: "SET_ACTOR",
  SET_APP_MODE: "SET_APP_MODE",
  SET_DEMO_MODE: "SET_DEMO_MODE",

  // ✅ NEW: global journey plan
  SET_PLAN: "SET_PLAN",

  // Sim actions
  SET_LIVE_INDEX: "SET_LIVE_INDEX",
  SET_TRACKING_PAUSED: "SET_TRACKING_PAUSED",

  // UI routing + explicit state transitions
  SET_VIEW: "SET_VIEW",
  SET_PHASE: "SET_PHASE",
  SET_BOOKING_STEP: "SET_BOOKING_STEP",
  SET_RUN_FLAG: "SET_RUN_FLAG",

  // Data hydration actions (data-only; must NOT change ui.phase)
  BOOKING_CONFIRMED: "BOOKING_CONFIRMED",
  CASE_UPDATED: "CASE_UPDATED",
  CHAT_UPDATED: "CHAT_UPDATED",
  LIVE_UPDATED: "LIVE_UPDATED",
  LOOKAHEAD_UPDATED: "LOOKAHEAD_UPDATED",
  AI_UPDATED: "AI_UPDATED",
  GEMINI_VIDEO_UPDATED: "GEMINI_VIDEO_UPDATED",


  // Control actions
  SET_ACTIVE_SLICE_INDEX: "SET_ACTIVE_SLICE_INDEX",
  SET_SLICE_METERS: "SET_SLICE_METERS",
  SET_CENTER_TAB: "SET_CENTER_TAB",
  SET_GEMINI_TAB: "SET_GEMINI_TAB",
  SET_CHAT_OPEN: "SET_CHAT_OPEN",

  // Loading/error actions
  SET_LOADING_FLAG: "SET_LOADING_FLAG",
  SET_ERROR: "SET_ERROR",
  CLEAR_ERROR: "CLEAR_ERROR",
};

export function reducer(state, action) {
  switch (action.type) {
    // ─────────────────────────────
    // App actions
    // ─────────────────────────────
    case ACTIONS.SET_ACTOR: {
      const actor = action.payload;
      if (!actor || !Object.values(ACTOR).includes(actor)) return state;

      return {
        ...state,
        app: { ...state.app, actor },
      };
    }

    case ACTIONS.SET_APP_MODE: {
      const appMode = action.payload;
      if (!appMode || !Object.values(APP_MODE).includes(appMode)) return state;

      return {
        ...state,
        app: { ...state.app, appMode },
      };
    }

    case ACTIONS.SET_DEMO_MODE: {
      const demoMode = action.payload;
      if (!demoMode || !Object.values(DEMO_MODE).includes(demoMode)) return state;

      return {
        ...state,
        app: { ...state.app, demoMode },
      };
    }

    // ─────────────────────────────
    // ✅ Plan (single source of truth)
    // ─────────────────────────────
    case ACTIONS.SET_PLAN: {
      const plan = action.payload ?? null;
      return {
        ...state,
        data: {
          ...state.data,
          plan,
        },
      };
    }

    // ─────────────────────────────
    // UI actions (explicit, Traveller-driven)
    // ─────────────────────────────
    case ACTIONS.SET_VIEW: {
      const view = action.payload;
      if (!view || !Object.values(VIEW).includes(view)) return state;

      return {
        ...state,
        ui: { ...state.ui, view },
      };
    }

    // ✅ UPDATED: locks chat unless IN_ZONE
    case ACTIONS.SET_PHASE: {
      const phase = action.payload;
      if (!phase || !Object.values(PHASE).includes(phase)) return state;

      const mustLockChat = phase !== PHASE.IN_ZONE;

      return {
        ...state,
        ui: { ...state.ui, phase },
        data: {
          ...state.data,
          chat: mustLockChat
            ? { ...state.data.chat, mode: CHAT_MODE.LOCKED }
            : state.data.chat,
        },
      };
    }

    case ACTIONS.SET_BOOKING_STEP: {
      const bookingStep = action.payload;
      if (!bookingStep || !Object.values(BOOKING_STEP).includes(bookingStep))
        return state;

      return {
        ...state,
        ui: { ...state.ui, bookingStep },
      };
    }

    case ACTIONS.SET_RUN_FLAG: {
      const { key, value } = action.payload || {};
      if (!key || typeof value !== "boolean") return state;
      if (!state.ui?.run || !(key in state.ui.run)) return state;

      return {
        ...state,
        ui: {
          ...state.ui,
          run: { ...state.ui.run, [key]: value },
        },
      };
    }

    // ─────────────────────────────
    // Data hydration actions (data-only; NEVER changes ui.phase)
    // ─────────────────────────────
    case ACTIONS.BOOKING_CONFIRMED: {
      const { bookingId, case: caseObj, chat } = action.payload || {};

      // ✅ UPDATED: always lock chat on confirm
      const nextChat = {
        mode: CHAT_MODE.LOCKED,
        messages: Array.isArray(chat?.messages) ? chat.messages : [],
      };

      // NOTE: No phase derivation here. Traveller decides phase explicitly.
      return {
        ...state,
        data: {
          ...state.data,
          bookingId: bookingId ?? state.data.bookingId,
          case: caseObj ?? state.data.case,
          chat: nextChat,
        },
        ui: {
          ...state.ui,
          // Keep existing phase; only adjust lock display if chat unlocked
          lockedReason:
            nextChat.mode === CHAT_MODE.LOCKED ? state.ui.lockedReason : null,
        },
      };
    }

    case ACTIONS.CASE_UPDATED: {
      const caseObj = action.payload ?? null;
      return {
        ...state,
        data: { ...state.data, case: caseObj },
      };
    }

    case ACTIONS.CHAT_UPDATED: {
      const patch = action.payload || {};

      const nextChat = {
        ...state.data.chat,
        ...patch,
        messages: Array.isArray(patch.messages)
          ? patch.messages
          : state.data.chat.messages,
      };

      return {
        ...state,
        data: { ...state.data, chat: nextChat },
      };
    }

    case ACTIONS.LIVE_UPDATED: {
      const latest = action.payload ?? null;

      const prevHistory = state.data.live.history || [];
      const nextHistory = latest
        ? [latest, ...prevHistory].slice(0, 200)
        : prevHistory;

      // NOTE: No phase changes here. Live streaming is data-only.
      return {
        ...state,
        data: {
          ...state.data,
          live: { latest, history: nextHistory },
        },
      };
    }

    case ACTIONS.LOOKAHEAD_UPDATED: {
      const latest = action.payload ?? null;
      return {
        ...state,
        data: { ...state.data, lookahead: { latest } },
      };
    }

    // ✅ UPDATED: support { latest, lastInput } OR old style latest-only
    case ACTIONS.AI_UPDATED: {
      const p = action.payload;

      const isObj = p && typeof p === "object" && !Array.isArray(p);
      const hasNewShape =
        isObj && ("latest" in p || "lastInput" in p || "lastCheckpoint" in p);

      if (hasNewShape) {
        return {
          ...state,
          data: {
            ...state.data,
            ai: {
              ...state.data.ai, // keep any existing fields
              latest:
                p.latest !== undefined ? p.latest : state.data.ai?.latest ?? null,
              lastInput:
                p.lastInput !== undefined
                  ? p.lastInput
                  : state.data.ai?.lastInput ?? null,
              // optional, harmless if you later add it to initialState
              lastCheckpoint:
                p.lastCheckpoint !== undefined
                  ? p.lastCheckpoint
                  : state.data.ai?.lastCheckpoint ?? null,
            },
          },
        };
      }

      // Backward compat: payload itself is latest output
      const latest = p ?? null;
      return {
        ...state,
        data: {
          ...state.data,
          ai: {
            ...state.data.ai, // keep lastInput
            latest,
          },
        },
      };
    }

        // ✅ NEW: store LiveEye / Gemini video emergency result
    case ACTIONS.GEMINI_VIDEO_UPDATED: {
      const latest = action.payload ?? null;
      return {
        ...state,
        data: {
          ...state.data,
          geminiVideo: {
            ...state.data.geminiVideo,
            latest,
          },
        },
      };
    }

    // ─────────────────────────────
    // Control actions
    // ─────────────────────────────
    case ACTIONS.SET_ACTIVE_SLICE_INDEX: {
      const idx = action.payload;
      if (typeof idx !== "number" || idx < 0) return state;

      return {
        ...state,
        controls: { ...state.controls, activeSliceIndex: idx },
      };
    }

    case ACTIONS.SET_SLICE_METERS: {
      const meters = action.payload;
      if (typeof meters !== "number" || meters < 0) return state;

      return {
        ...state,
        controls: { ...state.controls, sliceMeters: meters },
      };
    }

    case ACTIONS.SET_CENTER_TAB: {
      const tab = action.payload;
      if (!tab) return state;

      return {
        ...state,
        controls: { ...state.controls, centerTab: tab },
      };
    }

    case ACTIONS.SET_GEMINI_TAB: {
      const tab = action.payload;
      if (!tab) return state;

      return {
        ...state,
        controls: { ...state.controls, geminiTab: tab },
      };
    }

    case ACTIONS.SET_CHAT_OPEN: {
      const isChatOpen = Boolean(action.payload);
      return {
        ...state,
        controls: { ...state.controls, isChatOpen },
      };
    }

    // ─────────────────────────────
    // Sim actions (UI-only)
    // ─────────────────────────────
    case ACTIONS.SET_LIVE_INDEX: {
      let idx = action.payload;

      if (typeof idx !== "number" || idx < 0) return state;

      const points =
        state.data.plan?.sample_points || state.data.plan?.points || [];

      const maxIdx = points.length > 0 ? points.length - 1 : 0;

      const clampedIdx = Math.min(Math.max(idx, 0), maxIdx);

      return {
        ...state,
        sim: {
          ...state.sim,
          liveIdx: clampedIdx,
        },
      };
    }

    case ACTIONS.SET_TRACKING_PAUSED: {
      const paused = Boolean(action.payload);
      return {
        ...state,
        sim: {
          ...state.sim,
          paused,
        },
      };
    }

    // ─────────────────────────────
    // Loading/error actions
    // ─────────────────────────────
    case ACTIONS.SET_LOADING_FLAG: {
      const { key, value } = action.payload || {};
      if (!key || typeof value !== "boolean") return state;
      if (!(key in state.ui.loading)) return state;

      return {
        ...state,
        ui: {
          ...state.ui,
          loading: { ...state.ui.loading, [key]: value },
        },
      };
    }

    case ACTIONS.SET_ERROR: {
      const error = action.payload || "Unknown error";
      return {
        ...state,
        ui: { ...state.ui, error: String(error) },
      };
    }

    case ACTIONS.CLEAR_ERROR: {
      return {
        ...state,
        ui: { ...state.ui, error: null },
      };
    }

    default:
      return state;
  }
}
