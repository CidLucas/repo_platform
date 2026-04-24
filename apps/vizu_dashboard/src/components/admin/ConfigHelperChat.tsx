import {
    Box,
    VStack,
    HStack,
    Heading,
    Text,
    Textarea,
    Button,
    Icon,
    Spinner,
    useToast,
} from '@chakra-ui/react';
import { useState, useEffect, useRef } from 'react';
import { FiSend } from 'react-icons/fi';
import { MarkdownMessage } from '../MarkdownMessage';
import { streamConfigHelperChat } from '../../services/standaloneAgentService';

interface ChatMessage {
    id: string;
    content: string;
    sender: 'user' | 'assistant';
    timestamp: Date;
}

interface ConfigHelperChatProps {
    sessionId: string | null;
    accessToken: string | null | undefined;
    agentName: string;
}

export const ConfigHelperChat = ({ sessionId, accessToken, agentName }: ConfigHelperChatProps) => {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const toast = useToast();

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Initialize with greeting
    useEffect(() => {
        if (sessionId && messages.length === 0) {
            setMessages([
                {
                    id: '0',
                    content: `Olá! Sou o Assistente de Configuração da Blu. Vou ajudá-lo a configurar o agente **${agentName}** respondendo algumas perguntas simples sobre seu negócio e dados.`,
                    sender: 'assistant',
                    timestamp: new Date(),
                },
            ]);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [sessionId, agentName]);

    const handleSendMessage = async () => {
        if (!inputValue.trim() || !sessionId || !accessToken || isLoading) return;

        const userMessage: ChatMessage = {
            id: Date.now().toString(),
            content: inputValue.trim(),
            sender: 'user',
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInputValue('');
        setIsLoading(true);

        const assistantMessageId = `${Date.now() + 1}`;
        let assistantContent = '';

        try {
            // Stream config helper response
            for await (const event of streamConfigHelperChat(sessionId, userMessage.content, accessToken)) {
                if (event.event === 'token' && typeof event.data === 'string') {
                    assistantContent += event.data;

                    // Update or create assistant message
                    setMessages((prev) => {
                        const lastMsg = prev[prev.length - 1];
                        if (lastMsg?.sender === 'assistant' && lastMsg.id === assistantMessageId) {
                            return [
                                ...prev.slice(0, -1),
                                { ...lastMsg, content: assistantContent },
                            ];
                        } else {
                            return [
                                ...prev,
                                {
                                    id: assistantMessageId,
                                    content: assistantContent,
                                    sender: 'assistant',
                                    timestamp: new Date(),
                                },
                            ];
                        }
                    });
                } else if (event.event === 'tool_start') {
                    const toolEvent = event.data as { tool?: string; input?: unknown };
                    console.debug(`Tool started: ${toolEvent.tool}`, toolEvent.input);
                } else if (event.event === 'error') {
                    const errorEvent = event.data as { error?: string };
                    toast({
                        title: 'Erro',
                        description: errorEvent.error,
                        status: 'error',
                        duration: 4000,
                    });
                }
            }
        } catch (err) {
            const error = err instanceof Error ? err.message : 'Erro desconhecido';
            console.error('Config helper chat error:', err);

            toast({
                title: 'Erro ao processar resposta',
                description: error,
                status: 'error',
                duration: 4000,
            });

            // Add error message
            setMessages((prev) => [
                ...prev,
                {
                    id: `${Date.now()}-error`,
                    content: `Desculpe, ocorreu um erro: ${error}`,
                    sender: 'assistant',
                    timestamp: new Date(),
                },
            ]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    if (!sessionId) {
        return (
            <Box borderWidth="1px" borderColor="rgba(255,255,255,0.08)" borderRadius="lg" bg="#1a1b2e" p={6} textAlign="center">
                <Text color="whiteAlpha.600">
                    Selecione um agente e comece a configuração para iniciar a conversa
                </Text>
            </Box>
        );
    }

    return (
        <Box
            borderWidth="1px"
            borderColor="rgba(255,255,255,0.08)"
            borderRadius="2xl"
            bg="#1a1b2e"
            display="flex"
            flexDir="column"
            height="600px"
            overflow="hidden"
            boxShadow="0 20px 60px rgba(0,0,0,0.35)"
        >
            {/* Header */}
            <Box borderBottomWidth="1px" borderColor="rgba(255,255,255,0.08)" p={4} bgGradient="linear(to-r, #141620, #1a1d2e)">
                <Heading size="sm" color="white">Assistente de Configuração</Heading>
                <Text fontSize="xs" color="whiteAlpha.600">
                    Blu Config
                </Text>
            </Box>

            {/* Messages */}
            <VStack
                flex={1}
                overflowY="auto"
                align="stretch"
                spacing={4}
                p={4}
            >
                {messages.map((msg) => (
                    <HStack
                        key={msg.id}
                        align="flex-start"
                        justify={msg.sender === 'user' ? 'flex-end' : 'flex-start'}
                    >
                        <Box
                            maxW="70%"
                            bg={msg.sender === 'user' ? 'transparent' : '#14151f'}
                            bgGradient={msg.sender === 'user' ? 'linear(to-br, #ff6b35, #ff006e)' : undefined}
                            borderWidth={msg.sender === 'user' ? '0' : '1px'}
                            borderColor="rgba(255,255,255,0.08)"
                            color="white"
                            px={4}
                            py={3}
                            borderRadius="xl"
                            boxShadow={msg.sender === 'user' ? '0 8px 24px rgba(255,107,53,0.18)' : 'none'}
                        >
                            {msg.sender === 'user' ? (
                                <Text fontSize="sm">{msg.content}</Text>
                            ) : (
                                <MarkdownMessage content={msg.content} />
                            )}
                        </Box>
                    </HStack>
                ))}
                {isLoading && (
                    <HStack align="flex-start">
                        <Spinner size="sm" color="whiteAlpha.600" />
                        <Text fontSize="xs" color="whiteAlpha.600">
                            Processando...
                        </Text>
                    </HStack>
                )}
                <div ref={messagesEndRef} />
            </VStack>

            {/* Input */}
            <Box borderTopWidth="1px" borderColor="rgba(255,255,255,0.08)" p={4} bgGradient="linear(to-r, #141620, #1a1d2e)">
                <HStack spacing={2} align="stretch">
                    <Textarea
                        placeholder="Descreva suas informações, dados e contexto do negócio..."
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={isLoading}
                        minH="60px"
                        maxH="100px"
                        resize="none"
                        fontSize="sm"
                        rows={3}
                        bg="#14151f"
                        color="white"
                        borderColor="rgba(255,255,255,0.08)"
                        _placeholder={{ color: 'whiteAlpha.400' }}
                        _hover={{ borderColor: 'rgba(255,255,255,0.16)' }}
                        _focus={{ borderColor: '#ff6b35', boxShadow: '0 0 0 1px #ff6b35' }}
                    />
                    <Button
                        bgGradient="linear(to-r, #ff6b35, #ff006e)"
                        color="white"
                        _hover={{ opacity: 0.9 }}
                        onClick={handleSendMessage}
                        isDisabled={!inputValue.trim() || isLoading}
                        isLoading={isLoading}
                        leftIcon={<Icon as={FiSend} />}
                        height="auto"
                        minW="120px"
                        boxShadow="0 8px 24px rgba(255,107,53,0.22)"
                    >
                        Enviar
                    </Button>
                </HStack>
            </Box>
        </Box>
    );
};
