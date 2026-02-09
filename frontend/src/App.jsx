import { Routes, Route, Navigate } from "react-router-dom";

import Journey from "./components/Journey/Journey";
import ScreenHome from "./components/Screen/ScreenHome";
import { useApp } from "./state_imp/AppContext";

/**
 * App shell is ROUTER driven.
 * No phase logic here.
 * No demo logic here.
 * This file ONLY decides which page to show.
 */
function App() {
  const { state, actions } = useApp();

  return (
    <Routes>
  <Route path="/" element={<Journey state={state} actions={actions} />} />
  <Route path="/screen" element={<ScreenHome state={state} actions={actions} />} />
  <Route path="*" element={<Navigate to="/" replace />} />
</Routes>

  );
}

export default App;
