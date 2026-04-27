import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import Auth from "./onboarding/steps/Auth";
import Welcome from "./onboarding/steps/Welcome";
import BusinessDNA from "./onboarding/steps/BusinessDNA";
import DataFork from "./onboarding/steps/DataFork";
import AgentActivation from "./onboarding/steps/AgentActivation";
import CommandRules from "./onboarding/steps/CommandRules";
import LaunchPad from "./onboarding/steps/LaunchPad";
import Website from "./onboarding/steps/Website";
import PackageProposal from "./onboarding/steps/PackageProposal";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/onboarding" element={<Navigate to="/onboarding/auth" replace />} />
        <Route path="/onboarding/auth" element={<Auth />} />
        <Route path="/onboarding/website" element={<Website />} />
        <Route path="/onboarding/package" element={<PackageProposal />} />

        {/* Legacy flow routes kept as redirects while Phase B rolls out. */}
        <Route path="/onboarding/welcome" element={<Navigate to="/onboarding/website" replace />} />
        <Route path="/onboarding/dna" element={<Navigate to="/onboarding/website" replace />} />
        <Route path="/onboarding/data" element={<Navigate to="/onboarding/package" replace />} />
        <Route path="/onboarding/agents" element={<Navigate to="/onboarding/package" replace />} />
        <Route path="/onboarding/rules" element={<Navigate to="/onboarding/package" replace />} />
        <Route path="/onboarding/launch" element={<Navigate to="/dashboard" replace />} />

        {/* Hidden imports retained temporarily to avoid large ripples during migration. */}
        <Route path="/onboarding/_legacy/welcome" element={<Welcome />} />
        <Route path="/onboarding/_legacy/dna" element={<BusinessDNA />} />
        <Route path="/onboarding/_legacy/data" element={<DataFork />} />
        <Route path="/onboarding/_legacy/agents" element={<AgentActivation />} />
        <Route path="/onboarding/_legacy/rules" element={<CommandRules />} />
        <Route path="/onboarding/_legacy/launch" element={<LaunchPad />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
