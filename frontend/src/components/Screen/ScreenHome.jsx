import "./screenHome.css";
import { useApp } from "../../state_imp/AppContext";
import { PHASE } from "../../state_imp/constants";

import BookingPanel from "../Traveller/BookingPanel";
import TrackingPanel from "../Traveller/TrackingPanel";
import InZonePanel from "../Traveller/InZonePanel";
import EmergencyPanel from "../Traveller/EmergencyPanel";
import ClosedPanel from "../Traveller/ClosedPanel";

import GeminiPanel from "../Gemini/GeminiPanel";
import CenterPanel from "../center/CenterPanel";

function ScreenHome() {
  const { state } = useApp();
  const phase = state?.ui?.phase;

  const showOpsPanels =
    phase === PHASE.TRACKING ||
    phase === PHASE.IN_ZONE ||
    phase === PHASE.EMERGENCY ||
    phase === PHASE.CLOSED;

  return (
    <div className="screen-home">
      {/* Header */}
      <h1 className="home-title">
        Blackreach
        <span className="gemini-powered">
          <img
            src="/Travellar/Gemini_logo.png"
            alt="Gemini Logo"
            className="gemini-logo"
          />
          <span className="gemini-text">
            Powered by Gemini Progenesis Engine
          </span>
        </span>
      </h1>

      {/* Traveller */}
      <section className="screen-section traveller-section">
        {phase === PHASE.BOOKED && <BookingPanel />}
        {phase !== PHASE.BOOKED && <TrackingPanel />}
      </section>


      {/* Gemini + Center (Ops View) */}
      {showOpsPanels && (
        <>
          <section className="screen-section gemini-section">
            <GeminiPanel />
          </section>

          <section className="screen-section center-section">
            <CenterPanel />
          </section>
        </>
      )}
    </div>
  );
}

export default ScreenHome;