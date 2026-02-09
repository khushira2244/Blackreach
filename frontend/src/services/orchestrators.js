// src/services/orchestrators.js

import { blackreachApi } from "./blackreachApi";
import { CHAT_MODE, PHASE } from "../state_imp/constants";
import { ACTIONS } from "../state_imp/reducer";

function safeErrMessage(err) {
  return (err && err.message) || "Unknown error";
}

function setLoading(dispatch, key, value) {
  dispatch({ type: ACTIONS.SET_LOADING_FLAG, payload: { key, value } });
}

function setError(dispatch, msg) {
  dispatch({ type: ACTIONS.SET_ERROR, payload: msg });
}

function clearError(dispatch) {
  dispatch({ type: ACTIONS.CLEAR_ERROR });
}

// Normalize gemini response into a consistent ai.latest shape
function normalizeAiLatest({ bookingId, payload, res }) {
  const checkpoint = payload?.checkpoint || payload?.checkpointName || "UNKNOWN";
  const src = res?.aiLatest || res || {};

  return {
    at: src.at || new Date().toISOString(),
    bookingId: bookingId || src.bookingId || null,
    checkpoint,

    riskColor: src.riskColor || src.risk || null,
    fpsProfile: src.fpsProfile || null,
    subcenterAdvice: src.subcenterAdvice || null,
    reasons: src.reasons || src.reason || src.explanation || null,
    brief: src.brief || null,

    // ✅ NEW: backend evidence/context fed to Gemini
    geminiInput: src.geminiInput || null,

    // (optional) keep request snapshot too; harmless + useful
    input: payload || null,

    raw: src,
  };
}


/**
 * Orchestrator (new architecture):
 * - Single-shot API helper only.
 * - NO loops, NO timers, NO demo logic.
 * - NO phase derivation.
 * - Data updates must NOT change ui.phase; Traveller owns transitions.
 */
