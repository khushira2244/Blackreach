// src/state_imp/sim/useTrackingSim.js
import { useEffect, useRef } from "react";
import { PHASE } from "../constants";

/**
 * Tracking simulator (stable):
 * - Moves along plan.sample_points
 * - Writes global live index
 * - Stops before security zone start (idx = securityStartIdx - 1) ONLY during TRACKING
 *
 * Requires actions in AppContext:
 * - actions.setLiveIndex(n)
 * - actions.setTrackingPaused(true/false)
 */
export function useTrackingSim({
  state,
  actions,
  plan,
  securityStartIdx = 4, // Adchini
  tickMs = 1400,
}) {
  const timerRef = useRef(null);

  // ✅ refs to avoid stale closure + interval churn
  const liveIdxRef = useRef(0);

  const phase = state?.ui?.phase;
  const paused = !!state?.sim?.paused;
  const liveIdx = state?.sim?.liveIdx ?? 0;

  // keep ref in sync with latest state value
  useEffect(() => {
    liveIdxRef.current = liveIdx;
  }, [liveIdx]);

  const pointsLen = plan?.sample_points?.length || 0;
  const stopIdx = Math.max(0, securityStartIdx - 1);

  useEffect(() => {
    // ✅ Run simulator in TRACKING OR IN_ZONE
    const shouldRun =
      (phase === PHASE.TRACKING || phase === PHASE.IN_ZONE) &&
      plan &&
      pointsLen >= 2 &&
      !paused;

    if (!shouldRun) {
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = null;
      return;
    }

    // ensure only 1 interval exists
    if (timerRef.current) clearInterval(timerRef.current);

    timerRef.current = setInterval(() => {
      const curr = liveIdxRef.current;

      // ✅ Stop at gate ONLY during TRACKING
      if (phase === PHASE.TRACKING && curr >= stopIdx) {
        actions.setTrackingPaused(true);
        return;
      }

      const next = Math.min(curr + 1, pointsLen - 1);
      actions.setLiveIndex(next);

      // update ref immediately to avoid waiting for React render
      liveIdxRef.current = next;
    }, tickMs);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = null;
    };
  }, [phase, paused, plan, pointsLen, stopIdx, tickMs, actions]);

  // helpers for UI buttons
  const resume = () => actions.setTrackingPaused(false);
  const pause = () => actions.setTrackingPaused(true);
  const reset = () => {
    actions.setTrackingPaused(false);
    actions.setLiveIndex(0);
    liveIdxRef.current = 0;
  };

  return {
    liveIdx,
    paused,
    stopIdx,
    canEnterSecurity: liveIdx >= stopIdx,
    resume,
    pause,
    reset,
  };
}
