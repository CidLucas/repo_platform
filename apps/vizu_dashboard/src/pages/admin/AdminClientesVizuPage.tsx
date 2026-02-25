import { useState, useEffect } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Button,
  Input,
  Textarea,
  Select,
  SimpleGrid,
  useToast,
  Spinner,
  Icon,
  Badge,
  IconButton,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  useDisclosure,
  FormControl,
  FormLabel,
  FormHelperText,
  Checkbox,
  CheckboxGroup,
  Wrap,
  WrapItem,
  Alert,
  AlertIcon,
  Divider,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
} from '@chakra-ui/react';
import { AdminLayout } from '../../components/layouts/AdminLayout';
import {
  FiPlus,
  FiEdit2,
  FiTrash2,
  FiRefreshCw,
  FiUsers,
  FiTool,
  FiShield,
} from 'react-icons/fi';
import {
  listClients,
  createClient,
  updateClient,
  deleteClient,
  getAllTools,
  ClienteVizu,
  ClienteVizuCreate,
  ClienteVizuUpdate,
  ToolMetadata,
  TIERS,
  TierType,
} from '../../services/adminService';

// Empty client form state
const emptyClientForm: ClienteVizuCreate = {
  nome_empresa: '',
  tipo_cliente: 'standard',
  tier: 'BASIC',
  prompt_base: '',
  enabled_tools: [],
  collection_rag: '',
  external_user_id: '',
};

