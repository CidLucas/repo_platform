import { Avatar, Flex, Spacer, IconButton, HStack, Text } from '@chakra-ui/react';
import { BellIcon, ChatIcon, SettingsIcon } from '@chakra-ui/icons';
import { Link } from 'react-router-dom';
import { useChat } from '../contexts/ChatContext';
import Logo from '../assets/logo.svg?react';

export const Header = () => {
  const { toggleChat } = useChat();
  
  // TODO: Get user name from auth context
  const userName = "Fábio";
  const userInitials = userName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  
  return (
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
        <IconButton
          as={Link}
          to="/dashboard/settings"
          aria-label="Settings"
          icon={<SettingsIcon />}
          variant="ghost"
          colorScheme="gray"
          borderRadius="full"
          size="md"
        />
        
        {/* User Avatar */}
        <Avatar 
          name={userName} 
          bg="black" 
          color="white"
          size="sm"
          fontSize="xs"
        >
          <Text fontSize="xs" fontWeight="normal">{userInitials}</Text>
        </Avatar>
      </HStack>
    </Flex>
  );
};
