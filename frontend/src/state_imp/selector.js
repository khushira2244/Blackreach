// src/state/selectors.js

import { RISK, FPS_PROFILE, CHAT_MODE, PHASE } from "./constants";

// ─────────────────────────────
// Basic selectors
// ─────────────────────────────
export function selectCaseState(state) {
  return state?.data?.case?.state || null;
}

export function selectChatMode(state) {
  return state?.data?.chat?.mode || CHAT_MODE.LOCKED;
}

// ─────────────────────────────
// AI derived selectors
// ─────────────────────────────
export function selectRiskColor(state) {
  return state?.data?.ai?.latest?.riskColor || RISK.GREEN;
}

export function selectFpsProfile(state) {
  return state?.data?.ai?.latest?.fpsProfile || FPS_PROFILE.LOW;
}

// ─────────────────────────────
// Zone / phase helpers
// ─────────────────────────────
export function selectIsInZone(state) {
  // New rule: UI rendering trusts ui.phase only (Traveller controls transitions)
  return state?.ui?.phase === PHASE.IN_ZONE;
}

export function selectIsChatEnabled(state) {
  const mode = selectChatMode(state);
  return mode !== CHAT_MODE.LOCKED;
}

/**
 * NOTE:
 * derivePhase(state) was removed on purpose.
 * Phase is explicit and Traveller-driven; selectors must not reintroduce
 * data-derived phase changes.
 */
