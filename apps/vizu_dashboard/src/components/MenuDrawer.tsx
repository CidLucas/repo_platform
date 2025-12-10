import {
  Drawer,
  DrawerBody,
  DrawerHeader,
  DrawerOverlay,
  DrawerContent,
  DrawerCloseButton,
  SimpleGrid,
  Box,
  Text,
  Icon,
} from '@chakra-ui/react';
import { useNavigate } from 'react-router-dom';
import { 
  FiUsers, 
  FiShoppingCart, 
  FiPackage, 
  FiTarget,
  FiPlus,
  FiDatabase,
  FiDollarSign,
  FiTrendingUp,
} from 'react-icons/fi';

interface MenuDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

// Menu items baseados no design do Figma
const menuItems = [
  {
    label: 'LISTA DE FORNECEDORES',
    icon: FiUsers,
    color: '#92daff',
    path: '/dashboard/suppliers',
  },
  {
    label: 'LISTA DE PEDIDOS',
    icon: FiShoppingCart,
    color: '#f9bbcb',
    path: '/dashboard/orders',
  },
  {
    label: 'LISTA DE PRODUTOS',
    icon: FiPackage,
    color: '#fff856',
    path: '/dashboard/products',
  },
  {
    label: 'MINHAS METAS',
    icon: FiTarget,
    color: '#24bd31',
    path: '/dashboard/goals',
  },
  {
    label: 'NOVO PEDIDO',
    icon: FiPlus,
    color: '#f9bbcb',
    path: '/dashboard/orders/new',
  },
  {
    label: 'NOVA FONTE DADOS',
    icon: FiDatabase,
    color: '#ff8b00',
    path: '/dashboard/admin/fontes',
  },
  {
    label: 'MÓDULO FINANCEIRO',
    icon: FiDollarSign,
    color: '#ff8b00',
    path: '/dashboard/financial',
  },
  {
    label: 'ADICIONAR META',
    icon: FiTrendingUp,
    color: '#24bd31',
    path: '/dashboard/goals/new',
  },
];

interface MenuCardProps {
  label: string;
  icon: React.ElementType;
  color: string;
  onClick: () => void;
}

const MenuCard = ({ label, icon, color, onClick }: MenuCardProps) => {
  return (
    <Box
      bg={color}
      borderRadius="16px"
      p={4}
      cursor="pointer"
      transition="all 0.2s"
      _hover={{
        transform: 'scale(1.02)',
        shadow: 'md',
      }}
      _active={{
        transform: 'scale(0.98)',
      }}
      onClick={onClick}
      minH="100px"
      display="flex"
      flexDirection="column"
      justifyContent="space-between"
    >
      <Icon as={icon} boxSize={6} color="black" />
      <Text
        fontSize="11px"
        fontWeight="bold"
        color="black"
        textTransform="uppercase"
        lineHeight="1.2"
        mt={2}
      >
        {label}
      </Text>
    </Box>
  );
};

export const MenuDrawer = ({ isOpen, onClose }: MenuDrawerProps) => {
  const navigate = useNavigate();

  const handleNavigate = (path: string) => {
    navigate(path);
    onClose();
  };

  return (
    <Drawer isOpen={isOpen} placement="right" onClose={onClose} size="sm">
      <DrawerOverlay />
      <DrawerContent maxW="360px">
        <DrawerCloseButton />
        <DrawerHeader borderBottomWidth="1px" pb={4}>
          <Text fontSize="lg" fontWeight="medium">
            Menu Rápido
          </Text>
        </DrawerHeader>

        <DrawerBody py={6}>
          <SimpleGrid columns={2} spacing={4}>
            {menuItems.map((item) => (
              <MenuCard
                key={item.label}
                label={item.label}
                icon={item.icon}
                color={item.color}
                onClick={() => handleNavigate(item.path)}
              />
            ))}
          </SimpleGrid>
        </DrawerBody>
      </DrawerContent>
    </Drawer>
  );
};
