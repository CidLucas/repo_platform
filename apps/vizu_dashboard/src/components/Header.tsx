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
import Logo from '../assets/logo.svg?react';
import { MenuDrawer } from './MenuDrawer';

export const Header = () => {
  const { toggleChat } = useChat();
  const navigate = useNavigate();
  const { isOpen: isMenuOpen, onOpen: onMenuOpen, onClose: onMenuClose } = useDisclosure();
  
  // TODO: Get user name from auth context
  const userName = "Fábio";
  const userInitials = userName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  
  // TODO: Check if user is admin from auth context
  const isAdmin = true;
  
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
            >
              <Text fontSize="xs" fontWeight="normal">{userInitials}</Text>
            </Avatar>
          </MenuButton>
          <MenuList shadow="lg" borderRadius="12px" py={2}>
            {/* User Info */}
            <Box px={4} py={2} mb={2}>
              <Text fontWeight="medium" fontSize="sm">{userName}</Text>
              <Text fontSize="xs" color="gray.500">fabio@vizu.ai</Text>
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
              onClick={() => {
                // TODO: Implement logout
                console.log('Logout');
              }}
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
