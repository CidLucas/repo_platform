import { Box, VStack, Text, Divider, Icon } from '@chakra-ui/react';
import { NavLink } from 'react-router-dom';
import {
  FiHome,
  FiDatabase,
  FiShield,
  FiCreditCard,
  FiHelpCircle,
  FiBook,
  FiCpu,
  FiChevronRight,
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
          px={3}
          py={2.5}
          borderRadius="lg"
          bg={isActive ? undefined : 'transparent'}
          bgGradient={isActive ? 'linear(to-r, #4361ee, #7209b7)' : undefined}
          color={isActive ? 'white' : 'gray.300'}
          fontWeight={isActive ? 'medium' : 'normal'}
          cursor="pointer"
          transition="all 0.2s"
          boxShadow={isActive ? 'lg' : 'none'}
          _hover={{
            bg: isActive ? undefined : 'whiteAlpha.50',
            color: 'white',
          }}
          w="full"
        >
          <Icon as={icon} boxSize={4} flexShrink={0} />
          <Text fontSize="sm" fontWeight="inherit" letterSpacing="-0.15px" flex={1}>
            {label}
          </Text>
          {isActive && <Icon as={FiChevronRight} boxSize={4} />}
        </Box>
      )}
    </NavLink>
  );
};

export const AdminSidebar = () => {
  return (
    <Box
      as="aside"
      w="280px"
      minH="calc(100vh - 64px)"
      bgGradient="linear(to-b, #141620, #181b28, #1a1d2e)"
      borderRight="1px solid"
      borderColor="rgba(255,255,255,0.08)"
      color="white"
      boxShadow="xl"
      display="flex"
      flexDirection="column"
    >
      <Box p={6}>
        <Text fontSize="lg" fontWeight="semibold" mb={1} color="white">Admin Panel</Text>
        <Text fontSize="sm" color="gray.400">System Configuration</Text>
      </Box>
      <VStack spacing={1} align="stretch" px={3} pb={4}>
        <SidebarItem
          to="/dashboard/admin"
          icon={FiHome}
          label="Início"
        />
        <SidebarItem
          to="/dashboard/admin/fontes"
          icon={FiDatabase}
          label="Fonte de Dados"
        />
        <SidebarItem
          to="/dashboard/admin/knowledge-base"
          icon={FiBook}
          label="Base de Conhecimento"
        />
        <SidebarItem
          to="/dashboard/admin/privacidade"
          icon={FiShield}
          label="Dados e privacidade"
        />
        <SidebarItem
          to="/dashboard/admin/agents"
          icon={FiCpu}
          label="AI Agents"
        />
        <SidebarItem
          to="/dashboard/admin/planos"
          icon={FiCreditCard}
          label="Planos contratado"
        />

        <Divider my={2} borderColor="whiteAlpha.100" />

        <SidebarItem
          to="/dashboard/admin/ajuda"
          icon={FiHelpCircle}
          label="Ajuda"
        />
      </VStack>
    </Box>
  );
};

export default AdminSidebar;