function AdminClientesVizuPage() {
  const toast = useToast();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const {
    isOpen: isDeleteOpen,
    onOpen: onDeleteOpen,
    onClose: onDeleteClose,
  } = useDisclosure();

  // State
  const [clients, setClients] = useState<ClienteVizu[]>([]);
  const [allTools, setAllTools] = useState<ToolMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editingClient, setEditingClient] = useState<ClienteVizu | null>(null);
  const [deletingClient, setDeletingClient] = useState<ClienteVizu | null>(null);
  const [formData, setFormData] = useState<ClienteVizuCreate>(emptyClientForm);
  const [error, setError] = useState<string | null>(null);

  // Load data on mount
  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- loadData only runs on mount
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [clientsRes, toolsRes] = await Promise.all([
        listClients(),
        getAllTools(),
      ]);
      setClients(clientsRes.clients);
      setAllTools(toolsRes.tools);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load data';
      setError(message);
      toast({
        title: 'Erro ao carregar dados',
        description: message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setLoading(false);
    }
  };

  // Filter tools by tier
  const getToolsForTier = (tier: string): ToolMetadata[] => {
    const tierOrder: Record<string, number> = {
      FREE: 0,
      BASIC: 1,
      SME: 2,
      PREMIUM: 3,
      ENTERPRISE: 4,
      ADMIN: 99,
    };
    const clientTierOrder = tierOrder[tier] || 0;

    return allTools.filter((tool) => {
      const toolTierOrder = tierOrder[tool.tier_required] || 0;
      return toolTierOrder <= clientTierOrder;
    });
  };

  // Open modal for creating new client
  const handleNewClient = () => {
    setEditingClient(null);
    setFormData(emptyClientForm);
    onOpen();
  };

  // Open modal for editing existing client
  const handleEditClient = (client: ClienteVizu) => {
    setEditingClient(client);
    setFormData({
      nome_empresa: client.nome_empresa,
      tipo_cliente: client.tipo_cliente || 'standard',
      tier: client.tier || 'BASIC',
      prompt_base: client.prompt_base || '',
      enabled_tools: client.enabled_tools || [],
      collection_rag: client.collection_rag || '',
      external_user_id: client.external_user_id || '',
    });
    onOpen();
  };

  // Save client (create or update)
  const handleSave = async () => {
    if (!formData.nome_empresa.trim()) {
      toast({
        title: 'Nome da empresa obrigatório',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    setSaving(true);
    try {
      if (editingClient) {
        // Update existing
        const updateData: ClienteVizuUpdate = {
          ...formData,
        };
        await updateClient(editingClient.id, updateData);
        toast({
          title: 'Cliente atualizado',
          status: 'success',
          duration: 3000,
        });
      } else {
        // Create new
        await createClient(formData);
        toast({
          title: 'Cliente criado',
          status: 'success',
          duration: 3000,
        });
      }
      onClose();
      loadData();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save';
      toast({
        title: 'Erro ao salvar',
        description: message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setSaving(false);
    }
  };

  // Delete client
  const handleDelete = async () => {
    if (!deletingClient) return;

    setSaving(true);
    try {
      await deleteClient(deletingClient.id);
      toast({
        title: 'Cliente excluído',
        status: 'success',
        duration: 3000,
      });
      onDeleteClose();
      setDeletingClient(null);
      loadData();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete';
      toast({
        title: 'Erro ao excluir',
        description: message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setSaving(false);
    }
  };

  // Confirm delete
  const handleConfirmDelete = (client: ClienteVizu) => {
    setDeletingClient(client);
    onDeleteOpen();
  };

  // Get tier badge color
  const getTierColor = (tier: string | null): string => {
    const colors: Record<string, string> = {
      FREE: 'gray',
      BASIC: 'blue',
      SME: 'green',
      PREMIUM: 'purple',
      ENTERPRISE: 'orange',
      ADMIN: 'red',
    };
    return colors[tier || 'BASIC'] || 'gray';
  };

  // Available tools for current form tier
  const availableTools = getToolsForTier(formData.tier || 'BASIC');

  return (
    <AdminLayout>
      <Box p={8} maxW="1400px" mx="auto">
        {/* Header */}
        <HStack justify="space-between" mb={8}>
          <VStack align="start" spacing={1}>
            <HStack>
              <Icon as={FiUsers} boxSize={6} color="gray.600" />
              <Text fontSize="24px" fontWeight="600" color="gray.900">
                Gerenciar Clientes Vizu
              </Text>
            </HStack>
            <Text fontSize="14px" color="gray.500">
              Criar e gerenciar clientes, suas ferramentas e configurações
            </Text>
          </VStack>

          <HStack>
            <Button
              leftIcon={<FiRefreshCw />}
              variant="outline"
              onClick={loadData}
              isLoading={loading}
            >
              Atualizar
            </Button>
            <Button
              leftIcon={<FiPlus />}
              colorScheme="blue"
              onClick={handleNewClient}
            >
              Novo Cliente
            </Button>
          </HStack>
        </HStack>

        {/* Error Alert */}
        {error && (
          <Alert status="error" mb={6} borderRadius="md">
            <AlertIcon />
            {error}
          </Alert>
        )}

        {/* Loading */}
        {loading ? (
          <Box textAlign="center" py={12}>
            <Spinner size="xl" />
            <Text mt={4} color="gray.500">
              Carregando clientes...
            </Text>
          </Box>
        ) : (
          /* Clients Table */
          <Box bg="white" borderRadius="lg" border="1px solid" borderColor="gray.200" overflow="hidden">
            <TableContainer>
              <Table variant="simple">
                <Thead bg="gray.50">
                  <Tr>
                    <Th>Empresa</Th>
                    <Th>Tier</Th>
                    <Th>Tipo</Th>
                    <Th>Ferramentas</Th>
                    <Th>Collection RAG</Th>
                    <Th>Criado em</Th>
                    <Th textAlign="right">Ações</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {clients.length === 0 ? (
                    <Tr>
                      <Td colSpan={7} textAlign="center" py={8}>
                        <Text color="gray.500">Nenhum cliente encontrado</Text>
                      </Td>
                    </Tr>
                  ) : (
                    clients.map((client) => (
                      <Tr key={client.id} _hover={{ bg: 'gray.50' }}>
                        <Td>
                          <Text fontWeight="500">{client.nome_empresa}</Text>
                          <Text fontSize="xs" color="gray.400" fontFamily="mono">
                            {client.id.slice(0, 8)}...
                          </Text>
                        </Td>
                        <Td>
                          <Badge colorScheme={getTierColor(client.tier)}>
                            {client.tier || 'BASIC'}
                          </Badge>
                        </Td>
                        <Td>
                          <Text fontSize="sm" color="gray.600">
                            {client.tipo_cliente || '-'}
                          </Text>
                        </Td>
                        <Td>
                          <Text fontSize="sm" color="gray.600">
                            {client.enabled_tools?.length || 0} ferramentas
                          </Text>
                        </Td>
                        <Td>
                          <Text fontSize="sm" color="gray.600" maxW="150px" isTruncated>
                            {client.collection_rag || '-'}
                          </Text>
                        </Td>
                        <Td>
                          <Text fontSize="sm" color="gray.500">
                            {client.created_at
                              ? new Date(client.created_at).toLocaleDateString('pt-BR')
                              : '-'}
                          </Text>
                        </Td>
                        <Td textAlign="right">
                          <HStack justify="flex-end" spacing={2}>
                            <IconButton
                              aria-label="Editar"
                              icon={<FiEdit2 />}
                              size="sm"
                              variant="ghost"
                              onClick={() => handleEditClient(client)}
                            />
                            <IconButton
                              aria-label="Excluir"
                              icon={<FiTrash2 />}
                              size="sm"
                              variant="ghost"
                              colorScheme="red"
                              onClick={() => handleConfirmDelete(client)}
                            />
                          </HStack>
                        </Td>
                      </Tr>
                    ))
                  )}
                </Tbody>
              </Table>
            </TableContainer>
          </Box>
        )}

        {/* Create/Edit Modal */}
        <Modal isOpen={isOpen} onClose={onClose} size="xl">
          <ModalOverlay />
          <ModalContent maxW="800px">
            <ModalHeader>
              {editingClient ? 'Editar Cliente' : 'Novo Cliente'}
            </ModalHeader>
            <ModalCloseButton />
            <ModalBody pb={6}>
              <VStack spacing={6} align="stretch">
                {/* Basic Info */}
                <SimpleGrid columns={2} spacing={4}>
                  <FormControl isRequired>
                    <FormLabel>Nome da Empresa</FormLabel>
                    <Input
                      value={formData.nome_empresa}
                      onChange={(e) =>
                        setFormData({ ...formData, nome_empresa: e.target.value })
                      }
                      placeholder="Ex: Acme Corp"
                    />
                  </FormControl>

                  <FormControl>
                    <FormLabel>Tipo de Cliente</FormLabel>
                    <Select
                      value={formData.tipo_cliente}
                      onChange={(e) =>
                        setFormData({ ...formData, tipo_cliente: e.target.value })
                      }
                    >
                      <option value="standard">Standard</option>
                      <option value="premium">Premium</option>
                      <option value="enterprise">Enterprise</option>
                    </Select>
                  </FormControl>
                </SimpleGrid>

                {/* Tier Selection */}
                <FormControl>
                  <FormLabel>
                    <HStack>
                      <Icon as={FiShield} />
                      <Text>Tier (Nível de Acesso)</Text>
                    </HStack>
                  </FormLabel>
                  <Select
                    value={formData.tier}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        tier: e.target.value as TierType,
                        // Reset tools when tier changes
                        enabled_tools: [],
                      })
                    }
                  >
                    {TIERS.map((tier) => (
                      <option key={tier} value={tier}>
                        {tier}
                      </option>
                    ))}
                  </Select>
                  <FormHelperText>
                    O tier determina quais ferramentas e funcionalidades o cliente pode acessar
                  </FormHelperText>
                </FormControl>

                <Divider />

                {/* Tools Selection */}
                <FormControl>
                  <FormLabel>
                    <HStack>
                      <Icon as={FiTool} />
                      <Text>Ferramentas Habilitadas</Text>
                    </HStack>
                  </FormLabel>
                  <FormHelperText mb={3}>
                    Selecione as ferramentas disponíveis para este cliente (baseado no tier{' '}
                    {formData.tier})
                  </FormHelperText>

                  {availableTools.length === 0 ? (
                    <Text color="gray.500" fontSize="sm">
                      Nenhuma ferramenta disponível para este tier
                    </Text>
                  ) : (
                    <CheckboxGroup
                      value={formData.enabled_tools}
                      onChange={(values) =>
                        setFormData({ ...formData, enabled_tools: values as string[] })
                      }
                    >
                      <Wrap spacing={3}>
                        {availableTools.map((tool) => (
                          <WrapItem key={tool.name}>
                            <Checkbox value={tool.name}>
                              <VStack align="start" spacing={0}>
                                <HStack>
                                  <Text fontSize="sm">{tool.name}</Text>
                                  <Badge size="sm" colorScheme={getTierColor(tool.tier_required)}>
                                    {tool.tier_required}
                                  </Badge>
                                </HStack>
                                <Text fontSize="xs" color="gray.500" maxW="200px">
                                  {tool.description}
                                </Text>
                              </VStack>
                            </Checkbox>
                          </WrapItem>
                        ))}
                      </Wrap>
                    </CheckboxGroup>
                  )}
                </FormControl>

                <Divider />

                {/* RAG Collection */}
                <FormControl>
                  <FormLabel>Collection RAG</FormLabel>
                  <Input
                    value={formData.collection_rag}
                    onChange={(e) =>
                      setFormData({ ...formData, collection_rag: e.target.value })
                    }
                    placeholder="Nome da collection no Qdrant"
                  />
                  <FormHelperText>
                    Collection do Qdrant para busca RAG deste cliente
                  </FormHelperText>
                </FormControl>

                {/* External User ID */}
                <FormControl>
                  <FormLabel>External User ID</FormLabel>
                  <Input
                    value={formData.external_user_id}
                    onChange={(e) =>
                      setFormData({ ...formData, external_user_id: e.target.value })
                    }
                    placeholder="ID do usuário no Supabase Auth (opcional)"
                  />
                  <FormHelperText>
                    Vincula este cliente a um usuário do Supabase Auth
                  </FormHelperText>
                </FormControl>

                {/* Prompt Base */}
                <FormControl>
                  <FormLabel>Prompt Base</FormLabel>
                  <Textarea
                    value={formData.prompt_base}
                    onChange={(e) =>
                      setFormData({ ...formData, prompt_base: e.target.value })
                    }
                    placeholder="Prompt personalizado para o agente deste cliente..."
                    rows={4}
                  />
                  <FormHelperText>
                    Instruções personalizadas que serão incluídas no prompt do agente
                  </FormHelperText>
                </FormControl>
              </VStack>
            </ModalBody>

            <ModalFooter>
              <Button variant="ghost" mr={3} onClick={onClose}>
                Cancelar
              </Button>
              <Button colorScheme="blue" onClick={handleSave} isLoading={saving}>
                {editingClient ? 'Salvar' : 'Criar'}
              </Button>
            </ModalFooter>
          </ModalContent>
        </Modal>

        {/* Delete Confirmation Modal */}
        <Modal isOpen={isDeleteOpen} onClose={onDeleteClose} isCentered>
          <ModalOverlay />
          <ModalContent>
            <ModalHeader>Confirmar Exclusão</ModalHeader>
            <ModalCloseButton />
            <ModalBody>
              <Text>
                Tem certeza que deseja excluir o cliente{' '}
                <strong>{deletingClient?.nome_empresa}</strong>?
              </Text>
              <Text color="red.500" mt={2} fontSize="sm">
                Esta ação não pode ser desfeita.
              </Text>
            </ModalBody>
            <ModalFooter>
              <Button variant="ghost" mr={3} onClick={onDeleteClose}>
                Cancelar
              </Button>
              <Button colorScheme="red" onClick={handleDelete} isLoading={saving}>
                Excluir
              </Button>
            </ModalFooter>
          </ModalContent>
        </Modal>
      </Box>
    </AdminLayout>
  );
}

export default AdminClientesVizuPage;
