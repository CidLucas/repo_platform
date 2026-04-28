import { Suspense, lazy } from "react";
import { Navigate } from "react-router-dom";
import { Flex, Spinner } from "@chakra-ui/react";
import HomePage from "../pages/HomePage";
// Client management pages (formerly "admin" pages - now accessible to all authenticated users)
// Super admin pages (requires ADMIN tier)
import { AdminRoute } from "./AdminRoute";

const InboxPage = lazy(() => import("../pages/InboxPage"));
const ReportsPage = lazy(() => import("../pages/ReportsPage"));

const AdminHomePage = lazy(() => import("../pages/admin/AdminHomePage"));
const AdminFontesPage = lazy(() => import("../pages/admin/AdminFontesPage"));
const AdminFontesDetalhesPage = lazy(() => import("../pages/admin/AdminFontesDetalhesPage"));
const AdminConnectorMappingPage = lazy(() => import("../pages/admin/AdminConnectorMappingPage"));
const AdminPlanosPage = lazy(() => import("../pages/admin/AdminPlanosPage"));
const AdminChatPage = lazy(() => import("../pages/admin/AdminChatPage"));
const AdminAjudaPage = lazy(() => import("../pages/admin/AdminAjudaPage"));
const AdminPrivacidadePage = lazy(() => import("../pages/admin/AdminPrivacidadePage"));
const AdminKnowledgeBasePage = lazy(() => import("../pages/admin/AdminKnowledgeBasePage"));
const AdminAgentBuilderPage = lazy(() => import("../pages/admin/AdminAgentBuilderPage"));
const AdminAgentBuilderEditorPage = lazy(() => import("../pages/admin/AdminAgentBuilderEditorPage"));
const AdminAgentsPage = lazy(() => import("../pages/admin/AdminAgentsPage"));
const AdminConnectorsPage = lazy(() => import("../pages/admin/AdminConnectorsPage"));
const OnboardingPage = lazy(() => import("../pages/admin/OnboardingPage"));
const AdminClientesBluPage = lazy(() => import("../pages/admin/AdminClientesBluPage"));
const AdminActivationFunnelPage = lazy(() => import("../pages/admin/AdminActivationFunnelPage"));

const routeFallback = (
  <Flex minH="220px" align="center" justify="center">
    <Spinner color="blue.400" size="lg" />
  </Flex>
);

const lazyElement = (element: React.ReactNode): React.ReactNode => (
  <Suspense fallback={routeFallback}>{element}</Suspense>
);

interface RouteConfig {
  path: string;
  element: React.ReactNode;
  requiresAdmin?: boolean;
}

