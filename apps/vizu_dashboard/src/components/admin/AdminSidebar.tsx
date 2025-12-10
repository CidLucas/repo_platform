import { Box, VStack, Text, Divider, Icon } from '@chakra-ui/react';
import { NavLink } from 'react-router-dom';
import { 
  FiHome, 
  FiDatabase, 
  FiShield, 
  FiMessageSquare, 
  FiCreditCard, 
  FiHelpCircle 
} from 'react-icons/fi';

interface SidebarItemProps {
  to: string;
  icon: React.ElementType;
  label: string;
}

const SidebarItem = ({ to, icon, label }: SidebarItemProps) => {
  return (
    <NavLink to={to} end style={{ width: '100%' }}>
      {({ isActive }) => (
        <Box
          display="flex"
          alignItems="center"
          gap={3}
          px={4}
          py={3}
          borderRadius="full"
          bg={isActive ? 'black' : 'transparent'}
          color={isActive ? 'white' : 'black'}
          cursor="pointer"
          transition="all 0.2s"
          _hover={{
            bg: isActive ? 'black' : 'gray.100',
          }}
          w="full"
        >
          <Icon as={icon} boxSize={5} />
          <Text fontSize="14px" fontWeight="normal" letterSpacing="-0.15px">
            {label}
          </Text>
        </Box>
      )}
    </NavLink>
  );
};

export const AdminSidebar = () => {
  return (
    <Box
      as="aside"
      w="256px"
      minH="calc(100vh - 61px)"
      borderRight="1px solid"
      borderColor="gray.200"
      bg="white"
      py={4}
    >
      <VStack spacing={1} align="stretch" px={3}>
        <SidebarItem 
          to="/dashboard/admin" 
          icon={FiHome} 
          label="Início" 
        />
        <SidebarItem 
          to="/dashboard/admin/fontes" 
          icon={FiDatabase} 
          label="Minhas fontes" 
        />
        <SidebarItem 
          to="/dashboard/admin/privacidade" 
          icon={FiShield} 
          label="Dados e privacidade" 
        />
        <SidebarItem 
          to="/dashboard/admin/chat" 
          icon={FiMessageSquare} 
          label="Chat admin" 
        />
        <SidebarItem 
          to="/dashboard/admin/planos" 
          icon={FiCreditCard} 
          label="Planos contratado" 
        />
        
        <Divider my={2} borderColor="gray.200" />
        
        <SidebarItem 
          to="/dashboard/admin/ajuda" 
          icon={FiHelpCircle} 
          label="Ajuda" 
        />
      </VStack>
    </Box>
  );
};

export { AdminSidebar };
export default AdminSidebar;
