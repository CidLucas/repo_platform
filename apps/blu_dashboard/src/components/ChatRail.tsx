import {
  Box,
  Button,
  Flex,
  HStack,
  Icon,
  IconButton,
  Text,
  VStack,
  useMediaQuery,
} from '@chakra-ui/react';
import { ChatIcon } from '@chakra-ui/icons';
import { FiMaximize2, FiEyeOff, FiEye } from 'react-icons/fi';
import { useEffect, useMemo, useState } from 'react';
import { useChat } from '../contexts/ChatContext';
import { useTracking } from '../hooks/useTracking';
import {
  CHAT_RAIL_FOCUS_MODE_EVENT,
  getChatRailFocusMode,
  setChatRailFocusMode,
} from './chatRailFocusMode';

export const ChatRail = () => {
  const { openChat, isChatOpen } = useChat();
  const { track } = useTracking();
  const [isDesktopWide] = useMediaQuery('(min-width: 1440px)');
  const [isDesktop] = useMediaQuery('(min-width: 1280px)');
  const [focusMode, setFocusMode] = useState<boolean>(getChatRailFocusMode);

  const suggestionChips = useMemo(
    () => ['Vendas dessa semana', 'Ticket médio', 'Top produtos'],
    []
  );

  const toggleFocusMode = () => {
    const next = !focusMode;
    setFocusMode(next);
    setChatRailFocusMode(next);
  };

  useEffect(() => {
    const onModeChanged = (event: Event) => {
      const next = (event as CustomEvent<{ value?: boolean }>).detail?.value;
      setFocusMode(typeof next === 'boolean' ? next : getChatRailFocusMode());
    };

    window.addEventListener(CHAT_RAIL_FOCUS_MODE_EVENT, onModeChanged);
    return () => window.removeEventListener(CHAT_RAIL_FOCUS_MODE_EVENT, onModeChanged);
  }, []);

  if (focusMode || !isDesktop || isChatOpen) {
    return null;
  }

  if (isDesktopWide) {
    return (
      <Box
        position="fixed"
        top="64px"
        right={0}
        width="320px"
        height="calc(100vh - 64px)"
        bg="#101428"
        borderLeft="1px solid"
        borderColor="rgba(255,255,255,0.08)"
        zIndex={19}
        px={4}
        py={5}
      >
        <Flex justify="space-between" align="center" mb={4}>
          <HStack spacing={2}>
            <Icon as={ChatIcon} color="#60a5fa" />
            <Text color="white" fontSize="sm" fontWeight="semibold">
              Chat Companion
            </Text>
          </HStack>
          <IconButton
            aria-label="Ativar modo foco"
            icon={<FiEyeOff size={14} />}
            size="sm"
            variant="ghost"
            color="whiteAlpha.700"
            _hover={{ bg: 'whiteAlpha.200', color: 'white' }}
            onClick={toggleFocusMode}
          />
        </Flex>

        <Text color="whiteAlpha.700" fontSize="xs" mb={4}>
          Pergunte ao Blu sobre seus dados e próximas ações.
        </Text>

        <VStack align="stretch" spacing={2}>
          {suggestionChips.map((chip) => (
            <Button
              key={chip}
              variant="outline"
              borderColor="whiteAlpha.300"
              color="white"
              fontSize="xs"
              justifyContent="flex-start"
              onClick={() => { track('dashboard.chat_rail.opened', { source: 'chip', chip }); openChat(chip); }}
              _hover={{ bg: 'whiteAlpha.200' }}
            >
              {chip}
            </Button>
          ))}
        </VStack>

        <Button
          mt={5}
          w="full"
          leftIcon={<FiMaximize2 />}
          bgGradient="linear(to-r, #2563eb, #1d4ed8)"
          color="white"
          _hover={{ bgGradient: 'linear(to-r, #1d4ed8, #1e40af)' }}
          onClick={() => { track('dashboard.chat_rail.opened', { source: 'expand_button' }); openChat(); }}
        >
          Expandir
        </Button>
      </Box>
    );
  }

  return (
    <Box
      position="fixed"
      top="120px"
      right={4}
      width="64px"
      borderRadius="18px"
      bg="#101428"
      border="1px solid"
      borderColor="rgba(255,255,255,0.12)"
      zIndex={19}
      py={3}
      px={2}
    >
      <VStack spacing={3}>
        <IconButton
          aria-label="Abrir chat"
          icon={<ChatIcon />}
          color="white"
          bg="whiteAlpha.200"
          _hover={{ bg: 'whiteAlpha.300' }}
          borderRadius="full"
          onClick={() => openChat()}
        />
        <IconButton
          aria-label="Ativar modo foco"
          icon={<FiEyeOff size={14} />}
          size="sm"
          variant="ghost"
          color="whiteAlpha.700"
          _hover={{ bg: 'whiteAlpha.200', color: 'white' }}
          onClick={toggleFocusMode}
        />
      </VStack>
    </Box>
  );
};

export const ChatRailFocusToggle = () => {
  const [focusMode, setFocusMode] = useState<boolean>(getChatRailFocusMode);

  const toggle = () => {
    const next = !focusMode;
    setFocusMode(next);
    setChatRailFocusMode(next);
  };

  return (
    <IconButton
      aria-label={focusMode ? 'Desativar modo foco do chat' : 'Ativar modo foco do chat'}
      icon={focusMode ? <FiEye size={14} /> : <FiEyeOff size={14} />}
      size="sm"
      variant="ghost"
      color="whiteAlpha.700"
      _hover={{ bg: 'whiteAlpha.200', color: 'white' }}
      onClick={toggle}
    />
  );
};