export const dashboardRoutes: RouteConfig[] = [
  {
    path: "/dashboard",
    element: <HomePage />,
  },
  {
    path: "/dashboard/settings",
    element: <Navigate to="/dashboard/configurar" replace />,
  },
  {
    path: "/dashboard/inbox",
    element: lazyElement(<InboxPage />),
  },
  {
    path: "/dashboard/reports",
    element: lazyElement(<ReportsPage />),
  },
  {
    path: "/dashboard/relatorios",
    element: lazyElement(<ReportsPage />),
  },
  // Client management routes (formerly "admin" routes - accessible to all authenticated users)
  {
    path: "/dashboard/admin",
    element: lazyElement(<AdminHomePage />),
  },
  {
    path: "/dashboard/configurar",
    element: lazyElement(<AdminHomePage />),
  },
  {
    path: "/dashboard/admin/fontes",
    element: lazyElement(<AdminFontesPage />),
  },
  {
    path: "/dashboard/configurar/fontes",
    element: lazyElement(<AdminFontesPage />),
  },
  {
    path: "/dashboard/admin/fontes/:id",
    element: lazyElement(<AdminFontesDetalhesPage />),
  },
  {
    path: "/dashboard/configurar/fontes/:id",
    element: lazyElement(<AdminFontesDetalhesPage />),
  },
  {
    path: "/dashboard/admin/connectors/:credentialId/mapping",
    element: lazyElement(<AdminConnectorMappingPage />),
  },
  {
    path: "/dashboard/configurar/connectors/:credentialId/mapping",
    element: lazyElement(<AdminConnectorMappingPage />),
  },
  {
    path: "/dashboard/admin/conectores",
    element: lazyElement(<AdminConnectorsPage />),
  },
  {
    path: "/dashboard/configurar/conectores",
    element: lazyElement(<AdminConnectorsPage />),
  },
  {
    path: "/dashboard/admin/planos",
    element: lazyElement(<AdminPlanosPage />),
  },
  {
    path: "/dashboard/configurar/planos",
    element: lazyElement(<AdminPlanosPage />),
  },
  {
    path: "/dashboard/admin/chat",
    element: lazyElement(<AdminChatPage />),
  },
  {
    path: "/dashboard/configurar/chat",
    element: lazyElement(<AdminChatPage />),
  },
  {
    path: "/dashboard/admin/ajuda",
    element: lazyElement(<AdminAjudaPage />),
  },
  {
    path: "/dashboard/configurar/ajuda",
    element: lazyElement(<AdminAjudaPage />),
  },
  {
    path: "/dashboard/admin/privacidade",
    element: lazyElement(<AdminPrivacidadePage />),
  },
  {
    path: "/dashboard/configurar/privacidade",
    element: lazyElement(<AdminPrivacidadePage />),
  },
  {
    path: "/dashboard/admin/knowledge-base",
    element: lazyElement(<AdminKnowledgeBasePage />),
  },
  {
    path: "/dashboard/configurar/knowledge-base",
    element: lazyElement(<AdminKnowledgeBasePage />),
  },
  {
    path: "/dashboard/admin/onboarding",
    element: lazyElement(<OnboardingPage />),
  },
  {
    path: "/dashboard/configurar/onboarding",
    element: lazyElement(<OnboardingPage />),
  },
  {
    path: "/dashboard/admin/agents",
    element: lazyElement(<AdminAgentsPage />),
  },
  {
    path: "/dashboard/configurar/agents",
    element: lazyElement(<AdminAgentsPage />),
  },
  {
    path: "/dashboard/admin/agents/:agentId",
    element: lazyElement(
      <AdminRoute>
        <AdminAgentBuilderEditorPage />
      </AdminRoute>
    ),
    requiresAdmin: true,
  },
  {
    path: "/dashboard/configurar/agents/:agentId",
    element: lazyElement(
      <AdminRoute>
        <AdminAgentBuilderEditorPage />
      </AdminRoute>
    ),
    requiresAdmin: true,
  },
  // Legacy routes kept for backwards compatibility
  {
    path: "/dashboard/admin/agent-builder",
    element: lazyElement(
      <AdminRoute>
        <AdminAgentBuilderPage />
      </AdminRoute>
    ),
    requiresAdmin: true,
  },
  {
    path: "/dashboard/configurar/agent-builder",
    element: lazyElement(
      <AdminRoute>
        <AdminAgentBuilderPage />
      </AdminRoute>
    ),
    requiresAdmin: true,
  },
  {
    path: "/dashboard/admin/agent-builder/:agentId",
    element: lazyElement(
      <AdminRoute>
        <AdminAgentBuilderEditorPage />
      </AdminRoute>
    ),
    requiresAdmin: true,
  },
  {
    path: "/dashboard/configurar/agent-builder/:agentId",
    element: lazyElement(
      <AdminRoute>
        <AdminAgentBuilderEditorPage />
      </AdminRoute>
    ),
    requiresAdmin: true,
  },
  // Redirect legacy dimension routes to Mission Control.
  {
    path: "/dashboard/clientes",
    element: <Navigate to="/dashboard" replace />,
  },
  {
    path: "/dashboard/fornecedores",
    element: <Navigate to="/dashboard" replace />,
  },
  {
    path: "/dashboard/produtos",
    element: <Navigate to="/dashboard" replace />,
  },
  {
    path: "/dashboard/clientes/lista",
    element: <Navigate to="/dashboard" replace />,
  },
  {
    path: "/dashboard/fornecedores/lista",
    element: <Navigate to="/dashboard" replace />,
  },
  {
    path: "/dashboard/produtos/lista",
    element: <Navigate to="/dashboard" replace />,
  },
  {
    path: "/dashboard/suppliers",
    element: <Navigate to="/dashboard" replace />,
  },
  {
    path: "/dashboard/products",
    element: <Navigate to="/dashboard" replace />,
  },
  // Backward-compat redirects (optional canonical move to /configurar namespace)
  {
    path: "/dashboard/admin/*",
    element: <Navigate to="/dashboard/configurar" replace />,
  },
  // Super Admin routes - requires ADMIN tier (checked via backend)
  {
    path: "/dashboard/super-admin/clientes",
    element: lazyElement(
      <AdminRoute>
        <AdminClientesBluPage />
      </AdminRoute>
    ),
    requiresAdmin: true,
  },
  {
    path: "/dashboard/super-admin/activation-funnel",
    element: lazyElement(
      <AdminRoute>
        <AdminActivationFunnelPage />
      </AdminRoute>
    ),
    requiresAdmin: true,
  },
];
