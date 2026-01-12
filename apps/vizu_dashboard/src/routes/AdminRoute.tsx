import { Navigate } from "react-router-dom";
import { Box, Text, VStack, Button, Center } from "@chakra-ui/react";
import { useAuth } from "../hooks/useAuth";
import { FiShield } from "react-icons/fi";

interface AdminRouteProps {
  children: React.ReactNode;
}

/**
 * Component to protect admin-only routes.
 * Checks if the logged-in user has admin role.
 */
export const AdminRoute: React.FC<AdminRouteProps> = ({ children }) => {
  const { user } = useAuth();

  // Check if user has admin role
  const isAdmin =
    user?.user_metadata?.role === 'admin' ||
    user?.app_metadata?.role === 'admin';

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
              Apenas administradores podem visualizar esta página.
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
