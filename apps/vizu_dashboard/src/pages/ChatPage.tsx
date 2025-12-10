import {
  Box,
  Flex,
  Text,
  IconButton,
  HStack,
  VStack,
  Button,
  Textarea,
} from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';
import { useState, useRef, useEffect } from 'react';
import { ArrowForwardIcon, AttachmentIcon, AddIcon, ChatIcon } from '@chakra-ui/icons';

interface Message {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
}

interface SuggestionChip {
  label: string;
  color: string;
  icon?: boolean;
}

const suggestionChips: SuggestionChip[] = [
  { label: 'Personalize seus dados', color: '#92DAFF' },
  { label: 'Personalize seu painel', color: '#FFF856', icon: true },
  { label: 'Abra um pedido', color: '#F9BBCB' },
];

function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // TODO: Get user name from auth context
  const userName = 'Fábio';

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue.trim(),
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    // TODO: Integrate with backend chat API
    // Simulating a response for now
    setTimeout(() => {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: 'Esta é uma resposta simulada. A integração com o backend será implementada em breve.',
        sender: 'assistant',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setIsLoading(false);
    }, 1000);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleChipClick = (label: string) => {
    setInputValue(label);
    textareaRef.current?.focus();
  };

  const hasMessages = messages.length > 0;

  return (
    <MainLayout>
      <Flex
        direction="column"
        flex="1"
        bg="#F6F6F6"
        height="calc(100vh - 61px)" // Subtract header height
        position="relative"
      >
        {/* Chat Container */}
        <Flex
          direction="column"
          maxW="750px"
          w="100%"
          mx="auto"
          flex="1"
          bg="white"
          borderRadius="0"
          overflow="hidden"
        >
          {/* Chat Header */}
          <Flex
            align="center"
            justify="space-between"
            px={6}
            py={4}
            borderBottom="1px solid"
            borderColor="gray.100"
          >
            <HStack spacing={2}>
              <Text fontWeight="500" fontSize="18px" fontFamily="'Noto Sans', sans-serif">
                Novo chat vizu
              </Text>
              <ChatIcon w={5} h={5} color="gray.500" />
            </HStack>
            <IconButton
              aria-label="Novo chat"
              icon={<AddIcon />}
              variant="ghost"
              size="sm"
              onClick={() => setMessages([])}
            />
          </Flex>

          {/* Messages Area */}
          <Flex
            direction="column"
            flex="1"
            overflowY="auto"
            px={6}
            py={4}
          >
            {!hasMessages ? (
              /* Welcome State */
              <VStack align="flex-start" spacing={6} mt={4}>
                <Text
                  fontSize="34px"
                  fontWeight="400"
                  fontFamily="'Noto Sans', sans-serif"
                  lineHeight="36px"
                  letterSpacing="0.35px"
                >
                  Olá {userName}, por{' '}
                  <br />
                  onde quer começar?
                </Text>

                {/* Suggestion Chips */}
                <VStack align="flex-start" spacing={3}>
                  {suggestionChips.map((chip) => (
                    <Button
                      key={chip.label}
                      bg={chip.color}
                      color="black"
                      borderRadius="full"
                      height="36px"
                      px={4}
                      fontWeight="400"
                      fontSize="14px"
                      fontFamily="'Noto Sans', sans-serif"
                      _hover={{ opacity: 0.9 }}
                      onClick={() => handleChipClick(chip.label)}
                      leftIcon={chip.icon ? <AddIcon w={3} h={3} /> : undefined}
                    >
                      {chip.label}
                    </Button>
                  ))}
                </VStack>
              </VStack>
            ) : (
              /* Messages List */
              <VStack align="stretch" spacing={4} w="100%">
                {messages.map((message) => (
                  <Flex
                    key={message.id}
                    justify={message.sender === 'user' ? 'flex-end' : 'flex-start'}
                  >
                    <Box
                      maxW="80%"
                      bg={message.sender === 'user' ? 'black' : 'gray.100'}
                      color={message.sender === 'user' ? 'white' : 'black'}
                      px={4}
                      py={3}
                      borderRadius="lg"
                    >
                      <Text fontSize="16px" fontFamily="'Noto Sans', sans-serif">
                        {message.content}
                      </Text>
                    </Box>
                  </Flex>
                ))}
                {isLoading && (
                  <Flex justify="flex-start">
                    <Box bg="gray.100" px={4} py={3} borderRadius="lg">
                      <Text fontSize="16px" color="gray.500">
                        Digitando...
                      </Text>
                    </Box>
                  </Flex>
                )}
                <div ref={messagesEndRef} />
              </VStack>
            )}
          </Flex>

          {/* Input Area */}
          <Box
            bg="#DEDEDE"
            borderRadius="22px"
            mx={4}
            mb={4}
            p={4}
          >
            {/* Context Button */}
            <HStack mb={3}>
              <Button
                bg="black"
                color="white"
                borderRadius="full"
                height="36px"
                px={4}
                fontWeight="400"
                fontSize="14px"
                fontFamily="'Noto Sans', sans-serif"
                leftIcon={<AddIcon w={3} h={3} />}
                _hover={{ bg: 'gray.800' }}
              >
                Adicione um contexto
              </Button>
            </HStack>

            {/* Text Input */}
            <Textarea
              ref={textareaRef}
              placeholder="Pergunte, pesquise ou faça qualquer coisa..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyPress}
              bg="transparent"
              border="none"
              resize="none"
              minH="60px"
              fontSize="16px"
              fontFamily="'Noto Sans', sans-serif"
              _placeholder={{ color: '#7D7D7D' }}
              _focus={{ border: 'none', boxShadow: 'none' }}
            />

            {/* Action Buttons */}
            <Flex justify="space-between" align="center" mt={3}>
              <HStack spacing={2}>
                <Button
                  variant="ghost"
                  size="sm"
                  leftIcon={<AttachmentIcon />}
                  color="blackAlpha.600"
                  fontWeight="400"
                  fontSize="16px"
                  fontFamily="'Noto Sans', sans-serif"
                >
                  Anexar
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  leftIcon={<AddIcon />}
                  color="blackAlpha.600"
                  fontWeight="400"
                  fontSize="16px"
                  fontFamily="'Noto Sans', sans-serif"
                >
                  Conectar bancos
                </Button>
              </HStack>

              {/* Send Button */}
              <IconButton
                aria-label="Enviar mensagem"
                icon={<ArrowForwardIcon />}
                bg="black"
                color="white"
                borderRadius="full"
                size="md"
                w="40px"
                h="40px"
                isDisabled={!inputValue.trim() || isLoading}
                onClick={handleSendMessage}
                _hover={{ bg: 'gray.800' }}
              />
            </Flex>
          </Box>
        </Flex>
      </Flex>
    </MainLayout>
  );
}

export default ChatPage;
