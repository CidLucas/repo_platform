import { Routes, Route } from "react-router-dom";
import { publicRoutes } from "./publicRoutes";
import { dashboardRoutes } from "./dashboardRoutes";
import { PrivateRoute } from "./PrivateRoute";

export const AppRoutes = () => {
  return (
    <Routes>
      {/* Rotas públicas */}
      {publicRoutes.map((route) => (
        <Route key={route.path} path={route.path} element={route.element} />
      ))}

      {/* Rotas do dashboard (protegidas) */}
      {dashboardRoutes.map((route) => (
        <Route
          key={route.path}
          path={route.path}
          element={<PrivateRoute>{route.element}</PrivateRoute>}
        />
      ))}
    </Routes>
  );
};

export default AppRoutes;
