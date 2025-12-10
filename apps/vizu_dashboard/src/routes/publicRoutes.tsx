import LandingFinalPage from "../pages/LandingFinalPage";
import LoginPage from "../pages/LoginPage";

interface RouteConfig {
  path: string;
  element: React.ReactNode;
}

export const publicRoutes: RouteConfig[] = [
  {
    path: "/",
    element: <LandingFinalPage />,
  },
  {
    path: "/login",
    element: <LoginPage />,
  },
];
