import { HStack, IconButton } from '@chakra-ui/react';
import { InfoOutlineIcon, ArrowUpDownIcon, SettingsIcon } from '@chakra-ui/icons';
import { NavLink } from 'react-router-dom';

export const FloatingMenu = () => {
  return (
    <HStack
      as="nav"
      position="fixed"
      bottom="2rem"
      left="50%"
      transform="translateX(-50%)"
      p={2}
      bg="gray.900"
      borderRadius="full"
      spacing={4}
      boxShadow="lg"
      zIndex="1001" // Added zIndex
    >
      <NavLink to="/dashboard" end>
        {({ isActive }) => (
          <IconButton
            aria-label="Home"
            icon={<InfoOutlineIcon />}
            variant="ghost"
            colorScheme={isActive ? "blue" : "whiteAlpha"}
          />
        )}
      </NavLink>
      <NavLink to="/dashboard/charts">
        {({ isActive }) => (
          <IconButton
            aria-label="Charts"
            icon={<ArrowUpDownIcon />}
            variant="ghost"
            colorScheme={isActive ? "blue" : "whiteAlpha"}
          />
        )}
      </NavLink>
      <NavLink to="/dashboard/settings">
        {({ isActive }) => (
          <IconButton
            aria-label="Settings"
            icon={<SettingsIcon />}
            variant="ghost"
            colorScheme={isActive ? "blue" : "whiteAlpha"}
          />
        )}
      </NavLink>
    </HStack>
  );
};
