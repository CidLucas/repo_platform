import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import Auth from "./onboarding/steps/Auth";
import InfoForm from "./onboarding/steps/InfoForm";
import DataFork from "./onboarding/steps/DataFork";
import ColumnMapping from "./onboarding/steps/ColumnMapping";
import LaunchPad from "./onboarding/steps/LaunchPad";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />

        {/* ── Onboarding (4 steps + launch) ── */}
        <Route path="/onboarding/auth" element={<Auth />} />
        <Route path="/onboarding/info" element={<InfoForm />} />
        <Route path="/onboarding/data" element={<DataFork />} />
        <Route path="/onboarding/mapping" element={<ColumnMapping />} />
        <Route path="/onboarding/launch" element={<LaunchPad />} />

        {/* Legacy redirects */}
        <Route path="/onboarding" element={<Navigate to="/onboarding/auth" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
