import { Avatar, Flex, Spacer, IconButton } from '@chakra-ui/react';
import { HamburgerIcon } from '@chakra-ui/icons';
import Logo from '../assets/logo.svg?react'; // Import the SVG as a React component

export const Header = () => {
  return (
    <Flex as="header" py={2} px={4} align="center" width="100%" bg="white" boxShadow="sm"> {/* Updated padding */}
      <Logo style={{ height: '13.0657px', width: '36.8166px', marginRight: '16px' }} /> {/* Updated Logo size */}
      <Spacer />
      <IconButton
        aria-label="Menu"
        icon={<HamburgerIcon />}
        variant="ghost"
        colorScheme="gray"
        mr={4}
      />
      <Avatar name="Fábio" bg="blue.500" />
    </Flex>
  );
};
