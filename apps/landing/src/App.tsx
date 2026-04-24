import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import Auth from "./onboarding/steps/Auth";
import Welcome from "./onboarding/steps/Welcome";
import BusinessDNA from "./onboarding/steps/BusinessDNA";
import DataFork from "./onboarding/steps/DataFork";
import AgentActivation from "./onboarding/steps/AgentActivation";
import CommandRules from "./onboarding/steps/CommandRules";
import LaunchPad from "./onboarding/steps/LaunchPad";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/onboarding" element={<Navigate to="/onboarding/auth" replace />} />
        <Route path="/onboarding/auth" element={<Auth />} />
        <Route path="/onboarding/welcome" element={<Welcome />} />
        <Route path="/onboarding/dna" element={<BusinessDNA />} />
        <Route path="/onboarding/data" element={<DataFork />} />
        <Route path="/onboarding/agents" element={<AgentActivation />} />
        <Route path="/onboarding/rules" element={<CommandRules />} />
        <Route path="/onboarding/launch" element={<LaunchPad />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
