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
import { streamConfigHelperChat, type StreamEvent } from '../../services/standaloneAgentService';

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
                    content: `Olá! Sou o Assistente de Configuração do Vizu. Vou ajudá-lo a configurar o agente **${agentName}** respondendo algumas perguntas simples sobre seu negócio e dados.`,
                    sender: 'assistant',
                    timestamp: new Date(),
                },
            ]);
        }
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
                    const toolEvent = event.data as any;
                    console.debug(`Tool started: ${toolEvent.tool}`, toolEvent.input);
                } else if (event.event === 'error') {
                    const errorEvent = event.data as any;
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
            <Box borderWidth="1px" borderColor="gray.200" borderRadius="lg" p={6} textAlign="center">
                <Text color="gray.600">
                    Selecione um agente e comece a configuração para iniciar a conversa
                </Text>
            </Box>
        );
    }

    return (
        <Box
            borderWidth="1px"
            borderColor="gray.200"
            borderRadius="lg"
            display="flex"
            flexDir="column"
            height="600px"
        >
            {/* Header */}
            <Box borderBottomWidth="1px" borderColor="gray.200" p={4}>
                <Heading size="sm">Assistente de Configuração</Heading>
                <Text fontSize="xs" color="gray.600">
                    Vizu Config
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
                            bg={msg.sender === 'user' ? 'black' : 'gray.100'}
                            color={msg.sender === 'user' ? 'white' : 'black'}
                            px={4}
                            py={3}
                            borderRadius="lg"
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
                        <Spinner size="sm" color="gray.600" />
                        <Text fontSize="xs" color="gray.600">
                            Processando...
                        </Text>
                    </HStack>
                )}
                <div ref={messagesEndRef} />
            </VStack>

            {/* Input */}
            <Box borderTopWidth="1px" borderColor="gray.200" p={4}>
                <HStack spacing={2}>
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
                    />
                    <Button
                        colorScheme="black"
                        onClick={handleSendMessage}
                        isDisabled={!inputValue.trim() || isLoading}
                        isLoading={isLoading}
                        leftIcon={<Icon as={FiSend} />}
                        height="100%"
                    >
                        Enviar
                    </Button>
                </HStack>
            </Box>
        </Box>
    );
};
