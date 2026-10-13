import { Navigate, Route, Routes } from "react-router-dom";
import { LandingPage } from "./pages/LandingPage";
import { SignupPage } from "./pages/SignupPage";
import { CustomerLoginPage } from "./pages/CustomerLoginPage";
import { CustomerLayout } from "./pages/CustomerLayout";
import { DashboardPage } from "./pages/DashboardPage";
import { BuilderWizardPage } from "./pages/BuilderWizardPage";
import { CustomerAgentDetailPage } from "./pages/CustomerAgentDetailPage";
import { BuilderToolsPage } from "./pages/BuilderToolsPage";
import { BuilderSessionsPage } from "./pages/BuilderSessionsPage";
import { BuilderCustomersPage } from "./pages/BuilderCustomersPage";
import { BuilderLeadsPage } from "./pages/BuilderLeadsPage";
import { BuilderLeadDetailPage } from "./pages/BuilderLeadDetailPage";
import { BuilderAnalyticsPage } from "./pages/BuilderAnalyticsPage";
import { AdminLoginPage } from "./pages/AdminLoginPage";
import { AdminLayout } from "./pages/AdminLayout";
import { AgentsPage } from "./pages/AgentsPage";
import { AgentDetailPage } from "./pages/AgentDetailPage";
import { KnowledgePage } from "./pages/KnowledgePage";
import { ProvidersPage } from "./pages/ProvidersPage";
import { ProviderDetailPage } from "./pages/ProviderDetailPage";
import { ToolsPage } from "./pages/ToolsPage";
import { SessionsPage } from "./pages/SessionsPage";
import { CustomersPage } from "./pages/CustomersPage";
import { LeadsPage } from "./pages/LeadsPage";
import { LeadDetailPage } from "./pages/LeadDetailPage";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { SettingsPage } from "./pages/SettingsPage";

export default function App() {
  return (
    <div className="h-screen overflow-y-auto">
      <Routes>
        {/* Public marketing site + self-serve builder */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/login" element={<CustomerLoginPage />} />
        <Route element={<CustomerLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/dashboard/new" element={<BuilderWizardPage />} />
          <Route path="/dashboard/agents/:id" element={<CustomerAgentDetailPage />} />
          <Route path="/dashboard/tools" element={<BuilderToolsPage />} />
          <Route path="/dashboard/sessions" element={<BuilderSessionsPage />} />
          <Route path="/dashboard/customers" element={<BuilderCustomersPage />} />
          <Route path="/dashboard/leads" element={<BuilderLeadsPage />} />
          <Route path="/dashboard/leads/:id" element={<BuilderLeadDetailPage />} />
          <Route path="/dashboard/analytics" element={<BuilderAnalyticsPage />} />
        </Route>

        {/* Platform-operator admin dashboard (separate login/session) */}
        <Route path="/admin" element={<AdminLoginPage />} />
        <Route element={<AdminLayout />}>
          <Route path="/agents" element={<AgentsPage />} />
          <Route path="/agents/:id" element={<AgentDetailPage />} />
          <Route path="/agents/:id/knowledge" element={<KnowledgePage />} />
          <Route path="/providers" element={<ProvidersPage />} />
          <Route path="/providers/:id" element={<ProviderDetailPage />} />
          <Route path="/tools" element={<ToolsPage />} />
          <Route path="/sessions" element={<SessionsPage />} />
          <Route path="/customers" element={<CustomersPage />} />
          <Route path="/leads" element={<LeadsPage />} />
          <Route path="/leads/:id" element={<LeadDetailPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
