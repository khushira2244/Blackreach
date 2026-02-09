// src/components/Traveller/BookingPanel.jsx
import { useMemo, useState } from "react";
import "./bookingPanel.css";
import { useApp } from "../../state_imp/AppContext";
import { ACTOR, BOOKING_STEP } from "../../state_imp/constants";

/**
 * BookingPanel (Traveller)
 * RULE:
 * - Go does NOT start tracking/gemini/center loops.
 * - Go only loads plan JSON (instant demo) + moves bookingStep to SLIDER.
 * - Confirm starts tracking (PHASE.TRACKING).
 */

const DEMO_RECENTS = [
  {
    id: "trip-iit-mehrauli",
    title: "IIT Delhi → Mehrauli (Ber Sarai)",
    subtitle: "Scooty • Night commute",
    fromLabel: "JC Bose Marg, IIT Delhi",
    toLabel: "Seth Sarai, Mehrauli",
    origin: { lat: 28.54559, lng: 77.19274 },
    destination: { lat: 28.52485, lng: 77.18443 },
  },

];

const PLAN_URL = "/demo/journey_plan_iit_sethsarai.json";

// Security zone (Adele demo): Adchini -> (Block C / Qila Rai Pithora / Seth Sarai)
const SECURITY_START_IDX = 4; // Adchini
const SECURITY_END_MIN = 4;
const SECURITY_END_MAX = 7;
const RECOMMENDED_END_IDX = 7;

function fmtKm(m) {
  const km = Number(m || 0) / 1000;
  return `${km.toFixed(1)} km`;
}
function fmtMin(s) {
  const min = Math.round(Number(s || 0) / 60);
  return `${min} min`;
}

function computePrice({ distance_m, securityEndIdx, isSecurityMode }) {
  const base = 49 + Math.round(Number(distance_m || 0) / 250);
  if (!isSecurityMode) return { base, addon: 0, total: base };

  const segmentsCovered = Math.max(0, securityEndIdx - SECURITY_START_IDX + 1);
  const addon = 30 + segmentsCovered * 18;
  return { base, addon, total: base + addon };
}

