import { Navigate, useLocation } from "react-router-dom";
import { Box, Spinner, Center } from "@chakra-ui/react";
import { useAuth } from "../hooks/useAuth";

interface PrivateRouteProps {
  children: React.ReactNode;
}

// Dev mode bypass - set VITE_DEV_BYPASS_AUTH=true in .env to skip auth
const DEV_BYPASS_AUTH = import.meta.env.VITE_DEV_BYPASS_AUTH === "true";

/**
 * Componente para proteger rotas que requerem autenticação.
 * Usa Supabase Auth para verificar se o usuário está logado.
 * 
 * Em modo desenvolvimento (VITE_DEV_BYPASS_AUTH=true), permite acesso sem login.
 */
export const PrivateRoute: React.FC<PrivateRouteProps> = ({ children }) => {
  const location = useLocation();
  const { user, isLoading } = useAuth();

  // Bypass auth in development mode
  if (DEV_BYPASS_AUTH) {
    return <>{children}</>;
  }

  // Exibe loading enquanto verifica autenticação
  if (isLoading) {
    return (
      <Center h="100vh" bg="white">
        <Box textAlign="center">
          <Spinner size="xl" color="black" thickness="3px" />
        </Box>
      </Center>
    );
  }

  // Se não estiver autenticado, redireciona para login
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

export default PrivateRoute;
