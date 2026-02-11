import { Routes, Route, Navigate } from "react-router-dom";

import Journey from "./components/Journey/Journey";
import ScreenHome from "./components/Screen/ScreenHome";
import HeroSection from "./components/Landing/HeroSection";
import { useApp } from "./state_imp/AppContext";

function App() {
  const { state, actions } = useApp();

  return (
    <Routes>
      {/* Landing Page */}
      <Route path="/" element={<HeroSection />} />

      {/* Journey Page */}
      <Route
        path="/journey"
        element={<Journey state={state} actions={actions} />}
      />

      {/* Optional screen page */}
      <Route
        path="/screen"
        element={<ScreenHome state={state} actions={actions} />}
      />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
