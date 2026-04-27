import {
  Box,
  Flex,
  HStack,
  VStack,
  Text,
  Spinner,
  Alert,
  AlertIcon,
  Textarea,
  Button,
  Badge,
  IconButton,
  useToast,
  Divider,
} from '@chakra-ui/react';
import { RepeatIcon } from '@chakra-ui/icons';
import { useEffect, useMemo, useState } from 'react';
import { MainLayout } from '../components/layouts/MainLayout';
import {
  listInboxThreads,
  listThreadMessages,
  draftInboxReply,
  sendInboxReply,
  type InboxThread,
  type InboxMessage,
} from '../services/analyticsService';

const formatTime = (iso: string | null): string => {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit',
      day: '2-digit',
      month: '2-digit',
    });
  } catch {
    return iso;
  }
};

const STATUS_COLORS: Record<string, string> = {
  draft: 'gray',
  pending_approval: 'yellow',
  approved: 'blue',
  sent: 'green',
  failed: 'red',
  received: 'purple',
};

function InboxPage() {
  const toast = useToast();
  const [threads, setThreads] = useState<InboxThread[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeContactId, setActiveContactId] = useState<string | null>(null);
  const [messages, setMessages] = useState<InboxMessage[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [draftText, setDraftText] = useState('');
  const [draftMessageId, setDraftMessageId] = useState<string | null>(null);
  const [drafting, setDrafting] = useState(false);
  const [sending, setSending] = useState(false);
  const [hint, setHint] = useState('');

  const activeThread = useMemo(
    () => threads.find((t) => t.contact_id === activeContactId) ?? null,
    [threads, activeContactId],
  );

  const refreshThreads = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listInboxThreads(50);
      setThreads(data);
      if (!activeContactId && data.length > 0) {
        setActiveContactId(data[0].contact_id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erro ao carregar inbox');
    } finally {
      setLoading(false);
    }
  };

  const refreshMessages = async (contactId: string) => {
    try {
      setMessagesLoading(true);
      const data = await listThreadMessages(contactId, 200);
      setMessages(data);
      setDraftMessageId(null);
      setDraftText('');
    } catch (e) {
      toast({
        status: 'error',
        title: 'Erro ao carregar mensagens',
        description: e instanceof Error ? e.message : String(e),
      });
    } finally {
      setMessagesLoading(false);
    }
  };

  useEffect(() => {
    void refreshThreads();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (activeContactId) void refreshMessages(activeContactId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeContactId]);

  const handleDraft = async () => {
    if (!activeContactId) return;
    try {
      setDrafting(true);
      const result = await draftInboxReply(activeContactId, hint || undefined);
      setDraftText(result.draft_text);
      setDraftMessageId(result.message_id);
      await refreshMessages(activeContactId);
    } catch (e) {
      toast({
        status: 'error',
        title: 'Falha ao gerar rascunho',
        description: e instanceof Error ? e.message : String(e),
      });
    } finally {
      setDrafting(false);
    }
  };

  const handleSend = async () => {
    if (!draftMessageId) {
      toast({ status: 'warning', title: 'Gere um rascunho primeiro.' });
      return;
    }
    try {
      setSending(true);
      const result = await sendInboxReply(
        draftMessageId,
        draftText.trim() || undefined,
      );
      if (result.status === 'pending_approval') {
        toast({
          status: 'info',
          title: 'Aprovação pendente',
          description: 'Mensagem enviada para o painel de aprovações.',
        });
      } else {
        toast({ status: 'success', title: 'Mensagem enviada.' });
      }
      setDraftText('');
      setDraftMessageId(null);
      setHint('');
      if (activeContactId) await refreshMessages(activeContactId);
      await refreshThreads();
    } catch (e) {
      toast({
        status: 'error',
        title: 'Falha ao enviar',
        description: e instanceof Error ? e.message : String(e),
      });
    } finally {
      setSending(false);
    }
  };

  return (
    <MainLayout>
      <Flex direction="column" h="calc(100vh - 80px)" p={4} gap={3}>
        <HStack>
          <Text fontSize="2xl" fontWeight="bold">
            Inbox
          </Text>
          <IconButton
            aria-label="Atualizar"
            icon={<RepeatIcon />}
            size="sm"
            onClick={refreshThreads}
            isLoading={loading}
          />
        </HStack>
        {error && (
          <Alert status="error">
            <AlertIcon />
            {error}
          </Alert>
        )}
        <Flex flex={1} gap={3} minH={0}>
          {/* Thread list */}
          <Box
            w="320px"
            borderWidth="1px"
            borderRadius="md"
            overflowY="auto"
            bg="white"
          >
            {loading && (
              <Flex justify="center" p={6}>
                <Spinner />
              </Flex>
            )}
            {!loading && threads.length === 0 && (
              <Text p={4} color="gray.500" fontSize="sm">
                Nenhuma conversa ainda.
              </Text>
            )}
            {threads.map((t) => {
              const isActive = t.contact_id === activeContactId;
              return (
                <Box
                  key={t.contact_id}
                  p={3}
                  cursor="pointer"
                  bg={isActive ? 'blue.50' : 'transparent'}
                  borderBottomWidth="1px"
                  onClick={() => setActiveContactId(t.contact_id)}
                  _hover={{ bg: isActive ? 'blue.50' : 'gray.50' }}
                >
                  <HStack justify="space-between">
                    <Text fontWeight="semibold" noOfLines={1}>
                      {t.display_name || t.external_id}
                    </Text>
                    {t.unread_count > 0 && (
                      <Badge colorScheme="red">{t.unread_count}</Badge>
                    )}
                  </HStack>
                  <Text fontSize="xs" color="gray.500" noOfLines={1}>
                    {t.last_message_preview ?? '—'}
                  </Text>
                  <HStack mt={1} spacing={2}>
                    <Badge colorScheme="purple" fontSize="0.65em">
                      {t.channel}
                    </Badge>
                    <Text fontSize="xs" color="gray.400">
                      {formatTime(t.last_message_at)}
                    </Text>
                  </HStack>
                </Box>
              );
            })}
          </Box>

          {/* Conversation */}
          <Flex
            flex={1}
            direction="column"
            borderWidth="1px"
            borderRadius="md"
            bg="white"
            minH={0}
          >
            {!activeThread ? (
              <Flex flex={1} justify="center" align="center">
                <Text color="gray.500">Selecione uma conversa</Text>
              </Flex>
            ) : (
              <>
                <Box p={3} borderBottomWidth="1px">
                  <Text fontWeight="bold">
                    {activeThread.display_name || activeThread.external_id}
                  </Text>
                  <Text fontSize="xs" color="gray.500">
                    {activeThread.channel} · {activeThread.message_count} mensagens
                  </Text>
                </Box>

                <VStack flex={1} overflowY="auto" p={3} spacing={2} align="stretch">
                  {messagesLoading && (
                    <Flex justify="center">
                      <Spinner size="sm" />
                    </Flex>
                  )}
                  {messages.map((m) => {
                    const inbound = m.direction === 'inbound';
                    return (
                      <Box
                        key={m.id}
                        alignSelf={inbound ? 'flex-start' : 'flex-end'}
                        maxW="75%"
                        bg={inbound ? 'gray.100' : 'blue.500'}
                        color={inbound ? 'gray.800' : 'white'}
                        px={3}
                        py={2}
                        borderRadius="md"
                      >
                        <Text whiteSpace="pre-wrap" fontSize="sm">
                          {m.body}
                        </Text>
                        <HStack mt={1} spacing={2}>
                          <Badge
                            colorScheme={STATUS_COLORS[m.status] ?? 'gray'}
                            fontSize="0.6em"
                          >
                            {m.status}
                          </Badge>
                          <Text fontSize="0.65em" opacity={0.8}>
                            {formatTime(m.created_at)}
                          </Text>
                        </HStack>
                      </Box>
                    );
                  })}
                </VStack>

                <Divider />

                <Box p={3}>
                  <VStack align="stretch" spacing={2}>
                    <Textarea
                      placeholder="Instruções opcionais para a IA (ex: ofereça desconto)"
                      size="sm"
                      rows={1}
                      value={hint}
                      onChange={(e) => setHint(e.target.value)}
                    />
                    <Textarea
                      placeholder="Rascunho da resposta…"
                      size="sm"
                      rows={3}
                      value={draftText}
                      onChange={(e) => setDraftText(e.target.value)}
                    />
                    <HStack justify="flex-end">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={handleDraft}
                        isLoading={drafting}
                      >
                        Gerar rascunho
                      </Button>
                      <Button
                        size="sm"
                        colorScheme="blue"
                        onClick={handleSend}
                        isLoading={sending}
                        isDisabled={!draftMessageId}
                      >
                        Enviar
                      </Button>
                    </HStack>
                  </VStack>
                </Box>
              </>
            )}
          </Flex>
        </Flex>
      </Flex>
    </MainLayout>
  );
}

export default InboxPage;
