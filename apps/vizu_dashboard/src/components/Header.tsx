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
  Button,
} from '@chakra-ui/react';
import { BellIcon, ChatIcon } from '@chakra-ui/icons';
import { FiUser, FiSettings, FiShield, FiLogOut, FiGrid } from 'react-icons/fi';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useChat } from '../contexts/ChatContext';
import { useTenant } from '../contexts/TenantContext';
import { useContext } from 'react';
import { AuthContext } from '../contexts/AuthContext';
import Logo from '../assets/logo.svg?react';
import { MenuDrawer } from './MenuDrawer';

export const Header = () => {
  const { toggleChat } = useChat();
  const navigate = useNavigate();
  const location = useLocation();
  const tenant = useTenant();
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
        h="64px"
        px={6}
        align="center"
        width="100%"
        bgGradient="linear(to-r, #001f3f, #003366)"
        position="sticky"
        top={0}
        zIndex={20}
      >
        {/* Logo with gradient effect */}
        <Link to="/dashboard">
          <Box
            sx={{
              '& svg': {
                filter: 'brightness(0) invert(1)',
              },
            }}
          >
            <Logo style={{ height: '13.0657px', width: '36.8166px' }} />
          </Box>
        </Link>

        {/* Nav Buttons — Dashboard & Admin */}
        <HStack spacing={1} ml={6}>
          <Button
            size="sm"
            variant="ghost"
            color={location.pathname === '/dashboard' || (!location.pathname.startsWith('/dashboard/admin') && location.pathname.startsWith('/dashboard')) ? 'white' : 'whiteAlpha.600'}
            bg={location.pathname === '/dashboard' || (!location.pathname.startsWith('/dashboard/admin') && location.pathname.startsWith('/dashboard')) ? 'whiteAlpha.200' : 'transparent'}
            fontWeight="medium"
            fontSize="sm"
            borderRadius="lg"
            _hover={{ bg: 'whiteAlpha.200', color: 'white' }}
            onClick={() => navigate('/dashboard')}
          >
            Dashboard
          </Button>
          <Button
            size="sm"
            variant="ghost"
            color={location.pathname.startsWith('/dashboard/admin') ? 'white' : 'whiteAlpha.600'}
            bg={location.pathname.startsWith('/dashboard/admin') ? 'whiteAlpha.200' : 'transparent'}
            fontWeight="medium"
            fontSize="sm"
            borderRadius="lg"
            leftIcon={<FiShield size={14} />}
            _hover={{ bg: 'whiteAlpha.200', color: 'white' }}
            onClick={() => navigate('/dashboard/admin')}
          >
            Admin
          </Button>
        </HStack>

        <Spacer />

        {/* Action Buttons */}
        <HStack spacing={3}>
          {tenant.features.canUseAgent && (
            <IconButton
              aria-label="Chat"
              icon={<ChatIcon />}
              variant="ghost"
              color="white"
              borderRadius="full"
              size="md"
              onClick={toggleChat}
              _hover={{ bg: 'whiteAlpha.200' }}
            />
          )}
          <IconButton
            aria-label="Notifications"
            icon={<BellIcon />}
            variant="ghost"
            color="white"
            borderRadius="full"
            size="md"
            _hover={{ bg: 'whiteAlpha.200' }}
          />

          {/* Menu Grid Button */}
          <IconButton
            aria-label="Menu"
            icon={<FiGrid />}
            variant="ghost"
            color="white"
            borderRadius="full"
            size="md"
            onClick={onMenuOpen}
            _hover={{ bg: 'whiteAlpha.200' }}
          />

          {/* User Avatar with Dropdown Menu */}
          <Menu>
            <MenuButton>
              <Avatar
                name={userName}
                bg="whiteAlpha.300"
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
                <Text fontWeight="medium" fontSize="sm" color="white">{userName}</Text>
                <Text fontSize="xs" color="whiteAlpha.600">{auth?.user?.email || 'Sem email'}</Text>
              </Box>
              <MenuDivider borderColor="whiteAlpha.100" />

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
                  <MenuDivider borderColor="whiteAlpha.100" />
                  <MenuItem
                    icon={<FiShield />}
                    fontSize="sm"
                    fontWeight="medium"
                    color="#0ea5e9"
                    onClick={() => navigate('/dashboard/admin')}
                  >
                    Painel Admin
                  </MenuItem>
                </>
              )}

              <MenuDivider borderColor="whiteAlpha.100" />
              <MenuItem
                icon={<FiLogOut />}
                fontSize="sm"
                color="red.400"
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
