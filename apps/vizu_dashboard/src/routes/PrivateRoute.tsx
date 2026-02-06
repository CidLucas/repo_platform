import { Navigate, useLocation } from "react-router-dom";
import { Box, Spinner, Center, VStack, Text } from "@chakra-ui/react";
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
 * OAuth callback handling is done by AuthContext via onAuthStateChange.
 * Em modo desenvolvimento (VITE_DEV_BYPASS_AUTH=true), permite acesso sem login.
 */
export const PrivateRoute: React.FC<PrivateRouteProps> = ({ children }) => {
  const location = useLocation();
  const { user, isLoading } = useAuth();

  // Bypass auth in development mode
  if (DEV_BYPASS_AUTH) {
    return <>{children}</>;
  }

  // Show loading while checking auth or processing OAuth callback
  // AuthContext keeps isLoading=true until session is established
  if (isLoading) {
    const isOAuthCallback = window.location.hash.includes('access_token') ||
      window.location.search.includes('code=');
    return (
      <Center h="100vh" bg="white">
        <VStack spacing={4}>
          <Spinner size="xl" color="black" thickness="3px" />
          {isOAuthCallback && (
            <Text fontSize="lg" color="gray.600">Completing sign in...</Text>
          )}
        </VStack>
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
