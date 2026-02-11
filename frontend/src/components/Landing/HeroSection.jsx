import "./heroSection.css";

import realAppImage from "../../assets/logo/Real_app_image.png";
import SafetyFlowSection from "./SafetyFlowSection";
import AudienceSection from "./AudienceSection";
import TechStackSection from "./TechStackSection";

import { useNavigate } from "react-router-dom";




export default function HeroSection() {
    const navigate = useNavigate();
  return (
    <>
    <section className="hero">
      <div className="hero-inner">
        
        {/* LEFT CONTENT */}
        <div className="hero-left">
          <h1 className="hero-title">
            Blackreach
          </h1>

          <div className="hero-powered">
            <img
              src="/Travellar/Gemini_logo.png"
              alt="Gemini Logo"
              className="hero-gemini-logo"
            />
            <span>Powered by Gemini Progenesis Engine</span>
          </div>

          <p className="hero-description">
            Context-aware journey safety with real-time reasoning 
            and human-backed escalation.
          </p>

           <button
              className="hero-button"
              onClick={() => navigate("/journey")}
            >
              Watch Demo
            </button>
        </div>

        {/* RIGHT IMAGE */}
        <div className="hero-right">
          <img
            src={realAppImage}
            alt="Blackreach Application Preview"
            className="hero-image"
          />
        </div>

      </div>
    </section>
    <SafetyFlowSection/>
    <AudienceSection/>
    <TechStackSection/>
    </>
  );
}
