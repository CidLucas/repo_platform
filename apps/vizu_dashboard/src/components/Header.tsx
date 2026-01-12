import {
  Avatar,
  Flex,
  Spacer,
  IconButton,
  HStack,
  Text,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  MenuDivider,
  Box,
  useDisclosure,
} from '@chakra-ui/react';
import { BellIcon, ChatIcon } from '@chakra-ui/icons';
import { FiUser, FiSettings, FiShield, FiLogOut, FiGrid } from 'react-icons/fi';
import { Link, useNavigate } from 'react-router-dom';
import { useChat } from '../contexts/ChatContext';
import { useContext } from 'react';
import { AuthContext } from '../contexts/AuthContext';
import Logo from '../assets/logo.svg?react';
import { MenuDrawer } from './MenuDrawer';

export const Header = () => {
  const { toggleChat } = useChat();
  const navigate = useNavigate();
  const { isOpen: isMenuOpen, onOpen: onMenuOpen, onClose: onMenuClose } = useDisclosure();
  const auth = useContext(AuthContext);

  // Get user name from auth context - fallback to first part of email if no display name
  const userName = auth?.user?.user_metadata?.full_name ||
                   auth?.user?.email?.split('@')[0] ||
                   'Usuário';

  // Check if user is admin from auth context - checks for admin role in user metadata
  const isAdmin = auth?.user?.user_metadata?.role === 'admin' ||
                  auth?.user?.app_metadata?.role === 'admin' ||
                  false;

  const handleLogout = async () => {
    try {
      await auth?.signOut();
      navigate('/login');
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };
  
  return (
    <>
      <Flex 
        as="header" 
        py={3} 
        px={6} 
        align="center" 
        width="100%" 
        bg="white" 
        borderBottom="1px solid"
        borderColor="gray.200"
      >
        {/* Logo */}
        <Link to="/dashboard">
          <Logo style={{ height: '13.0657px', width: '36.8166px' }} />
        </Link>
        
        <Spacer />
        
        {/* Action Buttons */}
        <HStack spacing={3}>
          <IconButton
            aria-label="Chat"
            icon={<ChatIcon />}
            variant="ghost"
            colorScheme="gray"
            borderRadius="full"
            size="md"
            onClick={toggleChat}
          />
          <IconButton
            aria-label="Notifications"
            icon={<BellIcon />}
            variant="ghost"
            colorScheme="gray"
            borderRadius="full"
            size="md"
          />
          
          {/* Menu Grid Button */}
          <IconButton
            aria-label="Menu"
            icon={<FiGrid />}
            variant="ghost"
            colorScheme="gray"
            borderRadius="full"
            size="md"
            onClick={onMenuOpen}
          />
          
          {/* User Avatar with Dropdown Menu */}
          <Menu>
          <MenuButton>
            <Avatar
              name={userName}
              bg="black"
              color="white"
              size="sm"
              fontSize="xs"
              cursor="pointer"
              _hover={{ opacity: 0.8 }}
            />
          </MenuButton>
          <MenuList shadow="lg" borderRadius="12px" py={2}>
            {/* User Info */}
            <Box px={4} py={2} mb={2}>
              <Text fontWeight="medium" fontSize="sm">{userName}</Text>
              <Text fontSize="xs" color="gray.500">{auth?.user?.email || 'Sem email'}</Text>
            </Box>
            <MenuDivider />
            
            {/* Menu Items */}
            <MenuItem 
              icon={<FiUser />} 
              fontSize="sm"
              onClick={() => navigate('/dashboard/profile')}
            >
              Meu Perfil
            </MenuItem>
            <MenuItem 
              icon={<FiSettings />} 
              fontSize="sm"
              onClick={() => navigate('/dashboard/settings')}
            >
              Configurações
            </MenuItem>
            
            {/* Admin Link - Only show for admins */}
            {isAdmin && (
              <>
                <MenuDivider />
                <MenuItem 
                  icon={<FiShield />} 
                  fontSize="sm"
                  fontWeight="medium"
                  color="purple.600"
                  onClick={() => navigate('/dashboard/admin')}
                >
                  Painel Admin
                </MenuItem>
              </>
            )}
            
            <MenuDivider />
            <MenuItem
              icon={<FiLogOut />}
              fontSize="sm"
              color="red.500"
              onClick={handleLogout}
            >
              Sair
            </MenuItem>
          </MenuList>
        </Menu>
      </HStack>
    </Flex>
    
    {/* Menu Drawer */}
    <MenuDrawer isOpen={isMenuOpen} onClose={onMenuClose} />
  </>
  );
};