export default function BookingPanel() {
  const { state, actions } = useApp();

  const actor = state?.app?.actor;
  const canUseSecurity = actor === ACTOR.ADELE;

  // ✅ global micro-step
  const bookingStep = state?.ui?.bookingStep || BOOKING_STEP.FORM;

  // FORM fields (demo)  ✅ (A→B kept as-is)
  const [fromLabel, setFromLabel] = useState("JC Bose Marg, IIT Delhi");
  const [toLabel, setToLabel] = useState("Seth Sarai, Mehrauli");
  const [originLat, setOriginLat] = useState(28.54559);
  const [originLng, setOriginLng] = useState(77.19274);
  const [destLat, setDestLat] = useState(28.52485);
  const [destLng, setDestLng] = useState(77.18443);

  const filled = useMemo(
    () => ({
      origin: { lat: Number(originLat), lng: Number(originLng) },
      destination: { lat: Number(destLat), lng: Number(destLng) },
      fromLabel,
      toLabel,
    }),
    [originLat, originLng, destLat, destLng, fromLabel, toLabel]
  );

  // Plan after Go (kept local for now)
  const [plan, setPlan] = useState(null);
  const [loadingPlan, setLoadingPlan] = useState(false);
  const [planError, setPlanError] = useState("");

  // ✅ slider value stored globally (controls)
  const securityEndIdx =
    typeof state?.controls?.activeSliceIndex === "number"
      ? state.controls.activeSliceIndex
      : RECOMMENDED_END_IDX;

  const onUseRecent = (t) => {
    setFromLabel(t.fromLabel);
    setToLabel(t.toLabel);
    setOriginLat(t.origin.lat);
    setOriginLng(t.origin.lng);
    setDestLat(t.destination.lat);
    setDestLng(t.destination.lng);
  };

  // ✅ Go is ONLY A→B: load plan, move to SLIDER (unchanged)
  const onGo = async () => {
    setPlanError("");
    setLoadingPlan(true);

    try {
      const res = await fetch(PLAN_URL, { cache: "no-store" });
      if (!res.ok) throw new Error(`Plan file not found (${res.status})`);
      const data = await res.json();

      if (!data?.areas || !data?.distance_m || !data?.duration_s) {
        throw new Error("Invalid plan JSON shape");
      }

      setPlan(data);

      actions.setActiveSliceIndex(RECOMMENDED_END_IDX);
      actions.setBookingStep(BOOKING_STEP.SLIDER);
    } catch (err) {
      setPlanError(err?.message || "Failed to load route plan");
    } finally {
      setLoadingPlan(false);
    }
  };



  const price = useMemo(() => {
    if (!plan) return { base: 0, addon: 0, total: 0 };
    return computePrice({
      distance_m: plan.distance_m,
      securityEndIdx,
      isSecurityMode: canUseSecurity,
    });
  }, [plan, securityEndIdx, canUseSecurity]);

  const BLOCK_C = { lat: 28.54433, lng: 77.19539 };

 const onConfirmStart = async () => {
  try {
    if (!plan) return;

    const isAdele = actor === ACTOR.ADELE;
    const endIdx =
      typeof state?.controls?.activeSliceIndex === "number"
        ? state.controls.activeSliceIndex
        : RECOMMENDED_END_IDX;

    const areasArr = Array.isArray(plan.areas) ? plan.areas : [];

    const polylineFinal =
      typeof plan.polyline === "string" && plan.polyline.length > 10
        ? plan.polyline
        : "}hfmDsucvMHMROs@yDBOvCeAMe@BQLIJAp@a@N_@b@}A\\}@tAoFF[z@aDbA_Dx@kDk@Yl@wBDYsGoCqCaAH[zCjApQhHdDx@`E`A~Ar@jB`AzBr@tFzBd@TvAh@`@LdBp@xCx@zBj@ZNbCfB`@\\l@`@jD|ClAnAd@t@fEvHtGxLj@t@nDhDjA~ABJlBzA\\\\h@VrBnAb@f@e@RwCPMzKFbAJd@VVZJ|DQz@?";

    const payload = {
      origin: filled.origin,
      destination: filled.destination,
      polyline: polylineFinal,
      distance_m: plan.distance_m,
      duration_s: plan.duration_s,
      areas: areasArr.map((name, index) => ({ index, name })),

      coverage: isAdele ? "SLICE" : "NONE",
      companionMode: isAdele ? "NORMAL_SLICE" : "COMPANION",
      securityTier: isAdele ? "MONITORING" : "NONE",

      ...(isAdele
        ? {
            start_index: SECURITY_START_IDX,
            end_index: endIdx,
            covered_km: 1.0,
            estimatedPriceINR: price.total,
          }
        : {
            start_index: 0,
            end_index: Math.max(0, areasArr.length - 1),
            covered_km: 0,
            estimatedPriceINR: price.base,
          }),

      notes: "IIT -> Seth Sarai, security slice demo",
    };

    // 1) booking confirm ONLY
    const res = await actions.bookingConfirm(payload);
    const bookingId = res?.bookingId;
    if (!bookingId) return;

    // state stays the same
    actions.setBookingStep(BOOKING_STEP.CONFIRM_READY);
    actions.startTracking();

    return res;
  } catch (e) {
    console.error(e);
  }
};






  // ─────────────────────────────────────────────
  // SLIDER step (AFTER Go)
  // ─────────────────────────────────────────────
  if (bookingStep === BOOKING_STEP.SLIDER && plan) {
    const nodeLabels = plan.areas

    return (
      <div className="bp-shell">
        {/* LEFT */}
        <div className="bp-left">
          <div className="bp-card">
            <div className="bp-title">Security Coverage</div>

            <div className="bp-field">
              <div className="bp-label">
                <img src="/demo/icons/map-pin.svg" alt="" className="bp-icon" />
                Route summary
              </div>

              <div className="bp-summaryRow">
                <span className="bp-kpi">
                  <span className="bp-kpiLabel">Distance</span>
                  <span className="bp-kpiValue">{fmtKm(plan.distance_m)}</span>
                </span>

                <span className="bp-kpi">
                  <span className="bp-kpiLabel">Duration</span>
                  <span className="bp-kpiValue">{fmtMin(plan.duration_s)}</span>
                </span>
              </div>
            </div>

            {/* Slider (AFTER Go) */}
            <div className="bp-field" style={{ marginTop: 14 }}>
              <div className="bp-label">
                <img
                  src="/demo/icons/arrow-right.svg"
                  alt=""
                  className="bp-icon"
                />
                Select security zone (~1.2 km demo)
              </div>

              <div className="bp-sliderBlock">
                {/* keep the actual range input (you’ll style vertical in CSS) */}
                <input
                  className="bp-slider"
                  type="range"
                  min={0}
                  max={plan.areas.length - 1}
                  step={1}
                  value={securityEndIdx}
                  onChange={(e) => actions.setActiveSliceIndex(Number(e.target.value))}
                  style={{ pointerEvents: "none" }}
                  aria-label="security-zone-slider"
                />



                {/* visual nodes + labels (CSS decides vertical layout) */}
                <div className="bp-routeNodes" aria-hidden="true">
                  {nodeLabels.map((label, idx) => {
                    const isSelectedEnd = idx === securityEndIdx;

                    // coverage is Adchini -> selected (only if selected is >= Adchini)
                    const inSelectedCoverage =
                      idx >= SECURITY_START_IDX && idx <= securityEndIdx;

                    const isSecurityStart = idx === SECURITY_START_IDX;

                    return (
                      <div
                        key={`${label}-${idx}`}
                        className={[
                          "bp-routeNode",
                          isSecurityStart ? "security" : "",
                          isSelectedEnd ? "active" : "",
                          inSelectedCoverage ? "covered" : "",
                        ].join(" ")}
                      >
                        <div className="bp-routeDot" />
                        <div className="bp-routeLabel">{label}</div>
                      </div>
                    );
                  })}
                </div>


              </div>
            </div>

            <div className="bp-actionsRow">
              <button className="bp-go" onClick={onConfirmStart}>
                Confirm & Start Journey
              </button>


            </div>
          </div>
        </div>

        {/* RIGHT */}
        <div className="bp-right">
          <div className="bp-right-head">
            <img src="/demo/icons/history.svg" alt="" className="bp-icon" />
            Security Coverage Pricing
          </div>

          <div className="bp-card bp-priceCard">
            {/* Reference: whole journey */}
            <div className="bp-priceLines">
              <div className="bp-priceLine">
                <span>Whole journey security coverage</span>
                <b>
                  {fmtKm(plan.distance_m)} · ₹{price.base + price.addon}
                </b>
              </div>

              <div style={{ fontSize: 12, opacity: 0.7, marginTop: 4 }}>
                Whole Journey Cost
              </div>
            </div>

            {/* Selected decision */}
            <div className="bp-priceLines" style={{ marginTop: 14 }}>
              <div className="bp-priceLine">
                <span>Selected security area</span>
                <b>
                  {/* plug selected km here */}
                  1 km · ₹{price.addon}
                </b>
              </div>
            </div>


            {/* Reassurance */}
            <div className="bp-priceHint" style={{ marginTop: 12 }}>
              You saved cost by limiting security coverage.
            </div>
          </div>
          <div className="bp-card" style={{ marginTop: 14 }}>
            <div style={{ fontWeight: 700, marginBottom: 8, color: '#ff4d4d' }}>
              Vulnerability Assessment: High Risk
            </div>

            <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 12 }}>
              Why security is recommended here
            </div>

            <div style={{ fontSize: 13, lineHeight: 1.6, opacity: 0.85 }}>
              This 1.2 km segment traverses the <strong>Mehrauli–Sanjay Van</strong> forest periphery.
              Our data indicates critical risk factors: unlit forest-adjacent corridors,
              low transit density, and a documented history of evening safety incidents.
              Blackreach monitoring is highly advised for this zone.
            </div>
          </div>

        </div>


      </div>
    );
  }

  // ─────────────────────────────────────────────
  // FORM step (BEFORE Go) ✅ untouched A→B
  // ─────────────────────────────────────────────
  return (
    <div className="bp-shell">
      {/* LEFT */}
      <div className="bp-left">
        <div className="bp-card">
          <div className="bp-title">Plan your ride</div>

          <div className="bp-field">
            <div className="bp-label">
              <img src="/demo/icons/map-pin.svg" alt="" className="bp-icon" />
              From
            </div>

            <input
              className="bp-input"
              value={fromLabel}
              onChange={(e) => setFromLabel(e.target.value)}
              placeholder="Pickup"
            />

            <div className="bp-coords">
              <input
                className="bp-coord"
                type="number"
                step="0.00001"
                value={originLat}
                onChange={(e) => setOriginLat(e.target.value)}
                aria-label="origin-lat"
              />
              <input
                className="bp-coord"
                type="number"
                step="0.00001"
                value={originLng}
                onChange={(e) => setOriginLng(e.target.value)}
                aria-label="origin-lng"
              />
            </div>
          </div>

          <div className="bp-field">
            <div className="bp-label">
              <img src="/demo/icons/arrow-right.svg" alt="" className="bp-icon" />
              To
            </div>

            <input
              className="bp-input"
              value={toLabel}
              onChange={(e) => setToLabel(e.target.value)}
              placeholder="Dropoff"
            />

            <div className="bp-coords">
              <input
                className="bp-coord"
                type="number"
                step="0.00001"
                value={destLat}
                onChange={(e) => setDestLat(e.target.value)}
                aria-label="dest-lat"
              />
              <input
                className="bp-coord"
                type="number"
                step="0.00001"
                value={destLng}
                onChange={(e) => setDestLng(e.target.value)}
                aria-label="dest-lng"
              />
            </div>
          </div>

          <div className="bp-hint">
            After <b>Go</b>, Adele selects a security zone (slider) and sees
            price.
          </div>

          <button className="bp-go" onClick={onGo} disabled={loadingPlan}>
            {loadingPlan ? "Loading plan..." : "Go"}
          </button>

          {planError && (
            <div className="bp-hint" style={{ marginTop: 10, opacity: 0.95 }}>
              ❌ {planError}
              <div style={{ opacity: 0.8, marginTop: 6 }}>
                Check file path: <b>{PLAN_URL}</b>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* RIGHT */}
      <div className="bp-right">
        <div className="bp-right-head">
          <img src="/demo/icons/history.svg" alt="" className="bp-icon" />
          Recent trips
        </div>

        <div className="bp-recents">
          {DEMO_RECENTS.map((t) => (
            <button
              key={t.id}
              type="button"
              className="bp-recent"
              onClick={() => onUseRecent(t)}
            >
              <div className="bp-recent-title">{t.title}</div>
              <div className="bp-recent-sub">{t.subtitle}</div>

              <div className="bp-recent-badge">
                <img
                  src="/demo/icons/scooty.svg"
                  alt=""
                  className="bp-badge-ic"
                />
                Completed
              </div>
            </button>
          ))}
        </div>

        <div className="bp-note">Safe history of Adele</div>
      </div>
    </div>
  );
}