export function createOrchestrator({ getState, dispatch }) {
  const aborters = {
    confirm: null,
    caseGet: null,
    chatGet: null,
    trackingUpdate: null,
    trackingLatest: null,
    lookahead: null,
    gemini: null,
    resolve: null,
  };

  function abortInFlight(key) {
    try {
      aborters[key]?.abort();
    } catch {}
    aborters[key] = null;
  }

  // Optional: call on route/page exit to cancel any in-flight requests
  function abortAll() {
    Object.keys(aborters).forEach((k) => abortInFlight(k));
  }

  // ─────────────────────────────
  // bookingConfirm(payload) → BOOKING_CONFIRMED (data only)
  // ─────────────────────────────
  async function bookingConfirm(payload) {
    clearError(dispatch);
    setLoading(dispatch, "confirming", true);

    abortInFlight("confirm");
    aborters.confirm = new AbortController();

    try {
      const res = await blackreachApi.booking.confirm(payload, {
        signal: aborters.confirm.signal,
      });

      const bookingId = res?.bookingId || res?.id || null;

      dispatch({
        type: ACTIONS.BOOKING_CONFIRMED,
        payload: {
          bookingId,
          case: res?.case || null,
          chat: res?.chat || {
            mode: res?.chatMode || CHAT_MODE.LOCKED,
            messages: Array.isArray(res?.chat?.messages) ? res.chat.messages : [],
          },
        },
      });

      return res;
    } catch (err) {
      setError(dispatch, safeErrMessage(err));
      throw err;
    } finally {
      setLoading(dispatch, "confirming", false);
      abortInFlight("confirm");
    }
  }

  // ─────────────────────────────
  // hydrateCase(bookingId) → CASE_UPDATED (data only)
  // ─────────────────────────────
  async function hydrateCase(bookingId) {
    clearError(dispatch);

    // Using "planning" because it exists in initialState.ui.loading
    setLoading(dispatch, "planning", true);

    abortInFlight("caseGet");
    aborters.caseGet = new AbortController();

    try {
      const id = bookingId || getState()?.data?.bookingId;
      if (!id) throw new Error("Missing bookingId for hydrateCase");

      const c = await blackreachApi.case.get(id, {
        signal: aborters.caseGet.signal,
      });

      dispatch({ type: ACTIONS.CASE_UPDATED, payload: c });
      return c;
    } catch (err) {
      setError(dispatch, safeErrMessage(err));
      throw err;
    } finally {
      setLoading(dispatch, "planning", false);
      abortInFlight("caseGet");
    }
  }

  // ─────────────────────────────
  // hydrateChat(bookingId) → CHAT_UPDATED (data only)
  // ─────────────────────────────
  async function hydrateChat(bookingId) {
    clearError(dispatch);
    setLoading(dispatch, "planning", true);

    abortInFlight("chatGet");
    aborters.chatGet = new AbortController();

    try {
      const id = bookingId || getState()?.data?.bookingId;
      if (!id) throw new Error("Missing bookingId for hydrateChat");

      const chat = await blackreachApi.chat.get(id, {
        signal: aborters.chatGet.signal,
      });

      dispatch({ type: ACTIONS.CHAT_UPDATED, payload: chat });
      return chat;
    } catch (err) {
      setError(dispatch, safeErrMessage(err));
      throw err;
    } finally {
      setLoading(dispatch, "planning", false);
      abortInFlight("chatGet");
    }
  }

  // ─────────────────────────────
  // trackingUpdateOnce(bookingId, payload) → LIVE_UPDATED
  // ─────────────────────────────
  async function trackingUpdateOnce(bookingId, payload = {}) {
    clearError(dispatch);
    setLoading(dispatch, "tracking", true);

    abortInFlight("trackingUpdate");
    aborters.trackingUpdate = new AbortController();

    try {
      const id = bookingId || getState()?.data?.bookingId;
      if (!id) throw new Error("Missing bookingId for trackingUpdateOnce");

      // ✅ match backend swagger
      const upd = await blackreachApi.tracking.update(
        { bookingId: id, ...payload },
        { signal: aborters.trackingUpdate.signal }
      );

      const latest = upd?.latest || upd?.live || upd || null;
      if (latest) dispatch({ type: ACTIONS.LIVE_UPDATED, payload: latest });

      return upd;
    } catch (err) {
      setError(dispatch, safeErrMessage(err));
      throw err;
    } finally {
      setLoading(dispatch, "tracking", false);
      abortInFlight("trackingUpdate");
    }
  }

  // Optional helper: read latest without update
  async function trackingLatestOnce(bookingId) {
    clearError(dispatch);
    setLoading(dispatch, "tracking", true);

    abortInFlight("trackingLatest");
    aborters.trackingLatest = new AbortController();

    try {
      const id = bookingId || getState()?.data?.bookingId;
      if (!id) throw new Error("Missing bookingId for trackingLatestOnce");

      const latest = await blackreachApi.tracking.latest(id, {
        signal: aborters.trackingLatest.signal,
      });

      if (latest) {
        dispatch({ type: ACTIONS.LIVE_UPDATED, payload: latest });
      }

      return latest;
    } catch (err) {
      setError(dispatch, safeErrMessage(err));
      throw err;
    } finally {
      setLoading(dispatch, "tracking", false);
      abortInFlight("trackingLatest");
    }
  }

  // ─────────────────────────────
  // lookaheadOnce(bookingId, payload) → LOOKAHEAD_UPDATED
  // ─────────────────────────────
async function lookaheadOnce(bookingId, payload = {}) {
  clearError(dispatch);
  setLoading(dispatch, "lookahead", true);

  abortInFlight("lookahead");
  aborters.lookahead = new AbortController();

  try {
    const id = bookingId || getState()?.data?.bookingId;
    if (!id) throw new Error("Missing bookingId for lookaheadOnce");

    const res = await blackreachApi.lookahead.m500(
      { bookingId: id, ...payload }, // ✅ bookingId goes inside body
      { signal: aborters.lookahead.signal }
    );

    dispatch({ type: ACTIONS.LOOKAHEAD_UPDATED, payload: res });
    return res;
  } catch (err) {
    setError(dispatch, safeErrMessage(err));
    throw err;
  } finally {
    setLoading(dispatch, "lookahead", false);
    abortInFlight("lookahead");
  }
}



  // ─────────────────────────────
  // geminiOnce(bookingId, payload) → AI_UPDATED (+ optional CHAT_UPDATED)
  // ─────────────────────────────
 async function geminiOnce(
  bookingId,
  payload,
  { hydrateChatOnUnlock = true } = {}
) {
  clearError(dispatch);
  setLoading(dispatch, "gemini", true);

  abortInFlight("gemini");
  aborters.gemini = new AbortController();

  try {
    const id = bookingId || getState()?.data?.bookingId;
    if (!id) throw new Error("Missing bookingId for geminiOnce");

    // ✅ sanitize payload to match Swagger (no nulls)
    const clean = { ...(payload || {}) };

    // checkpoint must exist
    if (!clean.checkpoint) clean.checkpoint = "INITIAL";

    // userSignal must be string if present (null breaks 422)
    if (clean.userSignal == null) delete clean.userSignal;

    // note optional (remove null)
    if (clean.note == null) delete clean.note;

    // max_recent_messages default
    if (clean.max_recent_messages == null) clean.max_recent_messages = 10;

    const res = await blackreachApi.gemini.run(id, clean, {
      signal: aborters.gemini.signal,
    });

    const aiLatest = normalizeAiLatest({ bookingId: id, payload: clean, res });

    dispatch({
      type: ACTIONS.AI_UPDATED,
      payload: {
        latest: aiLatest,
        lastInput: clean,
        lastCheckpoint: clean.checkpoint || aiLatest.checkpoint,
      },
    });

    // ... keep your hydrateChatOnUnlock logic exactly as-is ...

    return res;
  } catch (err) {
    setError(dispatch, safeErrMessage(err));
    throw err;
  } finally {
    setLoading(dispatch, "gemini", false);
    abortInFlight("gemini");
  }
}


  // ─────────────────────────────
  // resolveCase(bookingId) → CASE_UPDATED (data only)
  // ─────────────────────────────
  async function resolveCase(bookingId) {
    clearError(dispatch);

    abortInFlight("resolve");
    aborters.resolve = new AbortController();

    try {
      const id = bookingId || getState()?.data?.bookingId;
      if (!id) throw new Error("Missing bookingId to resolveCase");

      const res = await blackreachApi.case.resolve(id, {
        signal: aborters.resolve.signal,
      });

      // Refresh case snapshot for UI (data-only)
      await hydrateCase(id);

      return res;
    } catch (err) {
      setError(dispatch, safeErrMessage(err));
      throw err;
    } finally {
      abortInFlight("resolve");
    }
  }

  return {
    abortAll,

    bookingConfirm,
    hydrateCase,
    hydrateChat,

    trackingUpdateOnce,
    trackingLatestOnce,
    lookaheadOnce,
    geminiOnce,

    resolveCase,
  };
}
