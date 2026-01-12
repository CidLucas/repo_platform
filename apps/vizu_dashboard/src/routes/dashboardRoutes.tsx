import HomePage from "../pages/HomePage";
import ChartsPage from "../pages/ChartsPage";
import SettingsPage from "../pages/SettingsPage";
import FornecedoresPage from "../pages/FornecedoresPage";
import FornecedoresListPage from "../pages/FornecedoresListPage";
import ProdutosPage from "../pages/ProdutosPage";
import ProdutosListPage from "../pages/ProdutosListPage";
import ClientesPage from "../pages/ClientesPage";
import ClientesListPage from "../pages/ClientesListPage";
// Client management pages (formerly "admin" pages - now accessible to all authenticated users)
import AdminHomePage from "../pages/admin/AdminHomePage";
import AdminFontesPage from "../pages/admin/AdminFontesPage";
import AdminFontesDetalhesPage from "../pages/admin/AdminFontesDetalhesPage";
import AdminPlanosPage from "../pages/admin/AdminPlanosPage";
import AdminChatPage from "../pages/admin/AdminChatPage";
import AdminAjudaPage from "../pages/admin/AdminAjudaPage";
import AdminPrivacidadePage from "../pages/admin/AdminPrivacidadePage";

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
    path: "/dashboard/charts",
    element: <ChartsPage />,
  },
  {
    path: "/dashboard/settings",
    element: <SettingsPage />,
  },
  {
    path: "/dashboard/fornecedores",
    element: <FornecedoresPage />,
  },
  {
    path: "/dashboard/fornecedores/lista",
    element: <FornecedoresListPage />,
  },
  {
    path: "/dashboard/produtos",
    element: <ProdutosPage />,
  },
  {
    path: "/dashboard/produtos/lista",
    element: <ProdutosListPage />,
  },
  {
    path: "/dashboard/clientes",
    element: <ClientesPage />,
  },
  {
    path: "/dashboard/clientes/lista",
    element: <ClientesListPage />,
  },
  // Alias routes for Menu Rápido (English paths)
  {
    path: "/dashboard/suppliers",
    element: <FornecedoresListPage />,
  },
  {
    path: "/dashboard/products",
    element: <ProdutosListPage />,
  },
  // Placeholder routes for Menu Rápido items (to be implemented)
  {
    path: "/dashboard/orders",
    element: <HomePage />, // Placeholder - redirect to home for now
  },
  {
    path: "/dashboard/orders/new",
    element: <HomePage />, // Placeholder - redirect to home for now
  },
  {
    path: "/dashboard/goals",
    element: <HomePage />, // Placeholder - redirect to home for now
  },
  {
    path: "/dashboard/goals/new",
    element: <HomePage />, // Placeholder - redirect to home for now
  },
  {
    path: "/dashboard/financial",
    element: <HomePage />, // Placeholder - redirect to home for now
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
];
