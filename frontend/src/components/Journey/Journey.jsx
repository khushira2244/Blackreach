import "./journey.css";
import { useNavigate } from "react-router-dom";
import { useApp } from "../../state_imp/AppContext";
import { ACTOR } from "../../state_imp/constants";

function Journey() {
  const navigate = useNavigate();
  const { actions } = useApp();

  const goDemo = (actor) => {
    actions.setActor(actor);
    actions.watchDemo(); // state prep only (no loops)
    navigate("/screen");
  };

  return (
    <div className="journey-page home">
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

      <div className="cards-container">
        <div className="scenario-card">
          <div className="card-image">
            <img src="/Travellar/Adele.png" alt="Night office commute" />
          </div>

          <div className="card-content">
            <h2>The Last Ride Home</h2>
            <p>
              Adele is heading home after a late office shift. See how her journey
              is calmly secured.
            </p>

            <button className="demo-btn" onClick={() => goDemo(ACTOR.ADELE)}>
              Watch Demo
            </button>
          </div>
        </div>

        <div className="scenario-card">
          <div className="card-image">
            <img src="/Travellar/Harry.png" alt="Solo world traveller" />
          </div>

          <div className="card-content">
            <h2>Solo World Traveller</h2>
            <p>
              Experience how Harry’s journey is guided by Live Blackreach
            </p>

            <button className="demo-btn" onClick={() => goDemo(ACTOR.HARRY)}>
              Watch Demo
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Journey;
