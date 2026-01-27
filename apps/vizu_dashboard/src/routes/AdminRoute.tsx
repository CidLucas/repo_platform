import { useState, useEffect } from "react";
import { Box, Text, VStack, Button, Center, Spinner } from "@chakra-ui/react";
import { useAuth } from "../hooks/useAuth";
import { FiShield } from "react-icons/fi";
import { isCurrentUserAdmin } from "../services/adminService";

interface AdminRouteProps {
  children: React.ReactNode;
}

/**
 * Component to protect admin-only routes.
 * Checks if the logged-in user has ADMIN tier in cliente_vizu table.
 *
 * This check is done via the backend API, which validates the JWT
 * and checks the user's tier in the database.
 */
export const AdminRoute: React.FC<AdminRouteProps> = ({ children }) => {
  const { user, isLoading: authLoading } = useAuth();
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAdminAccess = async () => {
      if (!user) {
        setIsAdmin(false);
        setLoading(false);
        return;
      }

      try {
        const adminStatus = await isCurrentUserAdmin();
        setIsAdmin(adminStatus);
      } catch (error) {
        console.error("Failed to check admin status:", error);
        setIsAdmin(false);
      } finally {
        setLoading(false);
      }
    };

    if (!authLoading) {
      checkAdminAccess();
    }
  }, [user, authLoading]);

  // Show loading while checking auth or admin status
  if (authLoading || loading) {
    return (
      <Center h="100vh" bg="white">
        <VStack spacing={4}>
          <Spinner size="xl" color="gray.500" />
          <Text color="gray.500">Verificando permissões...</Text>
        </VStack>
      </Center>
    );
  }

  // If user is not admin, show access denied page
  if (!isAdmin) {
    return (
      <Center h="100vh" bg="white">
        <VStack spacing={6}>
          <Box
            p={4}
            borderRadius="full"
            bg="red.50"
            color="red.500"
          >
            <FiShield size={48} />
          </Box>
          <VStack spacing={2}>
            <Text fontSize="24px" fontWeight="600" color="gray.900">
              Acesso Negado
            </Text>
            <Text fontSize="16px" color="gray.600" textAlign="center" maxW="400px">
              Você não tem permissão para acessar esta área.
              Apenas usuários com tier ADMIN podem visualizar esta página.
            </Text>
          </VStack>
          <Button
            colorScheme="black"
            bg="black"
            color="white"
            onClick={() => window.history.back()}
            _hover={{ bg: "gray.800" }}
          >
            Voltar
          </Button>
        </VStack>
      </Center>
    );
  }

  return <>{children}</>;
};

export default AdminRoute;
