import HomePage from "../pages/HomePage";
import SettingsPage from "../pages/SettingsPage";
import GenericOverviewPage from "../pages/GenericOverviewPage";
import GenericListPage from "../pages/GenericListPage";
import { clientesConfig, fornecedoresConfig, produtosConfig } from "../config";
import PedidosPage from "../pages/PedidosPage";
// Client management pages (formerly "admin" pages - now accessible to all authenticated users)
import AdminHomePage from "../pages/admin/AdminHomePage";
import AdminFontesPage from "../pages/admin/AdminFontesPage";
import AdminFontesDetalhesPage from "../pages/admin/AdminFontesDetalhesPage";
import AdminConnectorMappingPage from "../pages/admin/AdminConnectorMappingPage";
import AdminPlanosPage from "../pages/admin/AdminPlanosPage";
import AdminChatPage from "../pages/admin/AdminChatPage";
import AdminAjudaPage from "../pages/admin/AdminAjudaPage";
import AdminPrivacidadePage from "../pages/admin/AdminPrivacidadePage";
// Super admin pages (requires ADMIN tier)
import AdminClientesVizuPage from "../pages/admin/AdminClientesVizuPage";
import { AdminRoute } from "./AdminRoute";

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
    element: <SettingsPage />,
  },
  {
    path: "/dashboard/fornecedores",
    element: <GenericOverviewPage config={fornecedoresConfig} />,
  },
  {
    path: "/dashboard/fornecedores/lista",
    element: <GenericListPage config={fornecedoresConfig} />,
  },
  {
    path: "/dashboard/produtos",
    element: <GenericOverviewPage config={produtosConfig} />,
  },
  {
    path: "/dashboard/produtos/lista",
    element: <GenericListPage config={produtosConfig} />,
  },
  {
    path: "/dashboard/clientes",
    element: <GenericOverviewPage config={clientesConfig} />,
  },
  {
    path: "/dashboard/clientes/lista",
    element: <GenericListPage config={clientesConfig} />,
  },
  // Alias routes for Menu Rápido (English paths)
  {
    path: "/dashboard/suppliers",
    element: <GenericListPage config={fornecedoresConfig} />,
  },
  {
    path: "/dashboard/products",
    element: <GenericListPage config={produtosConfig} />,
  },
  {
    path: "/dashboard/pedidos",
    element: <PedidosPage />,
  },
  {
    path: "/dashboard/orders",
    element: <PedidosPage />,
  },
  // Client management routes (formerly "admin" routes - accessible to all authenticated users)
  {
    path: "/dashboard/admin",
    element: <AdminHomePage />,
  },
  {
    path: "/dashboard/admin/fontes",
    element: <AdminFontesPage />,
  },
  {
    path: "/dashboard/admin/fontes/:id",
    element: <AdminFontesDetalhesPage />,
  },
  {
    path: "/dashboard/admin/connectors/:credentialId/mapping",
    element: <AdminConnectorMappingPage />,
  },
  {
    path: "/dashboard/admin/planos",
    element: <AdminPlanosPage />,
  },
  {
    path: "/dashboard/admin/chat",
    element: <AdminChatPage />,
  },
  {
    path: "/dashboard/admin/ajuda",
    element: <AdminAjudaPage />,
  },
  {
    path: "/dashboard/admin/privacidade",
    element: <AdminPrivacidadePage />,
  },
  // Super Admin routes - requires ADMIN tier (checked via backend)
  {
    path: "/dashboard/super-admin/clientes",
    element: (
      <AdminRoute>
        <AdminClientesVizuPage />
      </AdminRoute>
    ),
    requiresAdmin: true,
  },
];
