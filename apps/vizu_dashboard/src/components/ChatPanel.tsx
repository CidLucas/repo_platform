import {
  Box,
  Flex,
  Text,
  IconButton,
  HStack,
  VStack,
  Button,
  Textarea,
  Slide,
  Portal,
  useToast,
  Tag,
  TagLabel,
  TagCloseButton,
  Spinner,
} from '@chakra-ui/react';
import { useState, useRef, useEffect, useContext, useCallback } from 'react';
import { ArrowForwardIcon, AttachmentIcon, AddIcon, ChatIcon, CloseIcon } from '@chakra-ui/icons';
import { AuthContext } from '../contexts/AuthContext';
import { SimpleDataTable, type StructuredData } from './SimpleDataTable';
import { MarkdownMessage } from './MarkdownMessage';
import { sendChatMessageStream, type StreamDoneData } from '../services/chatService';
import { uploadFile, getAcceptedExtensions } from '../services/knowledgeBaseService';

interface Message {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
  structuredData?: StructuredData;
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

interface ChatPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ChatPanel = ({ isOpen, onClose }: ChatPanelProps) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<{ name: string; documentId: string }[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const auth = useContext(AuthContext);
  const toast = useToast();

  // Unique session ID per conversation — resets on "New Chat" or fresh page open
  const [sessionId, setSessionId] = useState(
    () => `${auth?.user?.id || 'anon'}:${Date.now()}`
  );

  // Get user name from auth context - fallback to first part of email if no display name
  const userName = auth?.user?.user_metadata?.full_name ||
    auth?.user?.email?.split('@')[0] ||
    'Usuário';

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => textareaRef.current?.focus(), 300);
    }
  }, [isOpen]);

  // Handle file upload from the "Anexar" button
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    const clientId = auth?.clientId;
    if (!clientId) {
      toast({ title: 'Erro', description: 'Usuário não autenticado.', status: 'error', duration: 3000 });
      return;
    }
    setUploadingFile(true);
    try {
      for (const file of Array.from(files)) {
        const documentId = await uploadFile(file, clientId, false, 'chat');
        setAttachedFiles((prev) => [...prev, { name: file.name, documentId }]);
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            content: `📎 Arquivo "${file.name}" enviado e processado para contexto.`,
            sender: 'user',
            timestamp: new Date(),
          },
        ]);
      }
      toast({ title: 'Upload concluído', status: 'success', duration: 2000 });
    } catch (err) {
      console.error('File upload error:', err);
      toast({
        title: 'Erro no upload',
        description: err instanceof Error ? err.message : 'Erro desconhecido',
        status: 'error',
        duration: 4000,
      });
    } finally {
      setUploadingFile(false);
      e.target.value = ''; // reset input
    }
  };

  // Handle export to Google Sheets
  const handleExportToSheets = async (data: StructuredData) => {
    toast({
      title: 'Exportando...',
      description: 'Preparando dados para exportar ao Google Sheets',
      status: 'info',
      duration: 2000,
    });

    // TODO: Integrate with Google Sheets export via agent
    // For now, just show a message to the user
    setInputValue(`Exportar os dados "${data.title || 'da consulta'}" para o Google Sheets`);
    textareaRef.current?.focus();
  };

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

    // Create placeholder message for streaming response
    const assistantMessageId = Date.now().toString() + '-assistant';
    let streamedContent = '';

    setMessages((prev) => [
      ...prev,
      {
        id: assistantMessageId,
        content: '',
        sender: 'assistant',
        timestamp: new Date(),
      },
    ]);

    // Stream response from atendente_core
    const token = auth?.session?.access_token;

    // Include attached document IDs in context
    const attachedDocumentIds = attachedFiles.map((f) => f.documentId);

    await sendChatMessageStream(
      {
        message: userMessage.content,
        session_id: sessionId,
        ...(attachedDocumentIds.length > 0 && {
          context: { attached_document_ids: attachedDocumentIds },
        }),
      },
      {
        onToken: (token: string) => {
          streamedContent += token;
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: streamedContent }
                : msg
            )
          );
        },
        onToolStart: (tool) => {
          // Show tool activity indicator
          const toolLabel = tool.name === 'execute_sql' ? 'Consultando banco de dados...' :
            tool.name === 'executar_rag_cliente' ? 'Pesquisando na base de conhecimento...' :
              `Executando ${tool.name}...`;
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: `_${toolLabel}_\n\n${streamedContent}` }
                : msg
            )
          );
        },
        onToolEnd: () => {
          // Remove tool indicator, keep just streamed content
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: streamedContent }
                : msg
            )
          );
        },
        onComplete: (data: StreamDoneData) => {
          // Final update with structured data if present
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? {
                  ...msg,
                  content: data.response || streamedContent || 'Sem resposta do atendente.',
                  structuredData: data.structured_data,
                }
                : msg
            )
          );
          setIsLoading(false);
        },
        onError: (error: Error) => {
          console.error('Stream error:', error);
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: 'Erro ao se comunicar com o atendente. Tente novamente.' }
                : msg
            )
          );
          setIsLoading(false);
        },
      },
      token
    );

    // Fallback: ensure loading is false even if callbacks don't fire
    setIsLoading(false);
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

  const handleNewChat = useCallback(() => {
    setMessages([]);
    setInputValue('');
    setAttachedFiles([]);
    setSessionId(`${auth?.user?.id || 'anon'}:${Date.now()}`);
  }, [auth?.user?.id]);

  const hasMessages = messages.length > 0;

  return (
    <Portal>
      {/* Backdrop with blur effect - iOS style */}
      {isOpen && (
        <Box
          position="fixed"
          top="0"
          left="0"
          right="0"
          bottom="0"
          bg="rgba(0, 0, 0, 0.2)"
          backdropFilter="blur(8px)"
          sx={{ WebkitBackdropFilter: 'blur(8px)' }}
          zIndex={9998}
          onClick={onClose}
          transition="opacity 0.3s ease"
        />
      )}

      {/* Chat Panel - Sliding from right */}
      <Slide direction="right" in={isOpen} style={{ zIndex: 9999 }}>
        <Box
          position="fixed"
          top="0"
          right="0"
          width={{ base: '100%', md: '50%' }}
          maxW="750px"
          height="100vh"
          bg="rgba(255, 255, 255, 0.98)"
          backdropFilter="blur(20px)"
          sx={{ WebkitBackdropFilter: 'blur(20px)' }}
          borderLeft="1px solid"
          borderColor="rgba(200, 200, 200, 0.5)"
          boxShadow="-10px 0 40px rgba(0, 0, 0, 0.15)"
          display="flex"
          flexDirection="column"
        >
          {/* Glass effect overlay */}
          <Box
            position="absolute"
            top="0"
            left="0"
            right="0"
            bottom="0"
            bg="linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%)"
            pointerEvents="none"
            zIndex="0"
          />

          {/* Chat Header */}
          <Flex
            align="center"
            justify="space-between"
            px={6}
            py={4}
            borderBottom="1px solid"
            borderColor="rgba(0, 0, 0, 0.08)"
            bg="rgba(255, 255, 255, 0.5)"
            position="relative"
            zIndex="1"
          >
            <HStack spacing={2}>
              <Text fontWeight="500" fontSize="18px" fontFamily="'Noto Sans', sans-serif">
                Novo chat vizu
              </Text>
              <ChatIcon w={5} h={5} color="gray.500" />
            </HStack>
            <HStack spacing={2}>
              <IconButton
                aria-label="Novo chat"
                icon={<AddIcon />}
                variant="ghost"
                size="sm"
                onClick={handleNewChat}
              />
              <IconButton
                aria-label="Fechar chat"
                icon={<CloseIcon />}
                variant="ghost"
                size="sm"
                onClick={onClose}
              />
            </HStack>
          </Flex>

          {/* Messages Area */}
          <Flex
            direction="column"
            flex="1"
            overflowY="auto"
            px={6}
            py={4}
            position="relative"
            zIndex="1"
          >
            {!hasMessages ? (
              /* Welcome State */
              <VStack align="flex-start" spacing={6} mt={4}>
                <Text
                  fontSize={{ base: '28px', md: '34px' }}
                  fontWeight="400"
                  fontFamily="'Noto Sans', sans-serif"
                  lineHeight="1.1"
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
                      _hover={{ opacity: 0.9, transform: 'scale(1.02)' }}
                      transition="all 0.2s ease"
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
                    w="100%"
                  >
                    <Box
                      maxW={message.structuredData ? '100%' : '85%'}
                      w={message.structuredData ? '100%' : 'auto'}
                    >
                      {/* Text content */}
                      {message.content && (
                        <Box
                          bg={message.sender === 'user' ? 'black' : 'rgba(0, 0, 0, 0.06)'}
                          color={message.sender === 'user' ? 'white' : 'black'}
                          px={4}
                          py={3}
                          borderRadius="18px"
                          boxShadow={message.sender === 'user' ? '0 2px 8px rgba(0,0,0,0.15)' : 'none'}
                          mb={message.structuredData ? 3 : 0}
                        >
                          <MarkdownMessage
                            content={message.content}
                            isUser={message.sender === 'user'}
                          />
                        </Box>
                      )}

                      {/* Structured data table */}
                      {message.structuredData && (
                        <SimpleDataTable
                          data={message.structuredData}
                          onExportToSheets={() => handleExportToSheets(message.structuredData!)}
                          maxHeight="350px"
                        />
                      )}
                    </Box>
                  </Flex>
                ))}
                {isLoading && (
                  <Flex justify="flex-start">
                    <Box bg="rgba(0, 0, 0, 0.06)" px={4} py={3} borderRadius="18px">
                      <Text fontSize="15px" color="gray.500">
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
            bg="rgba(222, 222, 222, 0.8)"
            backdropFilter="blur(10px)"
            borderRadius="22px"
            mx={4}
            mb={4}
            p={4}
            position="relative"
            zIndex="1"
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

            {/* Attached files chips */}
            {attachedFiles.length > 0 && (
              <HStack spacing={2} mb={3} flexWrap="wrap">
                {attachedFiles.map((f) => (
                  <Tag
                    key={f.documentId}
                    size="sm"
                    colorScheme="blue"
                    borderRadius="full"
                    variant="subtle"
                  >
                    <TagLabel>📎 {f.name}</TagLabel>
                    <TagCloseButton
                      onClick={() =>
                        setAttachedFiles((prev) =>
                          prev.filter((af) => af.documentId !== f.documentId)
                        )
                      }
                    />
                  </Tag>
                ))}
              </HStack>
            )}

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
                  leftIcon={uploadingFile ? <Spinner size="xs" /> : <AttachmentIcon />}
                  color="blackAlpha.600"
                  fontWeight="400"
                  fontSize="16px"
                  fontFamily="'Noto Sans', sans-serif"
                  _hover={{ bg: 'rgba(0,0,0,0.05)' }}
                  onClick={() => fileInputRef.current?.click()}
                  isDisabled={uploadingFile}
                >
                  {uploadingFile ? 'Enviando...' : 'Anexar'}
                </Button>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  accept={getAcceptedExtensions()}
                  multiple
                  style={{ display: 'none' }}
                />
                <Button
                  variant="ghost"
                  size="sm"
                  leftIcon={<AddIcon />}
                  color="blackAlpha.600"
                  fontWeight="400"
                  fontSize="16px"
                  fontFamily="'Noto Sans', sans-serif"
                  _hover={{ bg: 'rgba(0,0,0,0.05)' }}
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
                _hover={{ bg: 'gray.800', transform: 'scale(1.05)' }}
                _disabled={{ opacity: 0.5, cursor: 'not-allowed' }}
                transition="all 0.2s ease"
              />
            </Flex>
          </Box>
        </Box>
      </Slide>
    </Portal>
  );
};
